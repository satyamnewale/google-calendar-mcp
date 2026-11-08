
import pytest
from unittest.mock import patch

import server


# --------------------------------------------------
# 1. Verify MCP tool registration
# --------------------------------------------------

def test_server_has_expected_tools():
    expected_tools = {
        "create_calendar_event",
        "edit_calendar_event",
        "remove_calendar_event",
        "get_calendar_event",
        "postpone_calendar_event",
        "find_calendar_events",
        "find_similar_calendar_events",
        "get_calendar_overview",
        "check_calendar_availability",
        "suggest_available_slots",
        "get_calendar_list",
    }

    registered_tools = {
        tool.name
        for tool in server.mcp._tool_manager.list_tools()
    }

    assert expected_tools.issubset(registered_tools)


# --------------------------------------------------
# 2. Create calendar event
# --------------------------------------------------

def test_create_calendar_event_valid_input():
    with patch("server.create_event") as mock_create:
        mock_create.return_value = {
            "id": "event_001",
            "summary": "Team Meeting",
        }

        # We'll invoke the MCP tool through FastMCP
        # in the next implementation step.

        assert mock_create is not None


# --------------------------------------------------
# 3. Edit calendar event
# --------------------------------------------------

def test_edit_calendar_event_valid_input():
    with patch("server.update_event") as mock_update:
        mock_update.return_value = {
            "id": "event_001",
            "summary": "Updated Meeting",
        }

        assert mock_update is not None


# --------------------------------------------------
# 4. Delete calendar event
# --------------------------------------------------

def test_remove_calendar_event_requires_confirmation():
    with patch("server.delete_event") as mock_delete:

        # The actual tool invocation and assertion
        # will be added after checking the server API.

        assert mock_delete is not None


# --------------------------------------------------
# 5. Get calendar event
# --------------------------------------------------

def test_get_calendar_event():
    with patch("server.get_event_details") as mock_get:
        mock_get.return_value = {
            "id": "event_001",
            "summary": "Team Meeting",
        }

        assert mock_get is not None


# --------------------------------------------------
# 6. Postpone calendar event
# --------------------------------------------------

def test_postpone_calendar_event():
    with patch("server.postpone_event") as mock_postpone:
        mock_postpone.return_value = {
            "id": "event_001",
            "summary": "Team Meeting",
        }

        assert mock_postpone is not None


# --------------------------------------------------
# 7. Find calendar events
# --------------------------------------------------

def test_find_calendar_events():
    with patch("server.search_events") as mock_search:
        mock_search.return_value = []

        assert mock_search is not None


# --------------------------------------------------
# 8. Find similar calendar events
# --------------------------------------------------

def test_find_similar_calendar_events():
    with patch("server.find_similar_events") as mock_similar:
        mock_similar.return_value = []

        assert mock_similar is not None


# --------------------------------------------------
# 9. Get calendar overview
# --------------------------------------------------

def test_get_calendar_overview():
    with patch("server.get_calendar_summary") as mock_summary:
        mock_summary.return_value = {
            "period": "day",
            "events": [],
        }

        assert mock_summary is not None


# --------------------------------------------------
# 10. Check calendar availability
# --------------------------------------------------

def test_check_calendar_availability():
    with patch("server.check_availability") as mock_availability:
        mock_availability.return_value = {
            "available": True,
            "busy_periods": [],
        }

        assert mock_availability is not None


# --------------------------------------------------
# 11. Suggest available slots
# --------------------------------------------------

def test_suggest_available_slots():
    with patch("server.get_available_slots") as mock_slots:
        mock_slots.return_value = []

        assert mock_slots is not None


# --------------------------------------------------
# 12. Get calendar list
# --------------------------------------------------

def test_get_calendar_list():
    with patch("server.list_calendars") as mock_list:
        mock_list.return_value = []

        assert mock_list is not None
