
from datetime import datetime, date


def validate_title(title: str):
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Event title is required.")

    if len(title.strip()) > 200:
        raise ValueError("Event title cannot exceed 200 characters.")

    return title.strip()


def validate_event_time(
    start_time: datetime,
    end_time: datetime,
    all_day=False,
):
    if all_day:
        return validate_date_range(start_time, end_time)

    if not isinstance(start_time, datetime):
        raise ValueError("Start time must be a datetime.")

    if not isinstance(end_time, datetime):
        raise ValueError("End time must be a datetime.")

    if start_time.tzinfo is None or end_time.tzinfo is None:
        raise ValueError("Datetime values must include timezone information.")

    if start_time >= end_time:
        raise ValueError("End time must be after start time.")

    return True


def validate_date_range(start_date: date, end_date: date):
    if not isinstance(start_date, date) or isinstance(start_date, datetime):
        raise ValueError("Start date must be a date.")

    if not isinstance(end_date, date) or isinstance(end_date, datetime):
        raise ValueError("End date must be a date.")

    if start_date >= end_date:
        raise ValueError("End date must be after start date.")

    return True


def validate_event_update(updates: dict):
    allowed_fields = {
        "summary",
        "description",
        "location",
        "start",
        "end",
        "reminders",
        "recurrence",
        "visibility",
        "transparency",
    }

    if not isinstance(updates, dict) or not updates:
        raise ValueError("At least one update field is required.")

    invalid = set(updates) - allowed_fields

    if invalid:
        raise ValueError(
            f"Unsupported update fields: {', '.join(invalid)}"
        )

    if "summary" in updates:
        validate_title(updates["summary"])

    if "start" in updates or "end" in updates:
        if "start" not in updates or "end" not in updates:
            raise ValueError(
                "Both start and end must be supplied when rescheduling."
            )

        start = updates["start"]
        end = updates["end"]

        if not isinstance(start, dict) or not isinstance(end, dict):
            raise ValueError("Start and end must be event date objects.")

        if "date" in start and "date" in end:
            validate_date_range(
                date.fromisoformat(start["date"]),
                date.fromisoformat(end["date"]),
            )

        elif "dateTime" in start and "dateTime" in end:
            start_dt = datetime.fromisoformat(start["dateTime"])
            end_dt = datetime.fromisoformat(end["dateTime"])

            validate_event_time(start_dt, end_dt)

        else:
            raise ValueError(
                "Start and end must both use date or both use dateTime."
            )

    return True
