from datetime import datetime, date
from zoneinfo import ZoneInfo

import pytest

from services import calendar_summary

TZ = ZoneInfo("Asia/Kolkata")


@pytest.mark.services
def test_multiday_all_day_event_appears_on_each_day(monkeypatch):

    event = {
        "id": "event_001",
        "summary": "Project Workshop",
        "start": {
            "date": "2026-11-09",
        },
        "end": {
            "date": "2026-11-12",
        },
    }

    monkeypatch.setattr(
        calendar_summary,
        "get_week_range",
        lambda _: (
            datetime(2026, 11, 9, tzinfo=TZ),
            datetime(2026, 11, 16, tzinfo=TZ),
        ),
    )

    monkeypatch.setattr(
        calendar_summary,
        "get_event_for_week",
        lambda _: [event],
    )

    result = calendar_summary.get_weekly_schedule(
        "2026-11-09"
    )

    assert result["total_events"] == 1

    assert "2026-11-09" in result["days"]
    assert "2026-11-10" in result["days"]
    assert "2026-11-11" in result["days"]

    assert "2026-11-12" not in result["days"]


@pytest.mark.services
def test_multiday_timed_event_appears_on_each_occupied_day(monkeypatch):

    event = {
        "id": "event_002",
        "summary": "Conference",
        "start": {
            "dateTime": "2026-11-09T09:00:00+05:30",
        },
        "end": {
            "dateTime": "2026-11-11T17:00:00+05:30",
        },
    }

    monkeypatch.setattr(
        calendar_summary,
        "get_week_range",
        lambda _: (
            datetime(2026, 11, 9, tzinfo=TZ),
            datetime(2026, 11, 16, tzinfo=TZ),
        ),
    )

    monkeypatch.setattr(
        calendar_summary,
        "get_event_for_week",
        lambda _: [event],
    )

    result = calendar_summary.get_weekly_schedule(
        "2026-11-09"
    )

    assert result["total_events"] == 1

    assert len(result["days"]["2026-11-09"]) == 1
    assert len(result["days"]["2026-11-10"]) == 1
    assert len(result["days"]["2026-11-11"]) == 1


@pytest.mark.services
def test_event_ending_at_midnight_does_not_occupy_next_day():

    event = {
        "start": {
            "dateTime": "2026-11-09T22:00:00+05:30",
        },
        "end": {
            "dateTime": "2026-11-10T00:00:00+05:30",
        },
    }

    dates = calendar_summary._get_event_dates(
        event,
        date(2026, 11, 9),
        date(2026, 11, 12),
    )

    assert dates == [
        date(2026, 11, 9)
    ]

@pytest.fixture
def sample_events():
    return [
        {
            "id": "event_001",
            "summary": "Team Meeting",
            "status": "confirmed",
            "start": {"dateTime": "2026-11-10T10:00:00+05:30"},
        },
        {
            "id": "event_002",
            "summary": "Project Discussion",
            "status": "confirmed",
            "start": {"date": "2026-11-10"},
        },
    ]

@pytest.mark.services
def test_count_events_in_range_excludes_cancelled(monkeypatch):
    events = [
        {"id": "a", "status": "confirmed"},
        {"id": "b", "status": "cancelled"},
        {"id": "c"},
    ]
    monkeypatch.setattr(calendar_summary, "list_events_in_range", lambda start, end: events)

    count = calendar_summary.count_events_in_range(
        datetime(2026, 11, 10, tzinfo=TZ),
        datetime(2026, 11, 11, tzinfo=TZ),
    )

    assert count == 2

@pytest.mark.services
def test_daily_schedule_returns_date_count_and_events(monkeypatch, sample_events):
    monkeypatch.setattr(calendar_summary, "get_event_for_day", lambda day: sample_events)

    result = calendar_summary.get_daily_schedule("2026-11-10")

    assert result == {
        "date": "2026-11-10",
        "total_events": 2,
        "events": sample_events,
    }

@pytest.mark.services
def test_daily_schedule_returns_empty_schedule(monkeypatch):
    monkeypatch.setattr(calendar_summary, "get_event_for_day", lambda day: [])

    result = calendar_summary.get_daily_schedule("2026-11-10")

    assert result == {"date": "2026-11-10", "total_events": 0, "events": []}

@pytest.mark.services
def test_weekly_schedule_groups_events_by_date(monkeypatch):
    events = [
    {
        "id": "a",
        "start": {
            "dateTime": "2026-11-10T10:00:00+05:30"
        },
        "end": {
            "dateTime": "2026-11-10T11:00:00+05:30"
        },
    },
    {
        "id": "b",
        "start": {"date": "2026-11-10"},
        "end": {"date": "2026-11-11"},
    },
    {
        "id": "c",
        "start": {
            "dateTime": "2026-11-11T09:00:00+05:30"
        },
        "end": {
            "dateTime": "2026-11-11T10:00:00+05:30"
        },
    },
]
    monkeypatch.setattr(calendar_summary, "get_event_for_week", lambda week: events)

    result = calendar_summary.get_weekly_schedule("2026-11-10")

    assert result["total_events"] == 3
    assert [event["id"] for event in result["days"]["2026-11-10"]] == ["a", "b"]
    assert [event["id"] for event in result["days"]["2026-11-11"]] == ["c"]

@pytest.mark.services
def test_weekly_schedule_empty(monkeypatch):
    monkeypatch.setattr(calendar_summary, "get_event_for_week", lambda week: [])

    assert calendar_summary.get_weekly_schedule() == {"total_events": 0, "days": {}}

@pytest.mark.services
def test_monthly_overview_counts_events_per_day(monkeypatch):
    events = [
    {
        "id": "a",
        "start": {
            "dateTime": "2026-11-10T10:00:00+05:30"
        },
        "end": {
            "dateTime": "2026-11-10T11:00:00+05:30"
        },
    },
    {
        "id": "b",
        "start": {"date": "2026-11-10"},
        "end": {"date": "2026-11-11"},
    },
    {
    "id": "c",
        "start": {
            "dateTime": "2026-11-12T09:00:00+05:30"
        },
        "end": {
            "dateTime": "2026-11-12T10:00:00+05:30"
        },
    }
]
    monkeypatch.setattr(calendar_summary, "get_event_for_month", lambda month: events)

    result = calendar_summary.get_monthly_overview("2026-11")

    assert result == {
        "total_events": 3,
        "daily_counts": {"2026-11-10": 2, "2026-11-12": 1},
    }

@pytest.mark.services
def test_monthly_overview_empty(monkeypatch):
    monkeypatch.setattr(calendar_summary, "get_event_for_month", lambda month: [])

    assert calendar_summary.get_monthly_overview("2026-11") == {
        "total_events": 0,
        "daily_counts": {},
    }

@pytest.mark.services
def test_get_calendar_summary_daily(monkeypatch):
    expected = {"date": "2026-11-10", "total_events": 0, "events": []}
    monkeypatch.setattr(calendar_summary, "get_daily_schedule", lambda day: expected)

    assert calendar_summary.get_calendar_summary("day", "2026-11-10") == expected

@pytest.mark.services
def test_get_calendar_summary_weekly(monkeypatch):
    expected = {"total_events": 0, "days": {}}
    monkeypatch.setattr(calendar_summary, "get_weekly_schedule", lambda week: expected)

    assert calendar_summary.get_calendar_summary("week", "2026-11-10") == expected

@pytest.mark.services
def test_get_calendar_summary_monthly(monkeypatch):
    expected = {"total_events": 0, "daily_counts": {}}
    monkeypatch.setattr(calendar_summary, "get_monthly_overview", lambda month: expected)

    assert calendar_summary.get_calendar_summary("month", "2026-11") == expected

@pytest.mark.services
def test_get_calendar_summary_normalizes_period_case(monkeypatch):
    expected = {"date": "today", "total_events": 0, "events": []}
    monkeypatch.setattr(calendar_summary, "get_daily_schedule", lambda day: expected)

    assert calendar_summary.get_calendar_summary("DAY") == expected

@pytest.mark.services
def test_get_calendar_summary_rejects_unsupported_period():
    with pytest.raises(ValueError, match="Period must be day, week, or month"):
        calendar_summary.get_calendar_summary("year", "2026")
