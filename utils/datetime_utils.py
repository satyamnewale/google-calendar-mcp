from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from dateutil import parser as date_parser
import re

from config.settings import TIMEZONE, WEEK_START_DAY

# ==================================================
# CALENDAR EVENT SEARCH RANGE
# ==================================================

_SEARCH_TIME_PATTERN = re.compile(
    r"(?:"
    r"T\d{2}:\d{2}"
    r"|"
    r"\b\d{1,2}:\d{2}\b"
    r"|"
    r"\b\d{1,2}\s*(?:AM|PM)\b"
    r"|"
    r"\b(?:noon|midnight)\b"
    r")",
    re.IGNORECASE,
)

def get_timezone() -> ZoneInfo:
    """Return the configured local timezone."""
    return ZoneInfo(TIMEZONE)


def get_now() -> datetime:
    """Return the current timezone-aware datetime."""
    return datetime.now(get_timezone())


def parse_date(value: str | date) -> date:
    """Parse a date string or return an existing date."""
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if not isinstance(value, str) or not value.strip():
        raise ValueError("Date value cannot be empty.")

    text = value.strip().lower()

    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    if text in weekdays:
        today = get_now().date()
        days_ahead = (weekdays[text] - today.weekday()) % 7
        return today + timedelta(days=days_ahead)

    try:
        return date_parser.parse(value, fuzzy=False).date()
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"Invalid date value: {value}") from exc


def resolve_date_expression(expression: str | date) -> date:
    """Resolve common natural date expressions into a date."""

    if isinstance(expression, datetime):
        return expression.date()

    if isinstance(expression, date):
        return expression

    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("Date expression cannot be empty.")

    text = expression.strip().lower()
    today = get_now().date()

    simple_expressions = {
        "today": today,
        "tomorrow": today + timedelta(days=1),
        "yesterday": today - timedelta(days=1),
        "this week": today,
        "this month": today.replace(day=1),
    }

    if text in simple_expressions:
        return simple_expressions[text]

    if text == "next week":
        start, _ = get_week_range(today)
        return (start + timedelta(days=7)).date()

    if text == "next month":
        first = today.replace(day=1)

        if first.month == 12:
            return first.replace(
                year=first.year + 1,
                month=1,
            )

        return first.replace(month=first.month + 1)

    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    # Explicit "next Monday" means the next occurrence,
    # not necessarily the Monday of the following calendar week.
    if text.startswith("next "):

        day_name = text[5:].strip()

        if day_name in weekdays:

            target = weekdays[day_name]

            days_ahead = (
                target - today.weekday()
            ) % 7

            if days_ahead == 0:
                days_ahead = 7

            return today + timedelta(days=days_ahead)

    if text.startswith("this "):

        day_name = text[5:].strip()

        if day_name in weekdays:

            target = weekdays[day_name]

            days_ahead = (
                target - today.weekday()
            ) % 7

            return today + timedelta(days=days_ahead)

    if text in weekdays:

        target = weekdays[text]

        days_ahead = (
            target - today.weekday()
        ) % 7

        return today + timedelta(days=days_ahead)

    return parse_date(expression)


def parse_datetime(value: str | datetime) -> datetime:
    """
    Parse a datetime string and normalize it to the configured timezone.

    Naive datetime values are interpreted in the configured local timezone.
    """
    if isinstance(value, datetime):
        parsed = value
    else:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Datetime value cannot be empty.")

        try:
            parsed = date_parser.parse(value, fuzzy=False)
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError(f"Invalid datetime value: {value}") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=get_timezone())

    return parsed.astimezone(get_timezone())


def parse_date_or_datetime(
    value: str,
    all_day: bool = False,
) -> date | datetime:
    """Parse an input according to the event type."""
    if all_day:
        return resolve_date_expression(value)

    return parse_datetime(value)


def to_rfc3339(value: datetime) -> str:
    """Convert a datetime into RFC3339 format."""
    if not isinstance(value, datetime):
        raise ValueError("Expected a datetime value.")

    if value.tzinfo is None:
        value = value.replace(tzinfo=get_timezone())

    return value.astimezone(get_timezone()).isoformat()


def get_day_range(day_value: str | date) -> tuple[datetime, datetime]:
    """Return the start and exclusive end of a local calendar day."""
    day = (
        resolve_date_expression(day_value)
        if isinstance(day_value, str)
        else day_value
    )

    start = datetime.combine(day, time.min, tzinfo=get_timezone())
    end = start + timedelta(days=1)

    return start, end


def get_week_range(
    week_value: str | date | None = None,
) -> tuple[datetime, datetime]:
    """Return the configured week start and the following week start."""
    if week_value is None:
        day = get_now().date()
    elif isinstance(week_value, str):
        day = resolve_date_expression(week_value)
    else:
        day = week_value

    start_date = day - timedelta(
        days=(day.weekday() - WEEK_START_DAY) % 7
    )

    start = datetime.combine(
        start_date,
        time.min,
        tzinfo=get_timezone(),
    )

    return start, start + timedelta(days=7)


def get_month_range(
    month: str | date | None = None,
) -> tuple[datetime, datetime]:
    """Return the first day of a month and the first day of the next month."""
    if month is None:
        current = get_now().date()
        year, month_number = current.year, current.month

    elif isinstance(month, str):
        parsed = date_parser.parse(month, fuzzy=False)
        year, month_number = parsed.year, parsed.month

    else:
        year, month_number = month.year, month.month

    start = datetime(
        year,
        month_number,
        1,
        tzinfo=get_timezone(),
    )

    if month_number == 12:
        end = datetime(year + 1, 1, 1, tzinfo=get_timezone())
    else:
        end = datetime(year, month_number + 1, 1, tzinfo=get_timezone())

    return start, end


def _parse_search_boundary(
    value: str | date | datetime,
    is_end: bool = False,
) -> datetime:
    """
    Parse a calendar search boundary.

    Date-only start:
        2026-11-10 -> 2026-11-10 00:00

    Date-only end:
        2026-11-30 -> 2026-12-01 00:00

    The end date is inclusive at the public tool interface,
    while Google Calendar's timeMax is exclusive.

    Explicit datetime inputs remain exact upper/lower boundaries.
    """

    timezone = get_timezone()

    if isinstance(value, datetime):

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone)

        return value.astimezone(timezone)

    if isinstance(value, date):

        target_date = value

    elif isinstance(value, str):

        expression = value.strip()

        if not expression:
            raise ValueError(
                "Calendar search date cannot be empty."
            )

        has_explicit_time = bool(
            _SEARCH_TIME_PATTERN.search(expression)
        )

        if has_explicit_time:
            return parse_datetime(expression)

        target_date = resolve_date_expression(expression)

    else:

        raise ValueError(
            "Calendar search boundary must be a date or datetime string."
        )

    # Date-only end boundaries are inclusive.
    # Convert them to the following midnight because Google
    # Calendar uses an exclusive timeMax.
    if is_end:
        target_date += timedelta(days=1)

    return datetime.combine(
        target_date,
        time.min,
        tzinfo=timezone,
    )

def parse_search_range(
    start_value: str | date | datetime,
    end_value: str | date | datetime,
) -> tuple[datetime, datetime]:
    """
    Convert a public inclusive date range into Calendar API boundaries.

    Examples:

    2026-11-10 through 2026-11-30:

        start = 2026-11-10 00:00
        end   = 2026-12-01 00:00

    Explicit datetime ranges retain their supplied boundaries.
    """

    start = _parse_search_boundary(
        start_value,
        is_end=False,
    )

    end = _parse_search_boundary(
        end_value,
        is_end=True,
    )

    if start >= end:
        raise ValueError(
            "Calendar search end must be after its start."
        )

    return start, end