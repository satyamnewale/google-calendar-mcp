from utils.recurrence_utils import (
    build_recurrence_rule,
    validate_recurrence_rule,
    get_occurrence_scope,
)

import pytest

from datetime import date, datetime
from zoneinfo import ZoneInfo

from utils.recurrence_utils import (
    build_recurrence_rule,
    generate_occurrence_windows,
    validate_recurrence_rule,
)


TZ = ZoneInfo("Asia/Kolkata")


@pytest.mark.unit
def test_daily_recurrence_count_generates_correct_occurrences():

    start = datetime(
        2026, 11, 9, 15, 30,
        tzinfo=TZ,
    )

    end = datetime(
        2026, 11, 9, 16, 30,
        tzinfo=TZ,
    )

    rule = build_recurrence_rule(
        frequency="DAILY",
        interval=1,
        count=21,
    )

    occurrences = generate_occurrence_windows(
        start,
        end,
        rule,
    )

    assert len(occurrences) == 21

    assert occurrences[0][0] == start

    assert occurrences[-1][0].date() == date(
        2026, 11, 29
    )


@pytest.mark.unit
def test_all_day_recurrence_uses_date_until():

    rule = build_recurrence_rule(
        frequency="DAILY",
        until="2026-11-29",
        all_day=True,
    )

    assert rule == [
        "RRULE:FREQ=DAILY;INTERVAL=1;UNTIL=20261129"
    ]


@pytest.mark.unit
def test_timed_recurrence_uses_utc_until():

    rule = build_recurrence_rule(
        frequency="DAILY",
        until="2026-11-29",
        all_day=False,
    )

    assert "UNTIL=" in rule[0]

    assert rule[0].endswith("Z")


@pytest.mark.unit
def test_all_day_recurrence_generates_dates():

    start = date(2026, 11, 9)
    end = date(2026, 11, 10)

    rule = build_recurrence_rule(
        frequency="DAILY",
        count=3,
        all_day=True,
    )

    occurrences = generate_occurrence_windows(
        start,
        end,
        rule,
        all_day=True,
    )

    assert len(occurrences) == 3

    assert occurrences[0][0].date() == start

    assert occurrences[-1][0].date() == date(
        2026, 11, 11
    )

    # All-day event end is the next midnight.
    assert occurrences[0][1].hour == 0


@pytest.mark.unit
def test_recurrence_rule_rejects_duplicate_components():

    with pytest.raises(ValueError):

        validate_recurrence_rule([
            "RRULE:FREQ=DAILY;FREQ=WEEKLY"
        ])


@pytest.mark.unit
def test_recurrence_rule_rejects_invalid_interval():

    with pytest.raises(ValueError):

        validate_recurrence_rule([
            "RRULE:FREQ=DAILY;INTERVAL=-10"
        ])


@pytest.mark.unit
def test_recurrence_rule_rejects_count_and_until():

    with pytest.raises(ValueError):

        validate_recurrence_rule([
            "RRULE:FREQ=DAILY;COUNT=5;UNTIL=20261129"
        ])


@pytest.mark.unit
def test_indefinite_recurrence_is_bounded_for_conflict_checking():

    start = datetime(
        2026, 11, 9, 15, 30,
        tzinfo=TZ,
    )

    end = datetime(
        2026, 11, 9, 16, 30,
        tzinfo=TZ,
    )

    rule = build_recurrence_rule(
        frequency="DAILY",
    )

    occurrences = generate_occurrence_windows(
        start,
        end,
        rule,
        indefinite=True,
    )

    assert len(occurrences) <= 91

    assert occurrences[0][0] == start

@pytest.mark.unit
def test_daily_recurrence():
    result = build_recurrence_rule("DAILY")

    assert result == ["RRULE:FREQ=DAILY;INTERVAL=1"]

@pytest.mark.unit
def test_weekly_recurrence():
    result = build_recurrence_rule("WEEKLY")

    assert result == ["RRULE:FREQ=WEEKLY;INTERVAL=1"]

@pytest.mark.unit
def test_monthly_recurrence():
    result = build_recurrence_rule("MONTHLY")

    assert result == ["RRULE:FREQ=MONTHLY;INTERVAL=1"]

@pytest.mark.unit
def test_yearly_recurrence():
    result = build_recurrence_rule("YEARLY")

    assert result == ["RRULE:FREQ=YEARLY;INTERVAL=1"]

@pytest.mark.unit
def test_recurrence_interval():
    result = build_recurrence_rule(
        frequency="DAILY",
        interval=2,
    )

    assert "INTERVAL=2" in result[0]

@pytest.mark.unit
def test_weekly_recurrence_with_days():
    result = build_recurrence_rule(
        frequency="WEEKLY",
        byday=["MO", "WE"],
    )

    assert "BYDAY=MO,WE" in result[0]

@pytest.mark.unit
def test_invalid_frequency():
    with pytest.raises(ValueError):
        build_recurrence_rule("HOURLY")

@pytest.mark.unit
def test_zero_interval():
    with pytest.raises(ValueError):
        build_recurrence_rule(
            frequency="DAILY",
            interval=0,
        )

@pytest.mark.unit
def test_interval_above_limit():
    with pytest.raises(ValueError):
        build_recurrence_rule(
            frequency="DAILY",
            interval=366,
        )

@pytest.mark.unit
def test_invalid_weekday():
    with pytest.raises(ValueError):
        build_recurrence_rule(
            frequency="WEEKLY",
            byday=["XX"],
        )

@pytest.mark.unit
def test_duplicate_weekdays():
    with pytest.raises(ValueError):
        build_recurrence_rule(
            frequency="WEEKLY",
            byday=["MO", "MO"],
        )

@pytest.mark.unit
def test_byday_with_daily_frequency():
    with pytest.raises(ValueError):
        build_recurrence_rule(
            frequency="DAILY",
            byday=["MO", "WE"],
        )

@pytest.mark.unit
def test_recurrence_count():
    result = build_recurrence_rule(
        frequency="DAILY",
        count=5,
    )

    assert "COUNT=5" in result[0]

@pytest.mark.unit
def test_count_and_until_cannot_be_combined():
    with pytest.raises(ValueError):
        build_recurrence_rule(
            frequency="DAILY",
            count=5,
            until="2026-12-31",
        )

@pytest.mark.unit
def test_validate_valid_recurrence_rule():
    result = validate_recurrence_rule(
        ["RRULE:FREQ=DAILY;INTERVAL=1"]
    )

    assert result is not False

@pytest.mark.unit
def test_validate_invalid_recurrence_rule():
    with pytest.raises((ValueError, TypeError)):
        validate_recurrence_rule(["INVALID"])


@pytest.mark.parametrize(
    "scope",
    ["single", "future", "all"],
)
def test_valid_occurrence_scope(scope):
    result = get_occurrence_scope(scope)

    assert result == scope

@pytest.mark.unit
def test_invalid_occurrence_scope():
    with pytest.raises(ValueError):
        get_occurrence_scope("everything")
