from datetime import datetime, date, timezone

from utils.datetime_utils import parse_datetime, get_timezone


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
    """Validate the recurrence entries used by Google Calendar."""
    if not isinstance(rule, list) or not rule:
        raise ValueError("Recurrence rule must be a non-empty list.")

    for item in rule:
        if not isinstance(item, str) or not item.startswith("RRULE:"):
            raise ValueError("Only RRULE recurrence entries are supported.")

        components = item.removeprefix("RRULE:").split(";")

        for component in components:
            if "=" not in component:
                raise ValueError("Invalid recurrence rule component.")

            key, value = component.split("=", 1)

            if not key or not value:
                raise ValueError("Invalid recurrence rule component.")

    return True


def build_recurrence_rule(
    frequency: str,
    interval: int = 1,
    byday: list[str] | None = None,
    count: int | None = None,
    until: str | date | datetime | None = None,
) -> list[str]:
    """Build a Google Calendar RRULE recurrence entry."""
    if not isinstance(frequency, str):
        raise ValueError("Recurrence frequency must be a string.")

    frequency = frequency.upper()

    if frequency not in VALID_FREQUENCIES:
        raise ValueError(
            f"Invalid recurrence frequency: {frequency}"
        )

    if not isinstance(interval, int) or isinstance(interval, bool):
        raise ValueError("Recurrence interval must be an integer.")

    if not 1 <= interval <= 365:
        raise ValueError("Recurrence interval must be between 1 and 365.")

    parts = [
        f"FREQ={frequency}",
        f"INTERVAL={interval}",
    ]

    if byday:
        days = [day.upper() for day in byday]

        if len(days) != len(set(days)):
            raise ValueError("Duplicate recurrence weekdays are not allowed.")

        if not set(days).issubset(VALID_DAYS):
            raise ValueError("Invalid weekday in recurrence rule.")

        if frequency != "WEEKLY":
            raise ValueError("Weekday selection is supported only for WEEKLY recurrence.")

        parts.append(f"BYDAY={','.join(days)}")

    if count is not None:
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError("Recurrence count must be a positive integer.")

        if until is not None:
            raise ValueError("Use either COUNT or UNTIL, not both.")

        parts.append(f"COUNT={count}")

    if until is not None:
        if isinstance(until, datetime):
            until_value = until
        elif isinstance(until, date):
            until_value = datetime.combine(
                until,
                datetime.max.time(),
                tzinfo=get_timezone(),
            )
        else:
            until_value = parse_datetime(until)

        until_utc = until_value.astimezone(timezone.utc)

        parts.append(until_utc.strftime("UNTIL=%Y%m%dT%H%M%SZ"))

    rule = ["RRULE:" + ";".join(parts)]

    validate_recurrence_rule(rule)

    return rule


def get_occurrence_scope(scope: str) -> str:
    """Validate the recurrence occurrence scope."""
    allowed = {"single", "future", "all"}

    if scope not in allowed:
        raise ValueError("Scope must be single, future, or all.")

    return scope