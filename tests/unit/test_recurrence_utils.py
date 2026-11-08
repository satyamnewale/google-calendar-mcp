
import pytest

from utils.recurrence_utils import (
    build_recurrence_rule,
    validate_recurrence_rule,
    get_occurrence_scope,
)

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
