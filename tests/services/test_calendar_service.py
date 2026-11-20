
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from errors.exceptions import (
    CalendarConcurrencyError,
    CalendarResultLimitExceededError,
)
from services import calendar_service


TZ = ZoneInfo("Asia/Kolkata")


def dt(day, hour=0):
    return datetime(2026, 11, day, hour, 0, tzinfo=TZ)


@pytest.fixture
def use_mock_service(monkeypatch, mock_calendar_service):
    monkeypatch.setattr(
        calendar_service,
        "get_calendar_service",
        lambda: mock_calendar_service,
    )
    return mock_calendar_service


@pytest.mark.asyncio
@pytest.mark.services
async def test_list_calendars(use_mock_service):
    expected = [{"id": "primary", "summary": "Primary Calendar"}]
    use_mock_service.calendarList.return_value.list.return_value.execute.return_value = {
        "items": expected
    }

    result = await calendar_service.list_calendars()

    assert result == expected
    use_mock_service.calendarList.return_value.list.assert_called_once_with(
        maxResults=100
    )


@pytest.mark.asyncio
@pytest.mark.services
async def test_get_event_by_id(use_mock_service):
    expected = {"id": "event_001", "summary": "Team Meeting"}
    use_mock_service.events.return_value.get.return_value.execute.return_value = (
        expected
    )

    result = await calendar_service.get_event_by_id("event_001")

    assert result == expected
    use_mock_service.events.return_value.get.assert_called_once_with(
        calendarId=calendar_service.CALENDAR_ID,
        eventId="event_001",
    )


@pytest.mark.asyncio
@pytest.mark.services
async def test_list_events_in_range(use_mock_service):
    expected = [{"id": "event_001"}, {"id": "event_002"}]
    use_mock_service.events.return_value.list.return_value.execute.return_value = {
        "items": expected,
        "nextPageToken": None,
    }

    result = await calendar_service.list_events_in_range(dt(10), dt(11))

    assert result == expected

    kwargs = use_mock_service.events.return_value.list.call_args.kwargs
    assert kwargs["timeMin"] == dt(10).isoformat()
    assert kwargs["timeMax"] == dt(11).isoformat()
    assert kwargs["singleEvents"] is True
    assert kwargs["orderBy"] == "startTime"


@pytest.mark.asyncio
@pytest.mark.services
async def test_list_events_rejects_invalid_range(use_mock_service):
    with pytest.raises(ValueError, match="End date must be after start date"):
        await calendar_service.list_events_in_range(dt(11), dt(10))


@pytest.mark.asyncio
@pytest.mark.services
async def test_list_events_requires_timezone_aware_datetimes(use_mock_service):
    with pytest.raises(ValueError, match="timezone-aware"):
        await calendar_service.list_events_in_range(
            datetime(2026, 11, 10),
            datetime(2026, 11, 11),
        )


@pytest.mark.asyncio
@pytest.mark.services
async def test_list_events_rejects_invalid_max_results(use_mock_service):
    with pytest.raises(ValueError, match="max_results"):
        await calendar_service.list_events_in_range(
            dt(10),
            dt(11),
            max_results=0,
        )


@pytest.mark.asyncio
@pytest.mark.services
async def test_list_events_handles_pagination(use_mock_service):
    execute = use_mock_service.events.return_value.list.return_value.execute
    execute.side_effect = [
        {
            "items": [{"id": "event_001"}],
            "nextPageToken": "page_2",
        },
        {
            "items": [{"id": "event_002"}],
            "nextPageToken": None,
        },
    ]

    result = await calendar_service.list_events_in_range(
        dt(10),
        dt(11),
        max_results=10,
    )

    assert [event["id"] for event in result] == [
        "event_001",
        "event_002",
    ]
    assert execute.call_count == 2

    assert (
        use_mock_service.events.return_value.list.call_args.kwargs["pageToken"]
        == "page_2"
    )


@pytest.mark.asyncio
@pytest.mark.services
async def test_list_events_stops_at_max_results(use_mock_service):
    execute = use_mock_service.events.return_value.list.return_value.execute
    execute.return_value = {
        "items": [
            {"id": "event_001"},
            {"id": "event_002"},
        ],
        "nextPageToken": "another_page",
    }

    with pytest.raises(CalendarResultLimitExceededError):
        await calendar_service.list_events_in_range(
            dt(10),
            dt(11),
            max_results=2,
        )

    assert execute.call_count == 1


@pytest.mark.asyncio
@pytest.mark.services
async def test_insert_calendar_event(use_mock_service):
    expected = {"id": "new_event", "summary": "New Meeting"}
    use_mock_service.events.return_value.insert.return_value.execute.return_value = (
        expected
    )

    body = {"summary": "New Meeting"}

    result = await calendar_service.insert_calendar_event(body)

    assert result == expected
    use_mock_service.events.return_value.insert.assert_called_once_with(
        calendarId=calendar_service.CALENDAR_ID,
        body=body,
    )



@pytest.mark.asyncio
@pytest.mark.services
async def test_update_calendar_event_uses_existing_etag(use_mock_service):
    existing = {
        "id": "event_001",
        "etag": '"etag-001"',
        "summary": "Old title",
        "start": {"dateTime": "2026-11-10T10:00:00+05:30"},
        "end": {"dateTime": "2026-11-10T11:00:00+05:30"},
    }

    expected = {
        "id": "event_001",
        "summary": "New title",
    }

    request = use_mock_service.events.return_value.update.return_value

    # Use a real dictionary instead of a MagicMock.
    request.headers = {}
    request.execute.return_value = expected

    result = await calendar_service.update_calendar_event(
        "event_001",
        {"summary": "New title"},
        existing_event=existing,
    )

    assert result == expected
    assert request.headers["If-Match"] == '"etag-001"'


@pytest.mark.asyncio
@pytest.mark.services
async def test_update_calendar_event_requires_etag(use_mock_service):
    with pytest.raises(CalendarConcurrencyError, match="ETag is missing"):
        await calendar_service.update_calendar_event(
            "event_001",
            {"summary": "New title"},
            existing_event={"id": "event_001"},
        )



@pytest.mark.asyncio
@pytest.mark.services
async def test_delete_calendar_event_uses_existing_etag(use_mock_service):
    existing = {
        "id": "event_001",
        "etag": '"etag-001"',
    }

    request = use_mock_service.events.return_value.delete.return_value

    # Use a real dictionary instead of a MagicMock.
    request.headers = {}

    result = await calendar_service.delete_calendar_event(
        "event_001",
        existing_event=existing,
    )

    assert result["success"] is True
    assert result["event_id"] == "event_001"
    assert request.headers["If-Match"] == '"etag-001"'



@pytest.mark.asyncio
@pytest.mark.services
async def test_delete_calendar_event_requires_etag(use_mock_service):
    with pytest.raises(CalendarConcurrencyError, match="ETag is missing"):
        await calendar_service.delete_calendar_event(
            "event_001",
            existing_event={"id": "event_001"},
        )
