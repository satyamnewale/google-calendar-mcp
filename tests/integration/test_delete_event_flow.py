
from unittest.mock import patch

import pytest
from fastmcp.exceptions import ToolError

import server


def test_delete_event_with_confirmation():
    with patch(
        "server.delete_event",
        return_value={
            "success": True,
            "event_id": "event_001",
        },
    ) as mock_delete:

        result = server.remove_calendar_event(
            event_id="event_001",
            confirmed=True,
        )

    assert result["success"] is True

    mock_delete.assert_called_once_with(
        "event_001",
        True,
    )


def test_delete_event_without_confirmation():
    with (
        patch("server.delete_event") as mock_delete,
        pytest.raises(ToolError),
    ):
        server.remove_calendar_event(
            event_id="event_001",
            confirmed=False,
        )

    # Deletion must never reach the service.
    mock_delete.assert_not_called()


def test_delete_event_invalid_id():
    with (
        patch("server.delete_event") as mock_delete,
        pytest.raises(ToolError),
    ):
        server.remove_calendar_event(
            event_id="",
            confirmed=True,
        )

    mock_delete.assert_not_called()


def test_delete_already_cancelled_event():
    with patch(
        "server.delete_event",
        return_value={
            "success": True,
            "event_id": "event_001",
            "message": "Event was already cancelled.",
        },
    ) as mock_delete:

        result = server.remove_calendar_event(
            event_id="event_001",
            confirmed=True,
        )

    assert result["success"] is True
    mock_delete.assert_called_once()
