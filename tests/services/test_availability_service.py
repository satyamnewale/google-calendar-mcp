from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock

import pytest

from services import availability_service

from services.availability_service import (
    find_occurrence_conflicts,
)

TZ = ZoneInfo("Asia/Kolkata")


@pytest.mark.services
def test_detects_conflict_in_later_recurrence():

    occurrences = [
        (
            datetime(2026, 11, 9, 15, 30, tzinfo=TZ),
            datetime(2026, 11, 9, 16, 30, tzinfo=TZ),
        ),
        (
            datetime(2026, 11, 10, 15, 30, tzinfo=TZ),
            datetime(2026, 11, 10, 16, 30, tzinfo=TZ),
        ),
        (
            datetime(2026, 11, 11, 15, 30, tzinfo=TZ),
            datetime(2026, 11, 11, 16, 30, tzinfo=TZ),
        ),
    ]

    busy_periods = [
        {
            "start": "2026-11-10T15:45:00+05:30",
            "end": "2026-11-10T16:00:00+05:30",
        }
    ]

    conflicts = find_occurrence_conflicts(
        occurrences,
        busy_periods,
    )

    assert len(conflicts) == 1

    assert conflicts[0]["occurrence"]["start"].startswith("2026-11-10")


@pytest.mark.services
def test_no_conflict_when_busy_period_is_between_occurrences():

    occurrences = [
        (
            datetime(2026, 11, 9, 15, 30, tzinfo=TZ),
            datetime(2026, 11, 9, 16, 30, tzinfo=TZ),
        ),
        (
            datetime(2026, 11, 10, 15, 30, tzinfo=TZ),
            datetime(2026, 11, 10, 16, 30, tzinfo=TZ),
        ),
    ]

    busy_periods = [
        {
            "start": "2026-11-09T18:00:00+05:30",
            "end": "2026-11-09T19:00:00+05:30",
        }
    ]

    conflicts = find_occurrence_conflicts(
        occurrences,
        busy_periods,
    )

    assert conflicts == []


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
    busy = [{"start": "2026-11-10T09:30:00+05:30", "end": "2026-11-10T10:30:00+05:30"}]
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
        availability_service,
        "check_availability",
        lambda start, end: {"available": False, "busy_periods": expected},
    )

    assert availability_service.find_conflicts(dt(9), dt(12)) == expected


@pytest.mark.services
def test_get_available_slots_returns_fixed_duration_candidates(
    mock_freebusy,
):
    set_busy(
        mock_freebusy,
        [
            {
                "start": "2026-11-10T10:00:00+05:30",
                "end": "2026-11-10T11:00:00+05:30",
            }
        ],
    )

    result = availability_service.get_available_slots(
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


@pytest.mark.services
def test_get_available_slots_excludes_windows_shorter_than_duration(mock_freebusy):
    set_busy(
        mock_freebusy,
        [{"start": "2026-11-10T09:30:00+05:30", "end": "2026-11-10T10:00:00+05:30"}],
    )

    result = availability_service.get_available_slots(
        dt(9), dt(10), duration_minutes=60
    )

    assert result == []


@pytest.mark.services
def test_get_available_slots_returns_empty_when_day_is_fully_busy(mock_freebusy):
    set_busy(
        mock_freebusy,
        [{"start": "2026-11-10T09:00:00+05:30", "end": "2026-11-10T13:00:00+05:30"}],
    )

    assert availability_service.get_available_slots(dt(9), dt(13), 30) == []


@pytest.mark.parametrize("duration", [0, -1, 1441, True, 1.5])
def test_get_available_slots_rejects_invalid_duration(mock_freebusy, duration):
    with pytest.raises(ValueError):
        availability_service.get_available_slots(dt(9), dt(12), duration)


@pytest.mark.services
def test_get_available_slots_propagates_freebusy_api_failure(mock_freebusy):
    mock_freebusy.freebusy.return_value.query.return_value.execute.side_effect = (
        RuntimeError("Google API failure")
    )

    with pytest.raises(RuntimeError, match="Google API failure"):
        availability_service.get_available_slots(dt(9), dt(10), 30)


@pytest.mark.services
def test_get_available_slots_returns_fixed_duration_slots(mock_freebusy):

    set_busy(
        mock_freebusy,
        [
            {
                "start": "2026-11-10T10:00:00+05:30",
                "end": "2026-11-10T11:00:00+05:30",
            }
        ],
    )

    result = availability_service.get_available_slots(
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


@pytest.mark.services
def test_slots_never_overlap_busy_period(mock_freebusy):

    set_busy(
        mock_freebusy,
        [
            {
                "start": dt(10, 30).isoformat(),
                "end": dt(11, 30).isoformat(),
            }
        ],
    )

    result = availability_service.get_available_slots(
        dt(10),
        dt(12),
        duration_minutes=45,
        slot_interval_minutes=15,
        max_suggestions=10,
    )

    for slot in result:

        slot_start = datetime.fromisoformat(slot["start"])
        slot_end = datetime.fromisoformat(slot["end"])

        assert slot_end - slot_start == timedelta(minutes=45)

        assert slot_end <= dt(10, 30) or slot_start >= dt(11, 30)


@pytest.mark.services
def test_slots_respect_working_hours_and_skip_weekends(
    mock_freebusy,
):

    start = datetime(
        2026,
        11,
        13,
        0,
        0,
        tzinfo=TZ,
    )

    end = datetime(
        2026,
        11,
        16,
        23,
        59,
        tzinfo=TZ,
    )

    # Friday is completely busy during working hours.
    set_busy(
        mock_freebusy,
        [
            {
                "start": "2026-11-13T10:00:00+05:30",
                "end": "2026-11-13T17:00:00+05:30",
            }
        ],
    )

    result = availability_service.get_available_slots(
        start,
        end,
        duration_minutes=90,
        slot_interval_minutes=15,
        max_suggestions=4,
        workday_start_time="10:00",
        workday_end_time="17:00",
        exclude_weekends=True,
    )

    expected = [
        {
            "start": "2026-11-16T10:00:00+05:30",
            "end": "2026-11-16T11:30:00+05:30",
        },
        {
            "start": "2026-11-16T10:15:00+05:30",
            "end": "2026-11-16T11:45:00+05:30",
        },
        {
            "start": "2026-11-16T10:30:00+05:30",
            "end": "2026-11-16T12:00:00+05:30",
        },
        {
            "start": "2026-11-16T10:45:00+05:30",
            "end": "2026-11-16T12:15:00+05:30",
        },
    ]

    assert result == expected

    # One FreeBusy API request for the entire range.
    mock_freebusy.freebusy.return_value.query.assert_called_once()


@pytest.mark.services
def test_slots_never_exceed_workday_end(mock_freebusy):

    start = datetime(
        2026,
        11,
        10,
        0,
        0,
        tzinfo=TZ,
    )

    end = datetime(
        2026,
        11,
        10,
        23,
        59,
        tzinfo=TZ,
    )

    set_busy(mock_freebusy, [])

    result = availability_service.get_available_slots(
        start,
        end,
        duration_minutes=90,
        slot_interval_minutes=15,
        max_suggestions=50,
        workday_start_time="10:00",
        workday_end_time="17:00",
        exclude_weekends=True,
    )

    for slot in result:

        slot_start = datetime.fromisoformat(slot["start"])

        slot_end = datetime.fromisoformat(slot["end"])

        assert slot_start.hour >= 10

        assert slot_end.hour < 17 or (slot_end.hour == 17 and slot_end.minute == 0)

        assert slot_end - slot_start == timedelta(minutes=90)

        assert slot_start.weekday() < 5


@pytest.mark.services
def test_weekend_exclusion_requires_working_hours(mock_freebusy):

    start = datetime(
        2026,
        11,
        10,
        0,
        0,
        tzinfo=TZ,
    )

    end = datetime(
        2026,
        11,
        17,
        23,
        59,
        tzinfo=TZ,
    )

    with pytest.raises(
        ValueError,
        match="Weekend exclusion requires working-hours",
    ):

        availability_service.get_available_slots(
            start,
            end,
            exclude_weekends=True,
        )


@pytest.mark.services
def test_workday_end_must_be_later_than_start(mock_freebusy):

    start = datetime(
        2026,
        11,
        10,
        0,
        0,
        tzinfo=TZ,
    )

    end = datetime(
        2026,
        11,
        10,
        23,
        59,
        tzinfo=TZ,
    )

    with pytest.raises(
        ValueError,
        match="Working-hours end must be later",
    ):

        availability_service.get_available_slots(
            start,
            end,
            workday_start_time="17:00",
            workday_end_time="10:00",
        )
