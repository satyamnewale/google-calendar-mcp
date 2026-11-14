
from datetime import date, datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch

import pytest
from fastmcp.exceptions import ToolError

import server


TZ = ZoneInfo("Asia/Kolkata")

@pytest.mark.integration
def test_postpone_timed_event():
    existing_event = {
        "id": "event_001",
        "summary": "Team Meeting",
        "start": {
            "dateTime": "2026-11-10T10:00:00+05:30",
        },
        "end": {
            "dateTime": "2026-11-10T11:00:00+05:30",
        },
    }

    with (
        patch(
            "server.get_event_details",
            return_value=existing_event,
        ) as mock_get,
        patch(
            "server.postpone_event",
            return_value={"id": "event_001"},
        ) as mock_postpone,
    ):
        result = server.postpone_calendar_event(
            event_id="event_001",
            new_start="2026-11-11T10:00:00+05:30",
            new_end="2026-11-11T11:00:00+05:30",
        )

    assert result["id"] == "event_001"
    mock_get.assert_called_once_with("event_001")

    args = mock_postpone.call_args.args

    assert args[0] == "event_001"
    assert isinstance(args[1], datetime)
    assert isinstance(args[2], datetime)
    assert args[1].tzinfo is not None
    assert args[2].tzinfo is not None

@pytest.mark.integration
def test_postpone_all_day_event():
    existing_event = {
        "id": "event_002",
        "summary": "Project Submission",
        "start": {
            "date": "2026-11-10",
        },
        "end": {
            "date": "2026-11-11",
        },
    }

    with (
        patch(
            "server.get_event_details",
            return_value=existing_event,
        ),
        patch(
            "server.postpone_event",
            return_value={"id": "event_002"},
        ) as mock_postpone,
    ):
        result = server.postpone_calendar_event(
            event_id="event_002",
            new_start="2026-11-12",
            new_end="2026-11-13",
        )

    assert result["success"] is True
    assert result["event"]["id"] == "event_002"
    assert result["user_visible_range"] == {
        "start_date": "2026-11-12",
        "end_date_inclusive": "2026-11-13",
    }

    args = mock_postpone.call_args.args

    assert args[0] == "event_002"
    assert isinstance(args[1], date)
    assert isinstance(args[2], date)
    assert not isinstance(args[1], datetime)
    assert not isinstance(args[2], datetime)

@pytest.mark.integration
def test_postpone_event_invalid_id():
    with (
        patch("server.get_event_details") as mock_get,
        pytest.raises(ToolError),
    ):
        server.postpone_calendar_event(
            event_id="",
            new_start="2026-11-12T10:00:00+05:30",
            new_end="2026-11-12T11:00:00+05:30",
        )

    mock_get.assert_not_called()

@pytest.mark.integration
def test_postpone_event_missing_end():
    with (
        patch("server.get_event_details") as mock_get,
        pytest.raises(ToolError),
    ):
        server.postpone_calendar_event(
            event_id="event_001",
            new_start="2026-11-12T10:00:00+05:30",
            new_end="",
        )

    mock_get.assert_not_called()

@pytest.mark.integration
def test_postpone_event_invalid_datetime():
    existing_event = {
        "id": "event_001",
        "start": {
            "dateTime": "2026-11-10T10:00:00+05:30",
        },
    }

    with (
        patch(
            "server.get_event_details",
            return_value=existing_event,
        ),
        patch("server.postpone_event") as mock_postpone,
        pytest.raises(ToolError),
    ):
        server.postpone_calendar_event(
            event_id="event_001",
            new_start="invalid-date",
            new_end="2026-11-12T11:00:00+05:30",
        )

    mock_postpone.assert_not_called()
