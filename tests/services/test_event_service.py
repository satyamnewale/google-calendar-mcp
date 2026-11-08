from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from errors.exceptions import ConfirmationRequiredError, EventAlreadyCancelledError
from services import event_service

TZ = ZoneInfo("Asia/Kolkata")


def timed(day=10, hour=10):
    return datetime(2026, 11, day, hour, 0, tzinfo=TZ)


def test_create_timed_event_builds_google_event_body(monkeypatch):
    captured = {}
    def insert(body):
        captured["body"] = body
        return {"id": "event_001", **body}
    monkeypatch.setattr(event_service, "insert_calendar_event", insert)

    result = event_service.create_event("Team Meeting", timed(), timed(hour=11))

    assert result["id"] == "event_001"
    body = captured["body"]
    assert body["summary"] == "Team Meeting"
    assert body["start"]["dateTime"]
    assert body["end"]["dateTime"]
    assert body["start"]["timeZone"] == event_service.TIMEZONE


def test_create_all_day_event(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        event_service, "insert_calendar_event",
        lambda body: captured.setdefault("body", body) or {"id": "event_002"},
    )
    # Avoid relying on the truthiness of the captured body in the mock return.
    def insert(body):
        captured["body"] = body
        return {"id": "event_002", **body}
    monkeypatch.setattr(event_service, "insert_calendar_event", insert)

    result = event_service.create_event(
        "Project Submission", date(2026, 11, 10), date(2026, 11, 11), all_day=True
    )

    assert result["id"] == "event_002"
    assert captured["body"]["start"] == {"date": "2026-11-10"}
    assert captured["body"]["end"] == {"date": "2026-11-11"}


def test_create_timed_event_uses_default_duration(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        event_service, "insert_calendar_event",
        lambda body: captured.setdefault("body", body),
    )

    event_service.create_event("Quick Meeting", timed(), end=None)

    start = datetime.fromisoformat(captured["body"]["start"]["dateTime"])
    end = datetime.fromisoformat(captured["body"]["end"]["dateTime"])
    assert end - start == timedelta(minutes=event_service.DEFAULT_EVENT_DURATION_MINUTES)


def test_create_event_includes_optional_description_and_location(monkeypatch):
    captured = {}
    def insert(body):
        captured["body"] = body
        return body
    monkeypatch.setattr(event_service, "insert_calendar_event", insert)

    event_service.create_event(
        "Client Meeting", timed(), timed(hour=11),
        description="Discuss project", location="Office",
    )

    assert captured["body"]["description"] == "Discuss project"
    assert captured["body"]["location"] == "Office"


def test_create_event_sets_popup_reminder(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        event_service, "insert_calendar_event",
        lambda body: captured.setdefault("body", body),
    )

    event_service.create_event("Meeting", timed(), timed(hour=11), reminder_minutes=15)

    assert captured["body"]["reminders"] == {
        "useDefault": False,
        "overrides": [{"method": "popup", "minutes": 15}],
    }


def test_create_event_includes_valid_recurrence(monkeypatch):
    captured = {}
    def insert(body):
        captured["body"] = body
        return body
    monkeypatch.setattr(event_service, "insert_calendar_event", insert)

    rule = ["RRULE:FREQ=DAILY;INTERVAL=1"]
    event_service.create_event("Daily Standup", timed(), timed(hour=11), recurrence=rule)

    assert captured["body"]["recurrence"] == rule


def test_create_event_rejects_blank_title():
    with pytest.raises(ValueError):
        event_service.create_event("", timed(), timed(hour=11))


def test_create_event_rejects_invalid_time_range():
    with pytest.raises(ValueError):
        event_service.create_event("Meeting", timed(hour=12), timed(hour=11))


def test_create_event_rejects_invalid_reminder():
    with pytest.raises(ValueError):
        event_service.create_event("Meeting", timed(), timed(hour=11), reminder_minutes=-1)


def test_create_event_rejects_non_datetime_for_timed_event():
    with pytest.raises(ValueError):
        event_service.create_event("Meeting", date(2026, 11, 10), date(2026, 11, 11))


def test_update_event_delegates_to_calendar_service(monkeypatch):
    captured = {}
    def update(event_id, updates):
        captured["event_id"] = event_id
        captured["updates"] = updates
        return {"id": event_id, **updates}
    monkeypatch.setattr(event_service, "update_calendar_event", update)

    result = event_service.update_event("event_001", {"summary": "Updated Meeting"})

    assert result["id"] == "event_001"
    assert captured == {
        "event_id": "event_001",
        "updates": {"summary": "Updated Meeting"},
    }


def test_update_event_rejects_unsupported_field():
    with pytest.raises(ValueError):
        event_service.update_event("event_001", {"invalid_field": "value"})


def test_delete_event_requires_confirmation():
    with pytest.raises(ConfirmationRequiredError):
        event_service.delete_event("event_001", confirmed=False)


def test_delete_event_deletes_confirmed_active_event(monkeypatch):
    monkeypatch.setattr(
        event_service, "get_event_by_id",
        lambda event_id: {"id": event_id, "status": "confirmed"},
    )
    deleted = {}
    def delete(event_id):
        deleted["id"] = event_id
        return {"success": True, "event_id": event_id}
    monkeypatch.setattr(event_service, "delete_calendar_event", delete)

    result = event_service.delete_event("event_001", confirmed=True)

    assert deleted["id"] == "event_001"
    assert result["success"] is True


def test_delete_event_rejects_already_cancelled_event(monkeypatch):
    monkeypatch.setattr(
        event_service, "get_event_by_id",
        lambda event_id: {"id": event_id, "status": "cancelled"},
    )
    def should_not_delete(event_id):
        pytest.fail("A cancelled event must not be deleted again")
    monkeypatch.setattr(event_service, "delete_calendar_event", should_not_delete)

    with pytest.raises(EventAlreadyCancelledError):
        event_service.delete_event("event_001", confirmed=True)


def test_get_event_details_returns_event(monkeypatch):
    expected = {"id": "event_001", "summary": "Team Meeting"}
    monkeypatch.setattr(event_service, "get_event_by_id", lambda event_id: expected)

    assert event_service.get_event_details("event_001") == expected


def test_postpone_timed_event_updates_only_schedule_and_reuses_existing_event(monkeypatch):
    existing = {
        "id": "event_001",
        "summary": "Team Meeting",
        "description": "Preserve this description",
        "start": {"dateTime": "2026-11-10T10:00:00+05:30"},
        "end": {"dateTime": "2026-11-10T11:00:00+05:30"},
    }
    monkeypatch.setattr(event_service, "get_event_by_id", lambda event_id: existing)
    captured = {}
    def update(event_id, updates, **kwargs):
        captured.update(event_id=event_id, updates=updates, kwargs=kwargs)
        return {"id": event_id, **updates}
    monkeypatch.setattr(event_service, "update_calendar_event", update)

    event_service.postpone_event("event_001", timed(day=12), timed(day=12, hour=11))

    assert captured["event_id"] == "event_001"
    assert captured["updates"]["start"]["dateTime"]
    assert captured["updates"]["end"]["dateTime"]
    assert captured["kwargs"]["existing_event"] is existing


def test_postpone_all_day_event(monkeypatch):
    existing = {
        "id": "event_002",
        "summary": "Project Submission",
        "start": {"date": "2026-11-10"},
        "end": {"date": "2026-11-11"},
    }
    monkeypatch.setattr(event_service, "get_event_by_id", lambda event_id: existing)
    captured = {}
    def update(event_id, updates, **kwargs):
        captured["updates"] = updates
        return {"id": event_id}
    monkeypatch.setattr(event_service, "update_calendar_event", update)

    event_service.postpone_event(
        "event_002", date(2026, 11, 12), date(2026, 11, 13)
    )

    assert captured["updates"] == {
        "start": {"date": "2026-11-12"},
        "end": {"date": "2026-11-13"},
    }


def test_postpone_rejects_cancelled_event(monkeypatch):
    monkeypatch.setattr(
        event_service, "get_event_by_id",
        lambda event_id: {
            "id": event_id,
            "status": "cancelled",
            "start": {"dateTime": "2026-11-10T10:00:00+05:30"},
        },
    )
    def should_not_update(*args, **kwargs):
        pytest.fail("A cancelled event must not be postponed")
    monkeypatch.setattr(event_service, "update_calendar_event", should_not_update)

    with pytest.raises(ValueError, match="Cannot postpone a cancelled event"):
        event_service.postpone_event("event_001", timed(day=12), timed(day=12, hour=11))
