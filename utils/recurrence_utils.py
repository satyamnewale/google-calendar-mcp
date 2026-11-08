from datetime import datetime, date, timezone

from utils.datetime_utils import (
    parse_datetime,
    get_timezone,
)


VALID_FREQUENCIES = {
    "DAILY",
    "WEEKLY",
    "MONTHLY",
    "YEARLY",
}

VALID_DAYS = {
    "MO", "TU", "WE", "TH", "FR", "SA", "SU"
}


def validate_recurrence_rule(rule: list[str]) -> bool:
    """Validate recurrence entries used by Google Calendar."""

    if not isinstance(rule, list) or not rule:
        raise ValueError(
            "Recurrence rule must be a non-empty list."
        )

    for item in rule:

        if not isinstance(item, str) or not item.startswith("RRULE:"):
            raise ValueError(
                "Only RRULE recurrence entries are supported."
            )

        components = item.removeprefix("RRULE:").split(";")

        for component in components:

            if "=" not in component:
                raise ValueError(
                    "Invalid recurrence rule component."
                )

            key, value = component.split("=", 1)

            if not key or not value:
                raise ValueError(
                    "Invalid recurrence rule component."
                )

    return True


def build_recurrence_rule(
    frequency: str,
    interval: int = 1,
    byday: list[str] | None = None,
    count: int | None = None,
    until: str | date | datetime | None = None,
) -> list[str]:
    """
    Build a Google Calendar RRULE.

    COUNT includes the first occurrence.

    UNTIL is inclusive. For a date-only value, the complete
    local calendar day is included.
    """

    if not isinstance(frequency, str):
        raise ValueError(
            "Recurrence frequency must be a string."
        )

    frequency = frequency.upper()

    if frequency not in VALID_FREQUENCIES:
        raise ValueError(
            f"Invalid recurrence frequency: {frequency}"
        )

    if (
        not isinstance(interval, int)
        or isinstance(interval, bool)
    ):
        raise ValueError(
            "Recurrence interval must be an integer."
        )

    if not 1 <= interval <= 365:
        raise ValueError(
            "Recurrence interval must be between 1 and 365."
        )

    if count is not None:

        if (
            not isinstance(count, int)
            or isinstance(count, bool)
            or count < 1
        ):
            raise ValueError(
                "Recurrence count must be a positive integer."
            )

    if count is not None and until is not None:
        raise ValueError(
            "Use either COUNT or UNTIL, not both."
        )

    parts = [
        f"FREQ={frequency}",
        f"INTERVAL={interval}",
    ]

    if byday:

        days = [day.upper() for day in byday]

        if len(days) != len(set(days)):
            raise ValueError(
                "Duplicate recurrence weekdays are not allowed."
            )

        if not set(days).issubset(VALID_DAYS):
            raise ValueError(
                "Invalid weekday in recurrence rule."
            )

        if frequency != "WEEKLY":
            raise ValueError(
                "Weekday selection is supported only for WEEKLY recurrence."
            )

        parts.append(
            f"BYDAY={','.join(days)}"
        )

    if count is not None:

        parts.append(
            f"COUNT={count}"
        )

    if until is not None:

        if isinstance(until, str):

            value = until.strip()

            # Date-only input: include the entire local day.
            try:
                until_value = date.fromisoformat(value)
            except ValueError:
                # Datetime input.
                until_value = parse_datetime(value)

        elif isinstance(until, datetime):
            until_value = until

        elif isinstance(until, date):
            until_value = until

        else:
            raise ValueError(
                "Invalid recurrence end date."
            )

        if isinstance(until_value, date) and not isinstance(
            until_value, datetime
        ):
            until_value = datetime.combine(
                until_value,
                datetime.max.time(),
                tzinfo=get_timezone(),
            )

        elif until_value.tzinfo is None:
            until_value = until_value.replace(
                tzinfo=get_timezone()
            )

        until_utc = until_value.astimezone(timezone.utc)

        parts.append(
            until_utc.strftime("UNTIL=%Y%m%dT%H%M%SZ")
        )

    rule = [
        "RRULE:" + ";".join(parts)
    ]

    validate_recurrence_rule(rule)

    return rule


def get_occurrence_scope(scope: str) -> str:
    """Validate the recurrence occurrence scope."""

    allowed = {"single", "future", "all"}

    if scope not in allowed:
        raise ValueError(
            "Scope must be single, future, or all."
        )

    return scope