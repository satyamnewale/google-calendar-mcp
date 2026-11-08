import re
from itertools import islice
from datetime import (
    datetime,
    date,
    time,
    timedelta,
    timezone,
)

from dateutil.rrule import rrulestr

from utils.datetime_utils import (
    parse_datetime,
    get_timezone,
)

from config.settings import (
    MAX_RECURRENCE_OCCURRENCES,
    INDEFINITE_RECURRENCE_CHECK_DAYS,
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

VALID_RULE_COMPONENTS = {
    "FREQ",
    "INTERVAL",
    "COUNT",
    "UNTIL",
    "BYDAY",
}


def validate_recurrence_rule(
    rule: list[str],
    all_day: bool | None = None,
) -> bool:
    """
    Validate supported Google Calendar RRULE entries.

    all_day:
        True  -> UNTIL must be DATE format.
        False -> UNTIL must be UTC DATE-TIME format.
        None  -> Either format is accepted.
    """

    if not isinstance(rule, list) or len(rule) != 1:
        raise ValueError(
            "Exactly one RRULE entry is supported."
        )

    item = rule[0]

    if not isinstance(item, str) or not item.startswith("RRULE:"):
        raise ValueError(
            "Invalid recurrence rule format."
        )

    raw_rule = item.removeprefix("RRULE:")

    fields = {}

    for component in raw_rule.split(";"):

        if "=" not in component:
            raise ValueError(
                "Invalid recurrence rule component."
            )

        key, value = component.split("=", 1)

        key = key.upper()
        value = value.upper()

        if key not in VALID_RULE_COMPONENTS:
            raise ValueError(
                f"Unsupported recurrence component: {key}"
            )

        if key in fields:
            raise ValueError(
                f"Duplicate recurrence component: {key}"
            )

        if not value:
            raise ValueError(
                f"Empty recurrence component: {key}"
            )

        fields[key] = value

    # Frequency
    frequency = fields.get("FREQ")

    if frequency not in VALID_FREQUENCIES:
        raise ValueError(
            "Invalid or missing recurrence frequency."
        )

    # Interval
    interval = fields.get("INTERVAL", "1")

    try:
        interval_value = int(interval)
    except ValueError as exc:
        raise ValueError(
            "Recurrence interval must be an integer."
        ) from exc

    if not 1 <= interval_value <= 365:
        raise ValueError(
            "Recurrence interval must be between 1 and 365."
        )

    # Count
    count = fields.get("COUNT")

    if count is not None:

        try:
            count_value = int(count)
        except ValueError as exc:
            raise ValueError(
                "Recurrence count must be an integer."
            ) from exc

        if not 1 <= count_value <= MAX_RECURRENCE_OCCURRENCES:
            raise ValueError(
                f"Recurrence count must be between 1 and "
                f"{MAX_RECURRENCE_OCCURRENCES}."
            )

    # COUNT and UNTIL cannot coexist.
    until = fields.get("UNTIL")

    if count is not None and until is not None:
        raise ValueError(
            "COUNT and UNTIL cannot be combined."
        )

    # Weekdays
    byday = fields.get("BYDAY")

    if byday is not None:

        days = byday.split(",")

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
                "BYDAY is supported only for WEEKLY recurrence."
            )

    # UNTIL type
    if until is not None:

        is_date = bool(
            re.fullmatch(r"\d{8}", until)
        )

        is_utc_datetime = bool(
            re.fullmatch(
                r"\d{8}T\d{6}Z",
                until,
            )
        )

        if not is_date and not is_utc_datetime:
            raise ValueError(
                "UNTIL must be YYYYMMDD or YYYYMMDDTHHMMSSZ."
            )

        if all_day is True and not is_date:
            raise ValueError(
                "All-day recurrence requires DATE-formatted UNTIL."
            )

        if all_day is False and not is_utc_datetime:
            raise ValueError(
                "Timed recurrence requires UTC DATE-TIME UNTIL."
            )

    return True


def build_recurrence_rule(
    frequency: str,
    interval: int = 1,
    byday: list[str] | None = None,
    count: int | None = None,
    until: str | date | datetime | None = None,
    all_day: bool = False,
) -> list[str]:
    """
    Build a Google Calendar RRULE.

    COUNT:
        Total occurrences, including DTSTART.

    UNTIL:
        Inclusive final occurrence.

    All-day UNTIL:
        YYYYMMDD.

    Timed UNTIL:
        UTC YYYYMMDDTHHMMSSZ.
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
            or not 1 <= count <= MAX_RECURRENCE_OCCURRENCES
        ):
            raise ValueError(
                f"Recurrence count must be between 1 and "
                f"{MAX_RECURRENCE_OCCURRENCES}."
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
        parts.append(f"COUNT={count}")

    if until is not None:

        if isinstance(until, str):

            value = until.strip()

            try:
                until_value = date.fromisoformat(value)
            except ValueError:
                until_value = parse_datetime(value)

        elif isinstance(until, datetime):
            until_value = until

        elif isinstance(until, date):
            until_value = until

        else:
            raise ValueError(
                "Invalid recurrence end date."
            )

        if all_day:

            if isinstance(until_value, datetime):
                raise ValueError(
                    "All-day recurrence requires a date-only UNTIL value."
                )

            parts.append(
                f"UNTIL={until_value.strftime('%Y%m%d')}"
            )

        else:

            if isinstance(until_value, date) and not isinstance(
                until_value,
                datetime,
            ):
                until_value = datetime.combine(
                    until_value,
                    time.max,
                    tzinfo=get_timezone(),
                )

            elif until_value.tzinfo is None:
                until_value = until_value.replace(
                    tzinfo=get_timezone()
                )

            until_utc = until_value.astimezone(timezone.utc)

            parts.append(
                until_utc.strftime(
                    "UNTIL=%Y%m%dT%H%M%SZ"
                )
            )

    rule = [
        "RRULE:" + ";".join(parts)
    ]

    validate_recurrence_rule(
        rule,
        all_day=all_day,
    )

    return rule


def generate_occurrence_windows(
    start: datetime | date,
    end: datetime | date,
    recurrence: list[str] | None,
    all_day: bool = False,
    indefinite: bool = False,
) -> list[tuple[datetime, datetime]]:
    """
    Generate occurrence start/end pairs for conflict checking.

    For all-day events:
        start/end are dates.
        end is exclusive.

    For timed events:
        start/end are timezone-aware datetimes.

    Indefinite series are checked only within the configured horizon.
    """

    local_timezone = get_timezone()

    # --------------------------------------------------
    # Normalize the first occurrence
    # --------------------------------------------------

    if all_day:

        if isinstance(start, datetime):
            start = start.date()

        if isinstance(end, datetime):
            end = end.date()

        if not isinstance(start, date) or not isinstance(end, date):
            raise ValueError(
                "All-day recurrence requires date values."
            )

        duration_days = (end - start).days

        if duration_days < 1:
            raise ValueError(
                "All-day event end must be after start."
            )

        dtstart = datetime.combine(
            start,
            time.min,
        )

    else:

        if not isinstance(start, datetime) or not isinstance(end, datetime):
            raise ValueError(
                "Timed recurrence requires datetime values."
            )

        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError(
                "Timed recurrence requires timezone-aware values."
            )

        if start >= end:
            raise ValueError(
                "Event end must be after start."
            )

        duration = end - start
        dtstart = start

    # --------------------------------------------------
    # Generate occurrence starts
    # --------------------------------------------------

    if recurrence is None:

        occurrence_starts = [dtstart]

    else:

        validate_recurrence_rule(
            recurrence,
            all_day=all_day,
        )

        raw_rule = recurrence[0].removeprefix("RRULE:")

        has_count = "COUNT=" in raw_rule
        has_until = "UNTIL=" in raw_rule
        is_unbounded = not has_count and not has_until

        if is_unbounded != indefinite:
            raise ValueError(
                "Recurrence termination configuration does not match "
                "the recurrence rule."
            )

        parsed_rule = rrulestr(
            raw_rule,
            dtstart=dtstart,
        )

        if indefinite:

            horizon_end = dtstart + timedelta(
                days=INDEFINITE_RECURRENCE_CHECK_DAYS
            )

            occurrence_starts = parsed_rule.between(
                dtstart,
                horizon_end,
                inc=True,
            )

        else:

            occurrence_starts = list(
                islice(
                    parsed_rule,
                    MAX_RECURRENCE_OCCURRENCES + 1,
                )
            )

        if len(occurrence_starts) > MAX_RECURRENCE_OCCURRENCES:
            raise ValueError(
                "The recurrence exceeds the maximum number of "
                f"{MAX_RECURRENCE_OCCURRENCES} occurrences supported "
                "for conflict checking."
            )

    if not occurrence_starts:
        raise ValueError(
            "The recurrence does not produce any occurrences."
        )

    # --------------------------------------------------
    # Build occurrence windows
    # --------------------------------------------------

    windows = []

    for occurrence_start in occurrence_starts:

        if all_day:

            occurrence_date = occurrence_start.date()

            occurrence_start_local = datetime.combine(
                occurrence_date,
                time.min,
                tzinfo=local_timezone,
            )

            occurrence_end_local = (
                occurrence_start_local
                + timedelta(days=duration_days)
            )

            windows.append(
                (
                    occurrence_start_local,
                    occurrence_end_local,
                )
            )

        else:

            occurrence_start_local = occurrence_start.astimezone(
                local_timezone
            )

            occurrence_end_local = (
                occurrence_start_local + duration
            )

            windows.append(
                (
                    occurrence_start_local,
                    occurrence_end_local,
                )
            )

    return windows


def get_occurrence_scope(scope: str) -> str:
    """Validate the recurrence occurrence scope."""

    allowed = {
        "single",
        "future",
        "all",
    }

    if scope not in allowed:
        raise ValueError(
            "Scope must be single, future, or all."
        )

    return scope