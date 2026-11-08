
from datetime import datetime, date, timedelta

from services.calendar_service import (
    insert_calendar_event,
    update_calendar_event,
    delete_calendar_event,
    get_event_by_id,
)

from utils.validators import (
    validate_title,
    validate_event_time,
    validate_date_range,
    validate_event_update,
    validate_reminder,
)

from utils.datetime_utils import to_rfc3339
from utils.recurrence_utils import validate_recurrence_rule

from config.settings import (
    DEFAULT_EVENT_DURATION_MINUTES,
    DEFAULT_REMINDER_MINUTES,
    TIMEZONE,
)

from errors.exceptions import (
    EventAlreadyCancelledError,
    ConfirmationRequiredError
)

def create_event(
    title: str,
    start: datetime | date,
    end: datetime | date | None = None,
    description: str | None = None,
    location: str | None = None,
    all_day: bool = False,
    recurrence: list[str] | None = None,
    reminder_minutes: int = DEFAULT_REMINDER_MINUTES,
):
    title = validate_title(title)
    validate_reminder(reminder_minutes)

    if all_day:
        if isinstance(start, datetime):
            start = start.date()

        if not isinstance(start, date):
            raise ValueError("All-day events require a date start.")

        if end is None:
            end = start + timedelta(days=1)

        if isinstance(end, datetime):
            end = end.date()

        validate_date_range(start, end)

        event_start = {"date": start.isoformat()}
        event_end = {"date": end.isoformat()}

    else:
        if not isinstance(start, datetime):
            raise ValueError("Timed events require a datetime start.")

        if end is None:
            end = start + timedelta(
                minutes=DEFAULT_EVENT_DURATION_MINUTES
            )

        validate_event_time(start, end)

        event_start = {
            "dateTime": to_rfc3339(start),
            "timeZone": TIMEZONE,
        }

        event_end = {
            "dateTime": to_rfc3339(end),
            "timeZone": TIMEZONE,
        }

    event_body = {
        "summary": title,
        "start": event_start,
        "end": event_end,
        "reminders": {
            "useDefault": False,
            "overrides": [
                {
                    "method": "popup",
                    "minutes": reminder_minutes,
                }
            ],
        },
    }

    if description:
        event_body["description"] = description

    if location:
        event_body["location"] = location

    if recurrence:

        validate_recurrence_rule(
            recurrence,
            all_day=all_day,
        )

        event_body["recurrence"] = recurrence

    return insert_calendar_event(event_body)


def update_event(event_id: str, updates: dict):

    validate_event_update(updates)

    existing_event = None

    if "recurrence" in updates:

        existing_event = get_event_by_id(event_id)

        is_all_day = (
            "date" in existing_event.get("start", {})
        )

        validate_recurrence_rule(
            updates["recurrence"],
            all_day=is_all_day,
        )

    if existing_event is not None:
        return update_calendar_event(
            event_id=event_id,
            updates=updates,
            existing_event=existing_event,
        )

    return update_calendar_event(
        event_id=event_id,
        updates=updates,
    )


def delete_event(
    event_id: str,
    confirmed: bool = False,
    recurrence_scope: str | None = None,
):
    """
    Delete a calendar event.

    Recurring master events require explicit series scope.
    Recurring instances can be deleted individually.
    """

    if not confirmed:
        raise ConfirmationRequiredError(
            "Event deletion requires explicit user confirmation."
        )

    existing = get_event_by_id(event_id)

    if existing.get("status") == "cancelled":
        raise EventAlreadyCancelledError(
            "The selected event is already cancelled. "
            "No deletion is necessary."
        )

    is_recurring_master = bool(
        existing.get("recurrence")
    )

    if is_recurring_master and recurrence_scope != "series":

        raise ConfirmationRequiredError(
            "This event is a recurring series. "
            "Specify recurrence_scope='series' and obtain explicit "
            "confirmation before deleting the entire series."
        )

    if not is_recurring_master and recurrence_scope == "series":

        raise ValueError(
            "The selected event is not a recurring master event."
        )

    return delete_calendar_event(
        event_id,
        existing_event=existing,
    )


def get_event_details(event_id: str):
    return get_event_by_id(event_id)


def postpone_event(
    event_id: str,
    new_start: datetime | date,
    new_end: datetime | date,
    existing_event: dict | None = None,
):
    if existing_event is None:
        existing_event = get_event_by_id(event_id)

    if existing_event.get("status") == "cancelled":
        raise ValueError(
            "Cannot postpone a cancelled event."
        )

    is_all_day = "date" in existing_event.get("start", {})

    if is_all_day:

        if isinstance(new_start, datetime):
            new_start = new_start.date()

        if isinstance(new_end, datetime):
            new_end = new_end.date()

        validate_date_range(
            new_start,
            new_end,
        )

        updates = {
            "start": {
                "date": new_start.isoformat()
            },
            "end": {
                "date": new_end.isoformat()
            },
        }

    else:

        if not isinstance(new_start, datetime):
            raise ValueError(
                "Timed events require datetime values."
            )

        if not isinstance(new_end, datetime):
            raise ValueError(
                "Timed events require datetime values."
            )

        validate_event_time(
            new_start,
            new_end,
        )

        updates = {
            "start": {
                "dateTime": to_rfc3339(new_start),
                "timeZone": TIMEZONE,
            },
            "end": {
                "dateTime": to_rfc3339(new_end),
                "timeZone": TIMEZONE,
            },
        }

    return update_calendar_event(
        event_id=event_id,
        updates=updates,
        existing_event=existing_event,
    )
