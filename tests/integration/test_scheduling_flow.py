
from unittest.mock import patch
import pytest
import server

@pytest.mark.integration
def test_available_slot_then_create_event():
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
                "id": "event_010",
                "summary": "Client Meeting",
            },
        ) as mock_create,
    ):
        result = server.create_calendar_event(
            title="Client Meeting",
            start="2026-11-10T14:00:00+05:30",
            end="2026-11-10T15:00:00+05:30",
        )

    assert result["success"] is True
    assert result["event"]["id"] == "event_010"

    mock_availability.assert_called_once()
    mock_create.assert_called_once()

@pytest.mark.integration
def test_busy_slot_prevents_event_creation():
    busy_periods = [
        {
            "start": "2026-11-10T14:00:00+05:30",
            "end": "2026-11-10T15:00:00+05:30",
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
            title="Client Meeting",
            start="2026-11-10T14:00:00+05:30",
            end="2026-11-10T15:00:00+05:30",
        )

    assert result["success"] is False
    assert result["conflict"] is True
    mock_create.assert_not_called()

@pytest.mark.integration
def test_check_calendar_availability():
    with patch(
        "server.check_availability",
        return_value={
            "available": True,
            "busy_periods": [],
        },
    ) as mock_availability:

        result = server.check_calendar_availability(
            start="2026-11-10T10:00:00+05:30",
            end="2026-11-10T11:00:00+05:30",
        )

    assert result["available"] is True
    mock_availability.assert_called_once()

@pytest.mark.integration
def test_check_calendar_availability_with_conflict():
    busy_periods = [
        {
            "start": "2026-11-10T10:00:00+05:30",
            "end": "2026-11-10T11:00:00+05:30",
        }
    ]

    with patch(
        "server.check_availability",
        return_value={
            "available": False,
            "busy_periods": busy_periods,
        },
    ):
        result = server.check_calendar_availability(
            start="2026-11-10T10:00:00+05:30",
            end="2026-11-10T11:00:00+05:30",
        )

    assert result["available"] is False
    assert result["busy_periods"] == busy_periods

@pytest.mark.integration
def test_suggest_available_slots():
    expected_slots = [
        {
            "start": "2026-11-10T09:00:00+05:30",
            "end": "2026-11-10T10:00:00+05:30",
        },
        {
            "start": "2026-11-10T11:00:00+05:30",
            "end": "2026-11-10T12:00:00+05:30",
        },
    ]

    with patch(
        "server.get_available_slots",
        return_value=expected_slots,
    ) as mock_slots:

        result = server.suggest_available_slots(
            start="2026-11-10T09:00:00+05:30",
            end="2026-11-10T18:00:00+05:30",
            duration_minutes=60,
        )

    assert result == expected_slots

    args = mock_slots.call_args.args

    assert args[2] == 60

@pytest.mark.integration
def test_suggest_available_slots_with_custom_duration():
    with patch(
        "server.get_available_slots",
        return_value=[],
    ) as mock_slots:

        result = server.suggest_available_slots(
            start="2026-11-10T09:00:00+05:30",
            end="2026-11-10T18:00:00+05:30",
            duration_minutes=90,
        )

    assert result == []
    assert mock_slots.call_args.args[2] == 90
