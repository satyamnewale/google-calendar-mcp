from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock

import pytest

from services import availability_service

TZ = ZoneInfo("Asia/Kolkata")

@pytest.mark.services
def dt(hour, minute=0):
    return datetime(2026, 11, 10, hour, minute, tzinfo=TZ)


@pytest.fixture
def mock_freebusy(monkeypatch):
    service = MagicMock()
    monkeypatch.setattr(availability_service, "get_calendar_service", lambda: service)
    return service

@pytest.mark.services
def set_busy(service, periods, *, errors=None):
    calendar_data = {"busy": periods}
    if errors is not None:
        calendar_data["errors"] = errors
    service.freebusy.return_value.query.return_value.execute.return_value = {
        "calendars": {availability_service.CALENDAR_ID: calendar_data}
    }

@pytest.mark.services
def test_check_availability_when_calendar_is_free(mock_freebusy):
    
    set_busy(mock_freebusy, [])

    result = availability_service.check_availability(dt(9), dt(10))

    assert result == {"available": True, "busy_periods": []}
    mock_freebusy.freebusy.return_value.query.assert_called_once()

@pytest.mark.services
def test_check_availability_when_one_busy_period_exists(mock_freebusy):
    busy = [{"start": "2026-11-10T09:30:00+05:30",
             "end": "2026-11-10T10:30:00+05:30"}]
    set_busy(mock_freebusy, busy)

    result = availability_service.check_availability(dt(10), dt(11))

    assert result["available"] is False
    assert result["busy_periods"] == busy

@pytest.mark.services
def test_check_availability_when_multiple_busy_periods_exist(mock_freebusy):
    busy = [
        {"start": "2026-11-10T09:00:00+05:30", "end": "2026-11-10T10:00:00+05:30"},
        {"start": "2026-11-10T10:30:00+05:30", "end": "2026-11-10T11:30:00+05:30"},
    ]
    set_busy(mock_freebusy, busy)

    result = availability_service.check_availability(dt(9), dt(12))

    assert result["available"] is False
    assert len(result["busy_periods"]) == 2

@pytest.mark.services
def test_check_availability_rejects_invalid_range(mock_freebusy):
    with pytest.raises(ValueError):
        availability_service.check_availability(dt(12), dt(10))

@pytest.mark.services
def test_check_availability_raises_when_google_returns_calendar_errors(mock_freebusy):
    set_busy(mock_freebusy, [], errors=[{"reason": "notFound"}])

    with pytest.raises(RuntimeError, match="FreeBusy API returned errors"):
        availability_service.check_availability(dt(9), dt(10))

@pytest.mark.services
def test_find_conflicts_returns_busy_periods(monkeypatch):
    expected = [{"start": "a", "end": "b"}]
    monkeypatch.setattr(
        availability_service, "check_availability",
        lambda start, end: {"available": False, "busy_periods": expected},
    )

    assert availability_service.find_conflicts(dt(9), dt(12)) == expected

@pytest.mark.services
def test_get_available_slots_returns_free_windows(mock_freebusy):
    set_busy(mock_freebusy, [
        {"start": "2026-11-10T10:00:00+05:30",
         "end": "2026-11-10T11:00:00+05:30"}
    ])

    result = availability_service.get_available_slots(dt(9), dt(13), duration_minutes=60)

    assert result == [
        {"start": dt(9).isoformat(), "end": dt(10).isoformat()},
        {"start": dt(11).isoformat(), "end": dt(13).isoformat()},
    ]

@pytest.mark.services
def test_get_available_slots_excludes_windows_shorter_than_duration(mock_freebusy):
    set_busy(mock_freebusy, [
        {"start": "2026-11-10T09:30:00+05:30",
         "end": "2026-11-10T10:00:00+05:30"}
    ])

    result = availability_service.get_available_slots(dt(9), dt(10), duration_minutes=60)

    assert result == []

@pytest.mark.services
def test_get_available_slots_returns_empty_when_day_is_fully_busy(mock_freebusy):
    set_busy(mock_freebusy, [
        {"start": "2026-11-10T09:00:00+05:30",
         "end": "2026-11-10T13:00:00+05:30"}
    ])

    assert availability_service.get_available_slots(dt(9), dt(13), 30) == []


@pytest.mark.parametrize("duration", [0, -1, 1441, True, 1.5])
def test_get_available_slots_rejects_invalid_duration(mock_freebusy, duration):
    with pytest.raises(ValueError):
        availability_service.get_available_slots(dt(9), dt(12), duration)

@pytest.mark.services
def test_get_available_slots_propagates_freebusy_api_failure(mock_freebusy):
    mock_freebusy.freebusy.return_value.query.return_value.execute.side_effect = RuntimeError(
        "Google API failure"
    )

    with pytest.raises(RuntimeError, match="Google API failure"):
        availability_service.get_available_slots(dt(9), dt(10), 30)
