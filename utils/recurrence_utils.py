
VALID_FREQUENCIES = {
    "DAILY",
    "WEEKLY",
    "MONTHLY",
    "YEARLY",
}

VALID_DAYS = {
    "MO", "TU", "WE", "TH", "FR", "SA", "SU"
}


def build_recurrence_rule(
    frequency: str,
    interval: int = 1,
    byday: list[str] | None = None,
    count: int | None = None,
    until: str | None = None,
):
    frequency = frequency.upper()

    if frequency not in VALID_FREQUENCIES:
        raise ValueError("Invalid recurrence frequency.")

    if interval < 1:
        raise ValueError("Interval must be at least 1.")

    parts = [
        f"FREQ={frequency}",
        f"INTERVAL={interval}"
    ]

    if byday:
        days = [day.upper() for day in byday]

        if not set(days).issubset(VALID_DAYS):
            raise ValueError("Invalid weekday in recurrence rule.")

        parts.append(f"BYDAY={','.join(days)}")

    if count is not None:
        if count < 1:
            raise ValueError("Count must be at least 1.")

        if until:
            raise ValueError("Use either COUNT or UNTIL, not both.")

        parts.append(f"COUNT={count}")

    if until:
        parts.append(f"UNTIL={until}")

    return ["RRULE:" + ";".join(parts)]


def validate_recurrence_rule(rule: list[str]):
    if not isinstance(rule, list) or not rule:
        raise ValueError("Recurrence rule must be a non-empty list.")

    for item in rule:
        if not item.startswith("RRULE:"):
            raise ValueError("Only RRULE recurrence entries are supported.")

    return True


def get_occurrence_scope(scope: str):
    allowed = {"single", "future", "all"}

    if scope not in allowed:
        raise ValueError(
            "Scope must be single, future, or all."
        )

    return scope
