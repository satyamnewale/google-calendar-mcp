
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch

import pytest
from fastmcp.exceptions import ToolError

import server


TZ = ZoneInfo("Asia/Kolkata")


# --------------------------------------------------
# 1. CREATE TIMED EVENT
# --------------------------------------------------

def test_create_timed_event():
    with (
        patch(
            "server.check_availability",
            return_value={
                "available": True,
                "busy_periods": [],
            },
        ) as mock_availability,
        patch(
            "server.create_event",
            return_value={
                "id": "event_001",
                "summary": "Team Meeting",
            },
        ) as mock_create,
    ):
        result = server.create_calendar_event(
            title="Team Meeting",
            start="2026-11-10T10:00:00+05:30",
            end="2026-11-10T11:00:00+05:30",
        )

    assert result["success"] is True
    assert result["event"]["id"] == "event_001"

    mock_availability.assert_called_once()
    mock_create.assert_called_once()


# --------------------------------------------------
# 2. CREATE ALL-DAY EVENT
# --------------------------------------------------

def test_create_all_day_event():
    with patch(
        "server.create_event",
        return_value={
            "id": "event_002",
            "summary": "Project Submission",
        },
    ) as mock_create:

        result = server.create_calendar_event(
            title="Project Submission",
            start="2026-11-10",
            end="2026-11-11",
            all_day=True,
        )

    assert result["success"] is True
    assert result["event"]["id"] == "event_002"

    kwargs = mock_create.call_args.kwargs

    assert kwargs["all_day"] is True
    assert kwargs["start"] == date(2026, 11, 10)
    assert kwargs["end"] == date(2026, 11, 11)


# --------------------------------------------------
# 3. DEFAULT ONE-HOUR DURATION
# --------------------------------------------------

def test_create_timed_event_without_end_uses_one_hour():
    with (
        patch(
            "server.check_availability",
            return_value={
                "available": True,
                "busy_periods": [],
            },
        ),
        patch(
            "server.create_event",
            return_value={"id": "event_003"},
        ) as mock_create,
    ):
        result = server.create_calendar_event(
            title="Quick Meeting",
            start="2026-11-10T10:00:00+05:30",
        )

    assert result["success"] is True

    kwargs = mock_create.call_args.kwargs

    assert kwargs["end"] - kwargs["start"] == timedelta(hours=1)


# --------------------------------------------------
# 4. CREATE RECURRING EVENT
# --------------------------------------------------

def test_create_recurring_event():
    with (
        patch(
            "server.check_availability",
            return_value={
                "available": True,
                "busy_periods": [],
            },
        ),
        patch(
            "server.create_event",
            return_value={"id": "event_004"},
        ) as mock_create,
    ):
        result = server.create_calendar_event(
            title="Daily Standup",
            start="2026-11-10T10:00:00+05:30",
            recurrence_frequency="DAILY",
            recurrence_interval=1,
        )

    assert result["success"] is True

    kwargs = mock_create.call_args.kwargs

    assert kwargs["recurrence"] is not None
    assert "FREQ=DAILY" in kwargs["recurrence"][0]


# --------------------------------------------------
# 5. CONFLICT WITHOUT USER APPROVAL
# --------------------------------------------------

def test_create_event_with_conflict_without_permission():
    busy_periods = [
        {
            "start": "2026-11-10T10:00:00+05:30",
            "end": "2026-11-10T11:00:00+05:30",
        }
    ]

    with (
        patch(
            "server.check_availability",
            return_value={
                "available": False,
                "busy_periods": busy_periods,
            },
        ),
        patch("server.create_event") as mock_create,
    ):
        result = server.create_calendar_event(
            title="Conflicting Meeting",
            start="2026-11-10T10:00:00+05:30",
            end="2026-11-10T11:00:00+05:30",
        )

    assert result["success"] is False
    assert result["conflict"] is True
    assert result["busy_periods"] == busy_periods

    mock_create.assert_not_called()


# --------------------------------------------------
# 6. CONFLICT WITH USER APPROVAL
# --------------------------------------------------

def test_create_event_with_conflict_and_permission():
    with (
        patch(
            "server.check_availability",
            return_value={
                "available": False,
                "busy_periods": [
                    {
                        "start": "10:00",
                        "end": "11:00",
                    }
                ],
            },
        ),
        patch(
            "server.create_event",
            return_value={"id": "event_005"},
        ) as mock_create,
    ):
        result = server.create_calendar_event(
            title="Approved Conflicting Meeting",
            start="2026-11-10T10:00:00+05:30",
            end="2026-11-10T11:00:00+05:30",
            allow_conflict=True,
        )

    assert result["success"] is True
    assert result["event"]["id"] == "event_005"

    mock_create.assert_called_once()


# --------------------------------------------------
# 7. INVALID EVENT TITLE
# --------------------------------------------------

def test_create_event_invalid_title():
    with (
        patch("server.create_event") as mock_create,
        pytest.raises(ToolError),
    ):
        server.create_calendar_event(
            title="",
            start="2026-11-10T10:00:00+05:30",
        )

    mock_create.assert_not_called()
