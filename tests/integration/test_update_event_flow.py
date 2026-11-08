
from unittest.mock import patch

import pytest
from fastmcp.exceptions import ToolError

import server

@pytest.mark.integration
def test_update_event_title():
    with patch(
        "server.update_event",
        return_value={
            "id": "event_001",
            "summary": "Updated Meeting",
        },
    ) as mock_update:

        result = server.edit_calendar_event(
            event_id="event_001",
            updates={"summary": "Updated Meeting"},
        )

    assert result["id"] == "event_001"
    assert result["summary"] == "Updated Meeting"

    mock_update.assert_called_once_with(
        "event_001",
        {"summary": "Updated Meeting"},
    )

@pytest.mark.integration
def test_update_event_description_and_location():
    updates = {
        "description": "Updated agenda",
        "location": "Conference Room",
    }

    with patch(
        "server.update_event",
        return_value={"id": "event_001"},
    ) as mock_update:

        result = server.edit_calendar_event(
            event_id="event_001",
            updates=updates,
        )

    assert result["id"] == "event_001"
    mock_update.assert_called_once_with("event_001", updates)

@pytest.mark.integration
def test_update_event_schedule():
    updates = {
        "start": {
            "dateTime": "2026-11-10T12:00:00+05:30",
        },
        "end": {
            "dateTime": "2026-11-10T13:00:00+05:30",
        },
    }

    with patch(
        "server.update_event",
        return_value={"id": "event_001"},
    ) as mock_update:

        result = server.edit_calendar_event(
            event_id="event_001",
            updates=updates,
        )

    assert result["id"] == "event_001"
    mock_update.assert_called_once()

@pytest.mark.integration
def test_update_event_invalid_id():
    with (
        patch("server.update_event") as mock_update,
        pytest.raises(ToolError),
    ):
        server.edit_calendar_event(
            event_id="",
            updates={"summary": "Updated Meeting"},
        )

    mock_update.assert_not_called()

@pytest.mark.integration
def test_update_event_empty_updates():
    with (
        patch("server.update_event") as mock_update,
        pytest.raises(ToolError),
    ):
        server.edit_calendar_event(
            event_id="event_001",
            updates={},
        )

    mock_update.assert_not_called()


def test_update_event_unsupported_field():
    with (
        patch("server.update_event") as mock_update,
        pytest.raises(ToolError),
    ):
        server.edit_calendar_event(
            event_id="event_001",
            updates={"invalid_field": "value"},
        )

    mock_update.assert_not_called()
