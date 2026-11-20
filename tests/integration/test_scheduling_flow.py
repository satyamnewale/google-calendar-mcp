
from unittest.mock import AsyncMock, patch

import pytest

import server


@pytest.mark.asyncio
@pytest.mark.integration
async def test_available_slot_then_create_event():
    with (
        patch(
            "server.check_availability",
            new_callable=AsyncMock,
            return_value={"available": True, "busy_periods": []},
        ) as mock_availability,
        patch(
            "server.create_event",
            new_callable=AsyncMock,
            return_value={"id": "event_010", "summary": "Client Meeting"},
        ) as mock_create,
    ):
        result = await server.create_calendar_event(
            title="Client Meeting",
            start="2026-11-10T14:00:00+05:30",
            end="2026-11-10T15:00:00+05:30",
        )

    assert result["success"] is True
    assert result["event"]["id"] == "event_010"
    mock_availability.assert_awaited_once()
    mock_create.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_busy_slot_prevents_event_creation():
    busy = [
        {
            "start": "2026-11-10T14:00:00+05:30",
            "end": "2026-11-10T15:00:00+05:30",
        }
    ]

    with (
        patch(
            "server.check_availability",
            new_callable=AsyncMock,
            return_value={"available": False, "busy_periods": busy},
        ),
        patch(
            "server.create_event",
            new_callable=AsyncMock,
        ) as mock_create,
    ):
        result = await server.create_calendar_event(
            title="Client Meeting",
            start="2026-11-10T14:00:00+05:30",
            end="2026-11-10T15:00:00+05:30",
        )

    assert result["success"] is False
    assert result["conflict"] is True
    mock_create.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_check_calendar_availability():
    expected = {"available": True, "busy_periods": []}

    with patch(
        "server.check_availability",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock_availability:
        result = await server.check_calendar_availability(
            start="2026-11-10T10:00:00+05:30",
            end="2026-11-10T11:00:00+05:30",
        )

    assert result == expected
    mock_availability.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_check_calendar_availability_with_conflict():
    busy = [
        {
            "start": "2026-11-10T10:00:00+05:30",
            "end": "2026-11-10T11:00:00+05:30",
        }
    ]

    with patch(
        "server.check_availability",
        new_callable=AsyncMock,
        return_value={"available": False, "busy_periods": busy},
    ):
        result = await server.check_calendar_availability(
            start="2026-11-10T10:00:00+05:30",
            end="2026-11-10T11:00:00+05:30",
        )

    assert result["available"] is False
    assert result["busy_periods"] == busy


@pytest.mark.asyncio
@pytest.mark.integration
async def test_suggest_available_slots():
    expected = [
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
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock_slots:
        result = await server.suggest_available_slots(
            start="2026-11-10T09:00:00+05:30",
            end="2026-11-10T18:00:00+05:30",
            duration_minutes=60,
        )

    assert result == expected
    assert mock_slots.await_args.args[2] == 60


@pytest.mark.asyncio
@pytest.mark.integration
async def test_suggest_available_slots_with_custom_duration():
    with patch(
        "server.get_available_slots",
        new_callable=AsyncMock,
        return_value=[],
    ) as mock_slots:
        result = await server.suggest_available_slots(
            start="2026-11-10T09:00:00+05:30",
            end="2026-11-10T18:00:00+05:30",
            duration_minutes=90,
        )

    assert result == []
    assert mock_slots.await_args.args[2] == 90
