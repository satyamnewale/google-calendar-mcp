
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.exceptions import ToolError

import server

from pydantic import ValidationError
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_event_title():
    with patch(
        "server.update_event",
        new_callable=AsyncMock,
        return_value={
            "id": "event_001",
            "summary": "Updated Meeting",
        },
    ) as mock_update:
        result = await server.edit_calendar_event(
            event_id="event_001",
            updates={"summary": "Updated Meeting"},
        )

    assert result["id"] == "event_001"
    assert result["summary"] == "Updated Meeting"
    mock_update.assert_awaited_once_with(
        "event_001",
        {"summary": "Updated Meeting"},
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_event_description_and_location():
    updates = {
        "description": "Updated agenda",
        "location": "Conference Room",
    }

    with patch(
        "server.update_event",
        new_callable=AsyncMock,
        return_value={"id": "event_001"},
    ) as mock_update:
        result = await server.edit_calendar_event(
            event_id="event_001",
            updates=updates,
        )

    assert result["id"] == "event_001"
    mock_update.assert_awaited_once_with("event_001", updates)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_event_schedule():
    updates = {
        "start": {"dateTime": "2026-11-10T12:00:00+05:30"},
        "end": {"dateTime": "2026-11-10T13:00:00+05:30"},
    }

    with patch(
        "server.update_event",
        new_callable=AsyncMock,
        return_value={"id": "event_001"},
    ) as mock_update:
        result = await server.edit_calendar_event(
            event_id="event_001",
            updates=updates,
        )

    assert result["id"] == "event_001"
    mock_update.assert_awaited_once_with("event_001", updates)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_event_invalid_id():
    with (
        patch(
            "server.update_event",
            new_callable=AsyncMock,
        ) as mock_update,
        pytest.raises(ValidationError),
    ):
        await server.edit_calendar_event(
            event_id="",
            updates={"summary": "Updated Meeting"},
        )

    mock_update.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_event_empty_updates():
    with (
        patch(
            "server.update_event",
            new_callable=AsyncMock,
        ) as mock_update,
        pytest.raises(ValidationError),
    ):
        await server.edit_calendar_event(
            event_id="event_001",
            updates={},
        )

    mock_update.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_event_unsupported_field():
    with (
        patch(
            "server.update_event",
            new_callable=AsyncMock,
        ) as mock_update,
        pytest.raises(ValidationError),
    ):
        await server.edit_calendar_event(
            event_id="event_001",
            updates={"invalid_field": "value"},
        )

    mock_update.assert_not_awaited()
