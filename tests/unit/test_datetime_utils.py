
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from utils.datetime_utils import (
    get_timezone,
    get_now,
    parse_date,
    parse_datetime,
    parse_date_or_datetime,
    resolve_date_expression,
    get_day_range,
    get_week_range,
    get_month_range,
    to_rfc3339,
    parse_search_range,
)

from utils import datetime_utils

TIMEZONE = ZoneInfo("Asia/Kolkata")

@pytest.mark.unit
def test_get_timezone():
    assert get_timezone().key == "Asia/Kolkata"

@pytest.mark.unit
def test_get_now_returns_aware_datetime():
    result = get_now()

    assert isinstance(result, datetime)
    assert result.tzinfo is not None
    assert result.tzinfo.key == "Asia/Kolkata"

@pytest.mark.unit
def test_parse_valid_date():
    result = parse_date("2026-11-10")

    assert result == date(2026, 11, 10)

@pytest.mark.unit
def test_parse_invalid_date():
    with pytest.raises((ValueError, TypeError)):
        parse_date("invalid-date")

@pytest.mark.unit
def test_parse_valid_datetime():
    result = parse_datetime("2026-11-10T10:00:00")

    assert isinstance(result, datetime)
    assert result.year == 2026
    assert result.month == 11
    assert result.day == 10

@pytest.mark.unit
def test_parse_naive_datetime_assigns_timezone():
    result = parse_datetime("2026-11-10T10:00:00")

    assert result.tzinfo is not None
    assert result.utcoffset() == timedelta(hours=5, minutes=30)

@pytest.mark.unit
def test_parse_utc_datetime_converts_to_local_timezone():
    result = parse_datetime("2026-11-10T04:30:00+00:00")

    assert result.hour == 10
    assert result.minute == 0
    assert result.tzinfo.key == "Asia/Kolkata"

@pytest.mark.unit
def test_parse_date_or_datetime_for_all_day_event():
    result = parse_date_or_datetime(
        "2026-11-10",
        all_day=True,
    )

    assert result == date(2026, 11, 10)

@pytest.mark.unit
def test_parse_date_or_datetime_for_timed_event():
    result = parse_date_or_datetime(
        "2026-11-10T10:00:00",
        all_day=False,
    )

    assert isinstance(result, datetime)

@pytest.mark.unit
def test_resolve_today():
    result = resolve_date_expression("today")

    assert result == get_now().date()

@pytest.mark.unit
def test_resolve_tomorrow():
    result = resolve_date_expression("tomorrow")

    assert result == get_now().date() + timedelta(days=1)

@pytest.mark.unit
def test_resolve_yesterday():
    result = resolve_date_expression("yesterday")

    assert result == get_now().date() - timedelta(days=1)

@pytest.mark.unit
def test_resolve_next_week():
    result = resolve_date_expression("next week")

    assert isinstance(result, date)

@pytest.mark.unit
def test_resolve_next_month():
    result = resolve_date_expression("next month")

    assert isinstance(result, date)

@pytest.mark.unit
def test_resolve_weekday_expression():
    result = resolve_date_expression("next Monday")

    assert isinstance(result, date)
    assert result.weekday() == 0

@pytest.mark.unit
def test_get_day_range():
    start, end = get_day_range("2026-11-10")

    assert start.date() == date(2026, 11, 10)
    assert end.date() == date(2026, 11, 11)
    assert start.tzinfo is not None
    assert end.tzinfo is not None

@pytest.mark.unit
def test_get_week_range():
    start, end = get_week_range("2026-11-10")

    assert start.weekday() == 0
    assert end.weekday() == 0
    assert (end - start).days == 7

@pytest.mark.unit
def test_get_month_range():
    start, end = get_month_range("2026-11")

    assert start.date() == date(2026, 11, 1)
    assert end.date() == date(2026, 12, 1)

@pytest.mark.unit
def test_to_rfc3339():
    value = datetime(2026, 11, 10, 10, 0)

    result = to_rfc3339(value)

    assert "2026-11-10T10:00:00" in result
    assert "+05:30" in result

@pytest.mark.unit
def test_parse_empty_date():
    with pytest.raises((ValueError, TypeError)):
        parse_date("")

@pytest.mark.unit
def test_next_monday_on_sunday(monkeypatch):

    monkeypatch.setattr(
        datetime_utils,
        "get_now",
        lambda: datetime(
            2026, 11, 8, 10, 0,
            tzinfo=ZoneInfo("Asia/Kolkata"),
        ),
    )

    result = datetime_utils.resolve_date_expression(
        "next Monday"
    )

    assert result == date(2026, 11, 9)


@pytest.mark.unit
def test_next_monday_on_tuesday(monkeypatch):

    monkeypatch.setattr(
        datetime_utils,
        "get_now",
        lambda: datetime(
            2026, 11, 10, 10, 0,
            tzinfo=ZoneInfo("Asia/Kolkata"),
        ),
    )

    result = datetime_utils.resolve_date_expression(
        "next Monday"
    )

    assert result == date(2026, 11, 16)


@pytest.mark.unit
def test_next_monday_on_monday(monkeypatch):

    monkeypatch.setattr(
        datetime_utils,
        "get_now",
        lambda: datetime(
            2026, 11, 9, 10, 0,
            tzinfo=ZoneInfo("Asia/Kolkata"),
        ),
    )

    result = datetime_utils.resolve_date_expression(
        "next Monday"
    )

    assert result == date(2026, 11, 16)


@pytest.mark.unit
def test_parse_search_range_includes_entire_end_date():

    start, end = parse_search_range(
        "2026-11-10",
        "2026-11-30",
    )

    assert start == datetime(
        2026, 11, 10, 0, 0,
        tzinfo=TIMEZONE,
    )

    assert end == datetime(
        2026, 12, 1, 0, 0,
        tzinfo=TIMEZONE,
    )

@pytest.mark.unit
def test_parse_search_range_preserves_explicit_datetime():

    start, end = parse_search_range(
        "2026-11-10T10:00:00+05:30",
        "2026-11-10T11:00:00+05:30",
    )

    assert start == datetime(
        2026, 11, 10, 10, 0,
        tzinfo=TIMEZONE,
    )

    assert end == datetime(
        2026, 11, 10, 11, 0,
        tzinfo=TIMEZONE,
    )

@pytest.mark.unit
def test_parse_search_range_supports_relative_date():

    start, end = parse_search_range(
        "2026-11-10",
        "2026-11-30",
    )

    assert start.date() == date(2026, 11, 10)
    assert end.date() == date(2026, 12, 1)

@pytest.mark.unit
def test_parse_search_range_rejects_invalid_range():

    with pytest.raises(ValueError):
        parse_search_range(
            "2026-11-30",
            "2026-11-10",
        )