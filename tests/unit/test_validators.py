
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from utils.validators import (
    validate_title,
    validate_event_time,
    validate_date_range,
    validate_event_update,
)

@pytest.mark.unit
def test_valid_title():
    assert validate_title("Team Meeting") is not None


@pytest.mark.parametrize(
    "title",
    ["", "   ", None],
)
def test_invalid_title(title):
    with pytest.raises((ValueError, TypeError)):
        validate_title(title)

@pytest.mark.unit
def test_title_exceeds_maximum_length():
    with pytest.raises(ValueError):
        validate_title("A" * 201)

@pytest.mark.unit
def test_valid_timed_event():
    timezone = ZoneInfo("Asia/Kolkata")

    start = datetime(2026, 11, 10, 10, 0, tzinfo=timezone)
    end = datetime(2026, 11, 10, 11, 0, tzinfo=timezone)

    result = validate_event_time(start, end)

    assert result is True

@pytest.mark.unit
def test_end_before_start():
    timezone = ZoneInfo("Asia/Kolkata")

    start = datetime(2026, 11, 10, 12, 0, tzinfo=timezone)
    end = datetime(2026, 11, 10, 11, 0, tzinfo=timezone)

    with pytest.raises(ValueError, match="End time must be after start time"):
        validate_event_time(start, end)

@pytest.mark.unit
def test_naive_datetime_validation():
    start = datetime(2026, 11, 10, 10, 0)
    end = datetime(2026, 11, 10, 11, 0)

    with pytest.raises(ValueError, match="timezone information"):
        validate_event_time(start, end)

@pytest.mark.unit
def test_valid_all_day_event():
    start = date(2026, 11, 10)
    end = date(2026, 11, 11)

    result = validate_date_range(start, end)

    assert result is not False

@pytest.mark.unit
def test_same_start_and_end_date():
    start = date(2026, 11, 10)
    end = date(2026, 11, 10)

    with pytest.raises(ValueError):
        validate_date_range(start, end)

@pytest.mark.unit
def test_end_date_before_start_date():
    start = date(2026, 11, 12)
    end = date(2026, 11, 10)

    with pytest.raises(ValueError):
        validate_date_range(start, end)

@pytest.mark.unit
def test_valid_event_update():
    updates = {
        "summary": "Updated Meeting",
        "description": "Updated agenda",
        "location": "Conference Room",
    }

    result = validate_event_update(updates)

    assert result is not None

@pytest.mark.unit
def test_empty_event_update():
    with pytest.raises(ValueError):
        validate_event_update({})

@pytest.mark.unit
def test_unsupported_update_field():
    updates = {
        "invalid_field": "some value",
    }

    with pytest.raises(ValueError):
        validate_event_update(updates)

@pytest.mark.unit
def test_only_start_supplied():
    updates = {
        "start": {
            "dateTime": "2026-11-10T10:00:00+05:30",
        },
    }

    with pytest.raises(ValueError):
        validate_event_update(updates)

@pytest.mark.unit
def test_only_end_supplied():
    updates = {
        "end": {
            "dateTime": "2026-11-10T11:00:00+05:30",
        },
    }

    with pytest.raises(ValueError):
        validate_event_update(updates)

@pytest.mark.unit
def test_mismatched_start_and_end_types():
    updates = {
        "start": {
            "date": "2026-11-10",
        },
        "end": {
            "dateTime": "2026-11-11T10:00:00+05:30",
        },
    }

    with pytest.raises(ValueError):
        validate_event_update(updates)

@pytest.mark.unit
def test_invalid_update_time_range():
    updates = {
        "start": {
            "dateTime": "2026-11-10T12:00:00+05:30",
        },
        "end": {
            "dateTime": "2026-11-10T11:00:00+05:30",
        },
    }

    with pytest.raises(ValueError):
        validate_event_update(updates)
