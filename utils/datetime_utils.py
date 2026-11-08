from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from dateutil import parser as date_parser

from config.settings import TIMEZONE, WEEK_START_DAY


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
            return first.replace(year=first.year + 1, month=1)

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

    if text.startswith("next "):
        day_name = text[5:].strip()

        if day_name in weekdays:
            target = weekdays[day_name]
            days_ahead = (target - today.weekday()) % 7

            # Next Monday means the Monday of the following week.
            return today + timedelta(days=days_ahead + (7 if days_ahead == 0 else 7))

    if text.startswith("this "):
        day_name = text[5:].strip()

        if day_name in weekdays:
            target = weekdays[day_name]
            days_ahead = (target - today.weekday()) % 7
            return today + timedelta(days=days_ahead)

    if text in weekdays:
        target = weekdays[text]
        days_ahead = (target - today.weekday()) % 7
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