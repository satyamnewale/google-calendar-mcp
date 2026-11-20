
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, MagicMock

import pytest

from services import availability_service
from errors.exceptions import CalendarFreeBusyError

TZ = ZoneInfo("Asia/Kolkata")


def dt(hour, minute=0):
    return datetime(2026, 11, 10, hour, minute, tzinfo=TZ)


@pytest.fixture
def mock_freebusy(monkeypatch):
    service = MagicMock()
    monkeypatch.setattr(
        availability_service,
        "get_calendar_service",
        lambda: service,
    )
    return service


def set_busy(service, periods, *, errors=None):
    calendar_data = {"busy": periods}
    if errors is not None:
        calendar_data["errors"] = errors

    service.freebusy.return_value.query.return_value.execute.return_value = {
        "calendars": {
            availability_service.CALENDAR_ID: calendar_data
        }
    }


# Pure synchronous helper tests

@pytest.mark.services
def test_detects_conflict_in_later_recurrence():
    occurrences = [
        (dt(9), dt(10)),
        (dt(10), dt(11)),
        (dt(11), dt(12)),
    ]
    busy = [
        {
            "start": "2026-11-10T10:30:00+05:30",
            "end": "2026-11-10T10:45:00+05:30",
        }
    ]

    conflicts = availability_service.find_occurrence_conflicts(
        occurrences,
        busy,
    )

    assert len(conflicts) == 1


@pytest.mark.services
def test_no_conflict_when_busy_period_is_outside_occurrence():
    occurrences = [(dt(9), dt(10))]
    busy = [
        {
            "start": "2026-11-10T11:00:00+05:30",
            "end": "2026-11-10T12:00:00+05:30",
        }
    ]

    assert availability_service.find_occurrence_conflicts(
        occurrences,
        busy,
    ) == []


# Async service tests

@pytest.mark.asyncio
@pytest.mark.services
async def test_check_availability_when_calendar_is_free(mock_freebusy):
    set_busy(mock_freebusy, [])

    result = await availability_service.check_availability(dt(9), dt(10))

    assert result == {
        "available": True,
        "busy_periods": [],
    }
    mock_freebusy.freebusy.return_value.query.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.services
async def test_check_availability_when_busy_period_exists(mock_freebusy):
    busy = [
        {
            "start": "2026-11-10T09:30:00+05:30",
            "end": "2026-11-10T10:30:00+05:30",
        }
    ]
    set_busy(mock_freebusy, busy)

    result = await availability_service.check_availability(dt(10), dt(11))

    assert result["available"] is False
    assert result["busy_periods"] == busy


@pytest.mark.asyncio
@pytest.mark.services
async def test_check_availability_rejects_invalid_range(mock_freebusy):
    with pytest.raises(ValueError):
        await availability_service.check_availability(dt(12), dt(10))


@pytest.mark.asyncio
@pytest.mark.services
async def test_check_availability_raises_on_google_calendar_errors(
    mock_freebusy,
):
    set_busy(
        mock_freebusy,
        [],
        errors=[{"reason": "notFound"}],
    )

    with pytest.raises(
        CalendarFreeBusyError,
        match="Google Calendar could not retrieve availability",
    ):
        await availability_service.check_availability(
            dt(9),
            dt(10),
        )


@pytest.mark.asyncio
@pytest.mark.services
async def test_find_conflicts_returns_busy_periods(monkeypatch):
    expected = [{"start": "a", "end": "b"}]
    check = AsyncMock(
        return_value={
            "available": False,
            "busy_periods": expected,
        }
    )
    monkeypatch.setattr(
        availability_service,
        "check_availability",
        check,
    )

    result = await availability_service.find_conflicts(dt(9), dt(12))

    assert result == expected
    check.assert_awaited_once_with(dt(9), dt(12))


@pytest.mark.asyncio
@pytest.mark.services
async def test_get_available_slots_returns_expected_candidates(mock_freebusy):
    set_busy(
        mock_freebusy,
        [
            {
                "start": "2026-11-10T10:00:00+05:30",
                "end": "2026-11-10T11:00:00+05:30",
            }
        ],
    )

    result = await availability_service.get_available_slots(
        dt(9),
        dt(13),
        duration_minutes=60,
        slot_interval_minutes=15,
        max_suggestions=10,
    )

    expected = [
        {"start": dt(9).isoformat(), "end": dt(10).isoformat()},
        {"start": dt(11).isoformat(), "end": dt(12).isoformat()},
        {"start": dt(11, 15).isoformat(), "end": dt(12, 15).isoformat()},
        {"start": dt(11, 30).isoformat(), "end": dt(12, 30).isoformat()},
        {"start": dt(11, 45).isoformat(), "end": dt(12, 45).isoformat()},
        {"start": dt(12).isoformat(), "end": dt(13).isoformat()},
    ]

    assert result == expected


@pytest.mark.asyncio
@pytest.mark.services
async def test_get_available_slots_rejects_invalid_duration(mock_freebusy):
    for duration in (0, -1, 1441, True, 1.5):
        with pytest.raises(ValueError):
            await availability_service.get_available_slots(
                dt(9),
                dt(12),
                duration_minutes=duration,
            )


@pytest.mark.asyncio
@pytest.mark.services
async def test_get_available_slots_propagates_api_failure(mock_freebusy):
    request = mock_freebusy.freebusy.return_value.query.return_value
    request.execute.side_effect = RuntimeError("Google API failure")

    with pytest.raises(RuntimeError, match="Google API failure"):
        await availability_service.get_available_slots(
            dt(9),
            dt(10),
            30,
        )


@pytest.mark.asyncio
@pytest.mark.services
async def test_slots_respect_working_hours_and_skip_weekends(mock_freebusy):
    start = datetime(2026, 11, 13, 0, 0, tzinfo=TZ)
    end = datetime(2026, 11, 16, 23, 59, tzinfo=TZ)

    set_busy(
        mock_freebusy,
        [
            {
                "start": "2026-11-13T10:00:00+05:30",
                "end": "2026-11-13T17:00:00+05:30",
            }
        ],
    )

    result = await availability_service.get_available_slots(
        start,
        end,
        duration_minutes=90,
        slot_interval_minutes=15,
        max_suggestions=4,
        workday_start_time="10:00",
        workday_end_time="17:00",
        exclude_weekends=True,
    )

    assert len(result) == 4
    assert all(
        datetime.fromisoformat(slot["start"]).weekday() < 5
        for slot in result
    )
    mock_freebusy.freebusy.return_value.query.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.services
async def test_workday_end_must_be_later_than_start(mock_freebusy):
    start = datetime(2026, 11, 10, 0, 0, tzinfo=TZ)
    end = datetime(2026, 11, 10, 23, 59, tzinfo=TZ)

    with pytest.raises(ValueError, match="Working-hours end must be later"):
        await availability_service.get_available_slots(
            start,
            end,
            workday_start_time="17:00",
            workday_end_time="10:00",
        )
