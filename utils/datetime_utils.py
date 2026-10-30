
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from dateutil import parser as date_parser

from config.settings import TIMEZONE, WEEK_START_DAY


def get_timezone():
    return ZoneInfo(TIMEZONE)


def get_now():
    return datetime.now(get_timezone())


def parse_date(value: str) -> date:
    """Parse an explicit date string."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    return date_parser.parse(value, fuzzy=False).date()


def resolve_date_expression(expression: str) -> date:
    """Resolve common natural date expressions."""

    text = expression.strip().lower()
    today = get_now().date()

    if text == "today":
        return today

    if text == "tomorrow":
        return today + timedelta(days=1)

    if text == "yesterday":
        return today - timedelta(days=1)

    if text == "this week":
        return today

    if text == "next week":
        start, _ = get_week_range(today) 
        return (start + timedelta(days=7)).date()

    if text == "this month":
        return today.replace(day=1)

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

            # "Next Monday" means the Monday in the following week.
            if days_ahead == 0:
                days_ahead = 7
            else:
                days_ahead += 7

            return today + timedelta(days=days_ahead)

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


def get_day_range(day_value: str | date):
    """Return local start and exclusive end of a day."""

    day = (
        resolve_date_expression(day_value)
        if isinstance(day_value, str)
        else day_value
    )

    start = datetime.combine(day, time.min, tzinfo=get_timezone())
    end = start + timedelta(days=1)

    return start, end


def get_week_range(week_value: str | date | None = None):
    """Return Monday to next Monday for a given week."""

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
        start_date, time.min, tzinfo=get_timezone()
    )
    end = start + timedelta(days=7)

    return start, end


def get_month_range(month: str | date | None = None):
    """Return first day of month to first day of next month."""

    if month is None:
        current = get_now().date()
        year, month_number = current.year, current.month

    elif isinstance(month, date):
        year, month_number = month.year, month.month

    else:
        parsed = date_parser.parse(month, fuzzy=False)
        year, month_number = parsed.year, parsed.month

    start = datetime(
        year, month_number, 1,
        tzinfo=get_timezone()
    )

    if month_number == 12:
        end = datetime(year + 1, 1, 1, tzinfo=get_timezone())
    else:
        end = datetime(year, month_number + 1, 1, tzinfo=get_timezone())

    return start, end


def to_rfc3339(value: datetime):
    """Convert datetime into RFC3339 format."""

    if value.tzinfo is None:
        value = value.replace(tzinfo=get_timezone())

    return value.isoformat()


def parse_datetime(value: str):
    """Parse a date and time expression."""

    parsed = date_parser.parse(value, fuzzy=False)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=get_timezone())

    return parsed.astimezone(get_timezone())
