from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch

import pytest

import server
import asyncio
import inspect


TZ = ZoneInfo("Asia/Kolkata")
START = "2026-11-10T10:00:00+05:30"
END = "2026-11-10T11:00:00+05:30"
NEW_START = "2026-11-12T10:00:00+05:30"
NEW_END = "2026-11-12T11:00:00+05:30"


# --------------------------------------------------
# 1. MCP TOOL REGISTRATION
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

    result = server.mcp.list_tools()

    # Support both synchronous and asynchronous FastMCP versions.
    if inspect.isawaitable(result):
        registered_tools = asyncio.run(result)
    else:
        registered_tools = result

    registered_names = {
        tool.name for tool in registered_tools
    }

    assert registered_names == expected_tools


# --------------------------------------------------
# 2. CREATE CALENDAR EVENT
# --------------------------------------------------

def test_create_calendar_event_valid_timed_event():
    expected_event = {"id": "event_001", "summary": "Team Meeting"}

    with (
        patch("server.check_availability", return_value={
            "available": True,
            "busy_periods": [],
        }) as mock_availability,
        patch("server.create_event", return_value=expected_event) as mock_create,
    ):
        result = server.create_calendar_event(
            title="Team Meeting",
            start=START,
            end=END,
            description="Discuss sprint progress",
            location="Office",
        )

    assert result == {"success": True, "event": expected_event}
    mock_availability.assert_called_once()
    mock_create.assert_called_once()

    kwargs = mock_create.call_args.kwargs
    assert kwargs["title"] == "Team Meeting"
    assert kwargs["description"] == "Discuss sprint progress"
    assert kwargs["location"] == "Office"
    assert kwargs["all_day"] is False


def test_create_calendar_event_all_day_skips_availability_check():
    expected_event = {"id": "event_002", "summary": "Project Submission"}

    with (
        patch("server.check_availability") as mock_availability,
        patch("server.create_event", return_value=expected_event) as mock_create,
    ):
        result = server.create_calendar_event(
            title="Project Submission",
            start="2026-11-10",
            end="2026-11-11",
            all_day=True,
        )

    assert result == {"success": True, "event": expected_event}
    mock_availability.assert_not_called()
    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["all_day"] is True


def test_create_calendar_event_uses_default_one_hour_end():
    expected_event = {"id": "event_003", "summary": "Quick Meeting"}

    with (
        patch("server.check_availability", return_value={
            "available": True,
            "busy_periods": [],
        }) as mock_availability,
        patch("server.create_event", return_value=expected_event) as mock_create,
    ):
        result = server.create_calendar_event(
            title="Quick Meeting",
            start=START,
        )

    assert result["success"] is True
    availability_start, availability_end = mock_availability.call_args.args
    assert (availability_end - availability_start).total_seconds() == 3600
    assert mock_create.call_args.kwargs["end"] == availability_end


def test_create_calendar_event_returns_conflict_without_creating():
    busy = [{"start": START, "end": END}]

    with (
        patch("server.check_availability", return_value={
            "available": False,
            "busy_periods": busy,
        }),
        patch("server.create_event") as mock_create,
    ):
        result = server.create_calendar_event(
            title="Team Meeting",
            start=START,
            end=END,
        )

    assert result["success"] is False
    assert result["conflict"] is True
    assert result["busy_periods"] == busy
    mock_create.assert_not_called()


def test_create_calendar_event_allows_conflict_when_user_approves():
    expected_event = {"id": "event_004", "summary": "Approved Meeting"}

    with (
        patch("server.check_availability", return_value={
            "available": False,
            "busy_periods": [{"start": START, "end": END}],
        }),
        patch("server.create_event", return_value=expected_event) as mock_create,
    ):
        result = server.create_calendar_event(
            title="Approved Meeting",
            start=START,
            end=END,
            allow_conflict=True,
        )

    assert result == {"success": True, "event": expected_event}
    mock_create.assert_called_once()


def test_create_calendar_event_builds_recurrence_rule():
    expected_event = {"id": "event_005", "summary": "Daily Standup"}

    with (
        patch("server.check_availability", return_value={
            "available": True,
            "busy_periods": [],
        }),
        patch("server.build_recurrence_rule", return_value=[
            "RRULE:FREQ=DAILY;INTERVAL=1"
        ]) as mock_rule,
        patch("server.create_event", return_value=expected_event) as mock_create,
    ):
        result = server.create_calendar_event(
            title="Daily Standup",
            start=START,
            end=END,
            recurrence_frequency="DAILY",
            recurrence_interval=1,
        )

    assert result["success"] is True
    mock_rule.assert_called_once_with(
        frequency="DAILY",
        interval=1,
        byday=None,
    )
    assert mock_create.call_args.kwargs["recurrence"] == [
        "RRULE:FREQ=DAILY;INTERVAL=1"
    ]


def test_create_calendar_event_rejects_invalid_recurrence_interval():
    with pytest.raises(Exception):
        server.create_calendar_event(
            title="Daily Standup",
            start=START,
            end=END,
            recurrence_frequency="DAILY",
            recurrence_interval=0,
        )


# --------------------------------------------------
# 3. EDIT CALENDAR EVENT
# --------------------------------------------------

def test_edit_calendar_event_valid_input():
    expected = {"id": "event_001", "summary": "Updated Meeting"}

    with patch("server.update_event", return_value=expected) as mock_update:
        result = server.edit_calendar_event(
            event_id="event_001",
            updates={"summary": "Updated Meeting"},
        )

    assert result == expected
    mock_update.assert_called_once_with(
        "event_001",
        {"summary": "Updated Meeting"},
    )


def test_edit_calendar_event_rejects_empty_event_id():
    with pytest.raises(Exception):
        server.edit_calendar_event(
            event_id="",
            updates={"summary": "Updated Meeting"},
        )


def test_edit_calendar_event_rejects_unsupported_update_field():
    with (
        patch("server.update_event") as mock_update,
        pytest.raises(Exception),
    ):
        server.edit_calendar_event(
            event_id="event_001",
            updates={"unsupported_field": "value"},
        )

    mock_update.assert_not_called()


# --------------------------------------------------
# 4. DELETE CALENDAR EVENT
# --------------------------------------------------

def test_remove_calendar_event_requires_confirmation():
    with (
        patch("server.delete_event") as mock_delete,
        pytest.raises(Exception),
    ):
        server.remove_calendar_event(
            event_id="event_001",
            confirmed=False,
        )

    mock_delete.assert_not_called()


def test_remove_calendar_event_after_confirmation():
    expected = {"success": True, "event_id": "event_001"}

    with patch("server.delete_event", return_value=expected) as mock_delete:
        result = server.remove_calendar_event(
            event_id="event_001",
            confirmed=True,
        )

    assert result == expected
    mock_delete.assert_called_once_with("event_001", True)


# --------------------------------------------------
# 5. GET CALENDAR EVENT
# --------------------------------------------------

def test_get_calendar_event_returns_details():
    expected = {
        "id": "event_001",
        "summary": "Team Meeting",
        "status": "confirmed",
    }

    with patch("server.get_event_details", return_value=expected) as mock_get:
        result = server.get_calendar_event("event_001")

    assert result == expected
    mock_get.assert_called_once_with("event_001")


def test_get_calendar_event_rejects_empty_id():
    with pytest.raises(Exception):
        server.get_calendar_event("")


# --------------------------------------------------
# 6. POSTPONE CALENDAR EVENT
# --------------------------------------------------

def test_postpone_timed_calendar_event():
    existing = {
        "id": "event_001",
        "start": {"dateTime": START},
        "end": {"dateTime": END},
    }
    expected = {"id": "event_001", "summary": "Team Meeting"}

    parsed_start = datetime(2026, 11, 12, 10, 0, tzinfo=TZ)
    parsed_end = datetime(2026, 11, 12, 11, 0, tzinfo=TZ)

    with (
        patch("server.get_event_details", return_value=existing),
        patch("server.parse_datetime", side_effect=[parsed_start, parsed_end]),
        patch("server.postpone_event", return_value=expected) as mock_postpone,
    ):
        result = server.postpone_calendar_event(
            event_id="event_001",
            new_start=NEW_START,
            new_end=NEW_END,
        )

    assert result == expected
    mock_postpone.assert_called_once_with(
        "event_001", parsed_start, parsed_end
    )


def test_postpone_all_day_calendar_event():
    existing = {
        "id": "event_002",
        "start": {"date": "2026-11-10"},
        "end": {"date": "2026-11-11"},
    }
    expected = {"id": "event_002", "summary": "Project Submission"}

    parsed_start = datetime(2026, 11, 12, tzinfo=TZ).date()
    parsed_end = datetime(2026, 11, 13, tzinfo=TZ).date()

    with (
        patch("server.get_event_details", return_value=existing),
        patch("server.resolve_date_expression", side_effect=[parsed_start, parsed_end]),
        patch("server.postpone_event", return_value=expected) as mock_postpone,
    ):
        result = server.postpone_calendar_event(
            event_id="event_002",
            new_start="2026-11-12",
            new_end="2026-11-13",
        )

    assert result == expected
    mock_postpone.assert_called_once_with(
        "event_002", parsed_start, parsed_end
    )


# --------------------------------------------------
# 7. FIND CALENDAR EVENTS
# --------------------------------------------------

def test_find_calendar_events():
    expected = [{"id": "event_001", "summary": "Team Meeting"}]
    parsed_start = datetime(2026, 11, 10, tzinfo=TZ)
    parsed_end = datetime(2026, 11, 11, tzinfo=TZ)

    with (
        patch("server.parse_datetime", side_effect=[parsed_start, parsed_end]),
        patch("server.search_events", return_value=expected) as mock_search,
    ):
        result = server.find_calendar_events(
            start=START,
            end=END,
            title="Team",
        )

    assert result == expected
    mock_search.assert_called_once_with(parsed_start, parsed_end, "Team")


def test_find_calendar_events_without_title():
    parsed_start = datetime(2026, 11, 10, tzinfo=TZ)
    parsed_end = datetime(2026, 11, 11, tzinfo=TZ)

    with (
        patch("server.parse_datetime", side_effect=[parsed_start, parsed_end]),
        patch("server.search_events", return_value=[]) as mock_search,
    ):
        result = server.find_calendar_events(start=START, end=END)

    assert result == []
    mock_search.assert_called_once_with(parsed_start, parsed_end, None)


# --------------------------------------------------
# 8. FIND SIMILAR CALENDAR EVENTS
# --------------------------------------------------

def test_find_similar_calendar_events():
    expected = [
        {
            "event": {"id": "event_001", "summary": "Team Meeting"},
            "similarity": 1.0,
        }
    ]
    parsed_start = datetime(2026, 11, 10, tzinfo=TZ)
    parsed_end = datetime(2026, 11, 11, tzinfo=TZ)

    with (
        patch("server.parse_datetime", side_effect=[parsed_start, parsed_end]),
        patch("server.find_similar_events", return_value=expected) as mock_similar,
    ):
        result = server.find_similar_calendar_events(
            title="Team Meeting",
            start=START,
            end=END,
        )

    assert result == expected
    mock_similar.assert_called_once_with(
        "Team Meeting", parsed_start, parsed_end
    )


# --------------------------------------------------
# 9. GET CALENDAR OVERVIEW
# --------------------------------------------------

@pytest.mark.parametrize("period", ["day", "week", "month"])
def test_get_calendar_overview(period):
    expected = {"total_events": 2, "events": []}

    with patch("server.get_calendar_summary", return_value=expected) as mock_summary:
        result = server.get_calendar_overview(
            period=period,
            value="2026-11-10",
        )

    assert result == expected
    mock_summary.assert_called_once_with(period, "2026-11-10")


def test_get_calendar_overview_rejects_invalid_period():
    with pytest.raises(Exception):
        server.get_calendar_overview(period="year", value="2026")


# --------------------------------------------------
# 10. CHECK CALENDAR AVAILABILITY
# --------------------------------------------------

def test_check_calendar_availability():
    expected = {"available": True, "busy_periods": []}
    parsed_start = datetime(2026, 11, 10, 10, 0, tzinfo=TZ)
    parsed_end = datetime(2026, 11, 10, 11, 0, tzinfo=TZ)

    with (
        patch("server.parse_datetime", side_effect=[parsed_start, parsed_end]),
        patch("server.check_availability", return_value=expected) as mock_availability,
    ):
        result = server.check_calendar_availability(start=START, end=END)

    assert result == expected
    mock_availability.assert_called_once_with(parsed_start, parsed_end)


# --------------------------------------------------
# 11. SUGGEST AVAILABLE SLOTS
# --------------------------------------------------

def test_suggest_available_slots():
    expected = [
        {"start": START, "end": END},
    ]
    parsed_start = datetime(2026, 11, 10, 9, 0, tzinfo=TZ)
    parsed_end = datetime(2026, 11, 10, 17, 0, tzinfo=TZ)

    with (
        patch("server.parse_datetime", side_effect=[parsed_start, parsed_end]),
        patch("server.get_available_slots", return_value=expected) as mock_slots,
    ):
        result = server.suggest_available_slots(
            start=START,
            end=END,
            duration_minutes=45,
        )

    assert result == expected
    mock_slots.assert_called_once_with(parsed_start, parsed_end, 45)


def test_suggest_available_slots_rejects_non_positive_duration():
    with pytest.raises(Exception):
        server.suggest_available_slots(
            start=START,
            end=END,
            duration_minutes=0,
        )


# --------------------------------------------------
# 12. GET CALENDAR LIST
# --------------------------------------------------

def test_get_calendar_list_returns_selected_calendar_fields():
    calendars = [
        {
            "id": "primary",
            "summary": "My Calendar",
            "primary": True,
            "timeZone": "Asia/Kolkata",
            "accessRole": "owner",
        },
        {
            "id": "work",
            "summary": "Work",
            "timeZone": "Asia/Kolkata",
        },
    ]

    with patch("server.list_calendars", return_value=calendars) as mock_list:
        result = server.get_calendar_list()

    assert result == [
        {
            "id": "primary",
            "summary": "My Calendar",
            "primary": True,
            "timeZone": "Asia/Kolkata",
        },
        {
            "id": "work",
            "summary": "Work",
            "primary": False,
            "timeZone": "Asia/Kolkata",
        },
    ]
    mock_list.assert_called_once_with()


def test_get_calendar_list_returns_empty_list():
    with patch("server.list_calendars", return_value=[]):
        assert server.get_calendar_list() == []
