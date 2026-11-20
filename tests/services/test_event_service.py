
from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest

from errors.exceptions import (
    ConfirmationRequiredError,
    EventAlreadyCancelledError,
)
from services import event_service


@pytest.mark.asyncio
@pytest.mark.services
async def test_create_event_calls_insert(monkeypatch):
    insert = AsyncMock(return_value={"id": "event_001"})
    monkeypatch.setattr(event_service, "insert_calendar_event", insert)

    start = datetime.fromisoformat("2026-11-10T10:00:00+05:30")
    end = datetime.fromisoformat("2026-11-10T11:00:00+05:30")

    result = await event_service.create_event(
        "Team Meeting",
        start,
        end,
    )

    assert result == {"id": "event_001"}
    insert.assert_awaited_once()

    body = insert.await_args.args[0]
    assert body["summary"] == "Team Meeting"
    assert body["start"]["dateTime"] == start.isoformat()
    assert body["end"]["dateTime"] == end.isoformat()


@pytest.mark.asyncio
@pytest.mark.services
async def test_create_all_day_event(monkeypatch):
    insert = AsyncMock(return_value={"id": "event_002"})
    monkeypatch.setattr(event_service, "insert_calendar_event", insert)

    result = await event_service.create_event(
        "Submission",
        date(2026, 11, 10),
        date(2026, 11, 11),
        all_day=True,
    )

    assert result["id"] == "event_002"

    body = insert.await_args.args[0]
    assert body["start"] == {"date": "2026-11-10"}
    assert body["end"] == {"date": "2026-11-11"}


@pytest.mark.asyncio
@pytest.mark.services
async def test_update_event_calls_calendar_service(monkeypatch):
    update = AsyncMock(return_value={"id": "event_001"})
    monkeypatch.setattr(event_service, "update_calendar_event", update)

    result = await event_service.update_event(
        "event_001",
        {"summary": "Updated"},
    )

    assert result["id"] == "event_001"
    update.assert_awaited_once_with(
        event_id="event_001",
        updates={"summary": "Updated"},
        existing_event=None,
    )


@pytest.mark.asyncio
@pytest.mark.services
async def test_update_recurrence_fetches_existing_event(monkeypatch):
    existing = {
        "id": "event_001",
        "start": {"dateTime": "2026-11-10T10:00:00+05:30"},
    }

    get_event = AsyncMock(return_value=existing)
    update = AsyncMock(return_value={"id": "event_001"})

    monkeypatch.setattr(event_service, "get_event_by_id", get_event)
    monkeypatch.setattr(event_service, "update_calendar_event", update)

    result = await event_service.update_event(
        "event_001",
        {"recurrence": ["RRULE:FREQ=DAILY;COUNT=3"]},
    )

    assert result["id"] == "event_001"
    get_event.assert_awaited_once_with("event_001")
    update.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.services
async def test_delete_event_requires_confirmation():
    with pytest.raises(ConfirmationRequiredError):
        await event_service.delete_event("event_001", confirmed=False)


@pytest.mark.asyncio
@pytest.mark.services
async def test_delete_event_rejects_already_cancelled(monkeypatch):
    get_event = AsyncMock(
        return_value={"id": "event_001", "status": "cancelled"}
    )
    delete = AsyncMock()

    monkeypatch.setattr(event_service, "get_event_by_id", get_event)
    monkeypatch.setattr(event_service, "delete_calendar_event", delete)

    with pytest.raises(EventAlreadyCancelledError):
        await event_service.delete_event("event_001", confirmed=True)

    get_event.assert_awaited_once_with("event_001")
    delete.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.services
async def test_delete_recurring_series_requires_scope(monkeypatch):
    get_event = AsyncMock(
        return_value={
            "id": "event_001",
            "recurrence": ["RRULE:FREQ=DAILY;COUNT=3"],
            "status": "confirmed",
        }
    )
    delete = AsyncMock()

    monkeypatch.setattr(event_service, "get_event_by_id", get_event)
    monkeypatch.setattr(event_service, "delete_calendar_event", delete)

    with pytest.raises(ConfirmationRequiredError):
        await event_service.delete_event(
            "event_001",
            confirmed=True,
        )

    delete.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.services
async def test_delete_event_calls_calendar_service(monkeypatch):
    existing = {
        "id": "event_001",
        "etag": '"etag-001"',
        "status": "confirmed",
    }

    get_event = AsyncMock(return_value=existing)
    delete = AsyncMock(
        return_value={"success": True, "event_id": "event_001"}
    )

    monkeypatch.setattr(event_service, "get_event_by_id", get_event)
    monkeypatch.setattr(event_service, "delete_calendar_event", delete)

    result = await event_service.delete_event(
        "event_001",
        confirmed=True,
    )

    assert result["success"] is True
    delete.assert_awaited_once_with(
        "event_001",
        existing_event=existing,
    )


@pytest.mark.asyncio
@pytest.mark.services
async def test_get_event_details(monkeypatch):
    expected = {"id": "event_001"}
    get_event = AsyncMock(return_value=expected)
    monkeypatch.setattr(event_service, "get_event_by_id", get_event)

    result = await event_service.get_event_details("event_001")

    assert result == expected
    get_event.assert_awaited_once_with("event_001")


@pytest.mark.asyncio
@pytest.mark.services
async def test_postpone_event(monkeypatch):
    existing = {
        "id": "event_001",
        "etag": '"etag-001"',
        "start": {"dateTime": "2026-11-10T10:00:00+05:30"},
        "end": {"dateTime": "2026-11-10T11:00:00+05:30"},
    }

    update = AsyncMock(return_value={"id": "event_001"})
    monkeypatch.setattr(event_service, "update_calendar_event", update)

    new_start = datetime.fromisoformat("2026-11-11T10:00:00+05:30")
    new_end = datetime.fromisoformat("2026-11-11T11:00:00+05:30")

    result = await event_service.postpone_event(
        "event_001",
        new_start,
        new_end,
        existing_event=existing,
    )

    assert result["id"] == "event_001"
    update.assert_awaited_once()

    kwargs = update.await_args.kwargs
    assert kwargs["event_id"] == "event_001"
    assert kwargs["existing_event"] == existing
    assert kwargs["updates"]["start"]["dateTime"] == new_start.isoformat()
    assert kwargs["updates"]["end"]["dateTime"] == new_end.isoformat()


@pytest.mark.asyncio
@pytest.mark.services
async def test_postpone_all_day_event(monkeypatch):
    existing = {
        "id": "event_002",
        "start": {"date": "2026-11-10"},
        "end": {"date": "2026-11-11"},
    }

    update = AsyncMock(return_value={"id": "event_002"})
    monkeypatch.setattr(event_service, "update_calendar_event", update)

    result = await event_service.postpone_event(
        "event_002",
        date(2026, 11, 12),
        date(2026, 11, 13),
        existing_event=existing,
    )

    assert result["id"] == "event_002"

    updates = update.await_args.kwargs["updates"]
    assert updates == {
        "start": {"date": "2026-11-12"},
        "end": {"date": "2026-11-13"},
    }
