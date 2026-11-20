
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.exceptions import ToolError

import server

from errors.exceptions import ConfirmationRequiredError
from pydantic import ValidationError
from unittest.mock import AsyncMock, patch



@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_event_without_confirmation():
    with (
        patch(
            "server.delete_event",
            new_callable=AsyncMock,
        ) as mock_delete,
        pytest.raises(ConfirmationRequiredError),
    ):
        await server.remove_calendar_event(
            event_id="event_001",
            confirmed=False,
        )

    mock_delete.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_event_without_confirmation():
    with (
        patch(
            "server.delete_event",
            new_callable=AsyncMock,
        ) as mock_delete,
        pytest.raises(ConfirmationRequiredError),
    ):
        await server.remove_calendar_event(
            event_id="event_001",
            confirmed=False,
        )

    mock_delete.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_event_invalid_id():
    with (
        patch(
            "server.delete_event",
            new_callable=AsyncMock,
        ) as mock_delete,
        pytest.raises(ValidationError),
    ):
        await server.remove_calendar_event(
            event_id="",
            confirmed=True,
        )

    mock_delete.assert_not_awaited()



@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_recurring_series():
    with patch(
        "server.delete_event",
        new_callable=AsyncMock,
        return_value={"success": True, "event_id": "event_001"},
    ) as mock_delete:
        result = await server.remove_calendar_event(
            event_id="event_001",
            confirmed=True,
            recurrence_scope="series",
        )

    assert result["success"] is True
    mock_delete.assert_awaited_once_with(
        "event_001",
        True,
        "series",
    )
