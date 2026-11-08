from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from errors.exceptions import CalendarResultLimitExceededError
from services import calendar_service

TZ = ZoneInfo("Asia/Kolkata")

@pytest.mark.services
def dt(day, hour=0):
    return datetime(2026, 11, day, hour, 0, tzinfo=TZ)

@pytest.mark.services
def use_mock_service(monkeypatch, service):
    monkeypatch.setattr(calendar_service, "get_calendar_service", lambda: service)

@pytest.mark.services
def test_get_event_by_id(mock_calendar_service, monkeypatch):
    use_mock_service(monkeypatch, mock_calendar_service)
    expected = {"id": "event_001", "summary": "Team Meeting"}
    mock_calendar_service.events.return_value.get.return_value.execute.return_value = expected

    result = calendar_service.get_event_by_id("event_001")

    assert result == expected
    mock_calendar_service.events.return_value.get.assert_called_once_with(
        calendarId=calendar_service.CALENDAR_ID,
        eventId="event_001",
    )

@pytest.mark.services
def test_list_events_in_range(mock_calendar_service, monkeypatch):
    use_mock_service(monkeypatch, mock_calendar_service)
    expected = [{"id": "event_001"}, {"id": "event_002"}]
    mock_calendar_service.events.return_value.list.return_value.execute.return_value = {
        "items": expected
    }

    result = calendar_service.list_events_in_range(dt(10), dt(11))

    assert result == expected
    kwargs = mock_calendar_service.events.return_value.list.call_args.kwargs
    assert kwargs["timeMin"] == dt(10).isoformat()
    assert kwargs["timeMax"] == dt(11).isoformat()
    assert kwargs["singleEvents"] is True
    assert kwargs["orderBy"] == "startTime"

@pytest.mark.services
def test_list_events_rejects_invalid_range(mock_calendar_service, monkeypatch):
    use_mock_service(monkeypatch, mock_calendar_service)

    with pytest.raises(ValueError, match="End date must be after start date"):
        calendar_service.list_events_in_range(dt(11), dt(10))

@pytest.mark.services
def test_list_events_requires_timezone_aware_datetimes(mock_calendar_service, monkeypatch):
    use_mock_service(monkeypatch, mock_calendar_service)

    with pytest.raises(ValueError, match="timezone-aware"):
        calendar_service.list_events_in_range(
            datetime(2026, 11, 10), datetime(2026, 11, 11)
        )

@pytest.mark.services
def test_list_events_rejects_invalid_max_results(mock_calendar_service, monkeypatch):
    use_mock_service(monkeypatch, mock_calendar_service)

    with pytest.raises(ValueError, match="max_results"):
        calendar_service.list_events_in_range(dt(10), dt(11), max_results=0)

@pytest.mark.services
def test_list_events_handles_pagination(mock_calendar_service, monkeypatch):
    use_mock_service(monkeypatch, mock_calendar_service)
    execute = mock_calendar_service.events.return_value.list.return_value.execute
    execute.side_effect = [
        {"items": [{"id": "event_001"}], "nextPageToken": "page_2"},
        {"items": [{"id": "event_002"}]},
    ]

    result = calendar_service.list_events_in_range(dt(10), dt(11), max_results=10)

    assert [event["id"] for event in result] == ["event_001", "event_002"]
    assert execute.call_count == 2
    assert mock_calendar_service.events.return_value.list.call_args.kwargs["pageToken"] == "page_2"

@pytest.mark.services
def test_list_events_stops_at_max_results(
    mock_calendar_service,
    monkeypatch,
):
    use_mock_service(monkeypatch, mock_calendar_service)

    execute = (
        mock_calendar_service.events
        .return_value.list.return_value.execute
    )

    execute.return_value = {
        "items": [
            {"id": "event_001"},
            {"id": "event_002"},
        ],
        "nextPageToken": "another_page",
    }

    with pytest.raises(CalendarResultLimitExceededError):
        calendar_service.list_events_in_range(
            dt(10),
            dt(11),
            max_results=2,
        )

    assert execute.call_count == 1

@pytest.mark.services
def test_insert_calendar_event(mock_calendar_service, monkeypatch):
    use_mock_service(monkeypatch, mock_calendar_service)
    expected = {"id": "new_event", "summary": "New Meeting"}
    mock_calendar_service.events.return_value.insert.return_value.execute.return_value = expected
    body = {"summary": "New Meeting"}

    result = calendar_service.insert_calendar_event(body)

    assert result == expected
    mock_calendar_service.events.return_value.insert.assert_called_once_with(
        calendarId=calendar_service.CALENDAR_ID,
        body=body,
    )

@pytest.mark.services
def test_update_calendar_event_gets_then_updates_full_resource(mock_calendar_service, monkeypatch):
    use_mock_service(monkeypatch, mock_calendar_service)
    events = mock_calendar_service.events.return_value
    existing = {
        "id": "event_001",
        "etag": '"etag-001"',
        "summary": "Old title",
        "description": "Keep this description",
        "start": {"dateTime": "2026-11-10T10:00:00+05:30"},
        "end": {"dateTime": "2026-11-10T11:00:00+05:30"},
    }
    events.get.return_value.execute.return_value = existing
    updated = {**existing, "summary": "New title"}
    events.update.return_value.execute.return_value = updated

    result = calendar_service.update_calendar_event(
        "event_001", {"summary": "New title"}
    )

    assert result == updated
    events.get.assert_called_once_with(
        calendarId=calendar_service.CALENDAR_ID, eventId="event_001"
    )
    events.update.assert_called_once()
    body = events.update.call_args.kwargs["body"]
    assert body["summary"] == "New title"
    assert body["description"] == "Keep this description"
    events.patch.assert_not_called()

@pytest.mark.services
def test_update_calendar_event_uses_supplied_existing_event(mock_calendar_service, monkeypatch):
    use_mock_service(monkeypatch, mock_calendar_service)
    events = mock_calendar_service.events.return_value
    existing = {"id": "event_001", "etag": '"etag-001"',"summary": "Old"}
    events.update.return_value.execute.return_value = {"id": "event_001", "summary": "New"}

    calendar_service.update_calendar_event(
        "event_001", {"summary": "New"}, existing_event=existing
    )

    events.get.assert_not_called()
    events.update.assert_called_once()

@pytest.mark.services
def test_delete_calendar_event(mock_calendar_service, monkeypatch):
    use_mock_service(monkeypatch, mock_calendar_service)

    result = calendar_service.delete_calendar_event("event_001")

    assert result == {
        "success": True,
        "event_id": "event_001",
        "message": "Event deleted successfully.",
    }
    mock_calendar_service.events.return_value.delete.assert_called_once_with(
        calendarId=calendar_service.CALENDAR_ID,
        eventId="event_001",
    )

@pytest.mark.services
def test_list_calendars(mock_calendar_service, monkeypatch):
    use_mock_service(monkeypatch, mock_calendar_service)
    expected = [{"id": "primary", "summary": "My Calendar"}]
    mock_calendar_service.calendarList.return_value.list.return_value.execute.return_value = {
        "items": expected
    }

    assert calendar_service.list_calendars() == expected

@pytest.mark.services
def test_list_calendars_returns_empty_list_when_no_items(mock_calendar_service, monkeypatch):
    use_mock_service(monkeypatch, mock_calendar_service)
    mock_calendar_service.calendarList.return_value.list.return_value.execute.return_value = {}

    assert calendar_service.list_calendars() == []

@pytest.mark.services
def test_update_uses_if_match_etag(
    monkeypatch,
    mock_calendar_service,
):

    monkeypatch.setattr(
        calendar_service,
        "get_calendar_service",
        lambda: mock_calendar_service,
    )

    update_request = (
        mock_calendar_service.events().update.return_value
    )

    update_request.headers = {}

    update_request.execute.return_value = {
        "id": "test_event_001",
        "summary": "Updated Meeting",
    }

    result = calendar_service.update_calendar_event(
        event_id="test_event_001",
        updates={"summary": "Updated Meeting"},
    )

    assert result["summary"] == "Updated Meeting"

    assert update_request.headers["If-Match"] == (
        '"test-etag-001"'
    )


@pytest.mark.services
def test_delete_uses_if_match_etag(
    monkeypatch,
    mock_calendar_service,
):

    monkeypatch.setattr(
        calendar_service,
        "get_calendar_service",
        lambda: mock_calendar_service,
    )

    delete_request = (
        mock_calendar_service.events().delete.return_value
    )

    delete_request.headers = {}

    result = calendar_service.delete_calendar_event(
        event_id="test_event_001",
    )

    assert result["success"] is True

    assert delete_request.headers["If-Match"] == (
        '"test-etag-001"'
    )

@pytest.mark.services
def test_event_search_does_not_silently_truncate(
    monkeypatch,
    mock_calendar_service,
):

    from datetime import datetime
    from zoneinfo import ZoneInfo

    from errors.exceptions import (
        CalendarResultLimitExceededError,
    )

    TZ = ZoneInfo("Asia/Kolkata")

    monkeypatch.setattr(
        calendar_service,
        "get_calendar_service",
        lambda: mock_calendar_service,
    )

    mock_calendar_service.events().list.return_value.execute.return_value = {
        "items": [
            {"id": "event_001"}
        ],
        "nextPageToken": "next-page",
    }

    with pytest.raises(CalendarResultLimitExceededError):

        calendar_service.list_events_in_range(
            start_date=datetime(
                2026, 11, 1, tzinfo=TZ
            ),
            end_date=datetime(
                2026, 12, 1, tzinfo=TZ
            ),
            max_results=1,
        )