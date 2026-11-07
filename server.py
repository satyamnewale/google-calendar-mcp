from fastmcp import FastMCP

from services.event_service import (
    create_event,
    update_event,
    delete_event,
    get_event_details,
    postpone_event,
) 
from services.event_search import (
    search_events,
    find_similar_events,
)

from typing import Annotated, Literal
from pydantic import Field

from services.calendar_summary import (
    get_calendar_summary,
)

from services.availability_service import (
    check_availability,
    get_available_slots,
)

from services.calendar_service import list_calendars

from utils.datetime_utils import (
    parse_datetime,
    resolve_date_expression,
)

from utils.recurrence_utils import build_recurrence_rule

from schemas.event_schema import (
    CreateEventSchema,
    UpdateEventSchema,
    DeleteEventSchema,
    GetEventSchema,
    PostponeEventSchema,
    SearchEventsSchema,
    SimilarEventsSchema,
    CalendarOverviewSchema,
    AvailabilitySchema,
    AvailableSlotsSchema,
)


mcp = FastMCP("Google Calendar MCP")


def parse_optional_datetime(value: str):
    return parse_datetime(value)


@mcp.tool()
def create_calendar_event(
    title: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description="Title or subject of the calendar event.",
        ),
    ],

    start: Annotated[
        str,
        Field(
            description=(
                "Start date or datetime of the event. "
                "Use YYYY-MM-DD for all-day events or ISO datetime for timed events. "
                "Natural expressions such as tomorrow are also supported."
            ),
        ),
    ],

    end: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "End date or datetime of the event. "
                "Must use the same event type as start. "
                "Defaults to one hour after start for timed events."
            ),
        ),
    ] = None,

    description: Annotated[
        str | None,
        Field(
            default=None,
            max_length=8192,
            description="Additional information, agenda, or notes associated with the event.",
        ),
    ] = None,

    location: Annotated[
        str | None,
        Field(
            default=None,
            max_length=500,
            description="Physical address, office location, or online meeting location.",
        ),
    ] = None,

    all_day: Annotated[
        bool,
        Field(
            default=False,
            description="Set True when the event occupies an entire calendar day.",
        ),
    ] = False,

    recurrence_frequency: Annotated[
        Literal["DAILY", "WEEKLY", "MONTHLY", "YEARLY"] | None,
        Field(
            default=None,
            description="Recurrence frequency. Supported values: DAILY, WEEKLY, MONTHLY, YEARLY.",
        ),
    ] = None,

    recurrence_interval: Annotated[
        int,
        Field(
            default=1,
            ge=1,
            le=365,
            description="Number of frequency units between recurring events. Requires recurrence_frequency.",
        ),
    ] = 1,

    recurrence_days: Annotated[
        list[Literal["MO", "TU", "WE", "TH", "FR", "SA", "SU"]] | None,
        Field(
            default=None,
            description="Weekdays for recurring events using two-letter codes such as MO, TU, WE.",
        ),
    ] = None,

    reminder_minutes: Annotated[
        int,
        Field(
            default=10,
            ge=0,
            le=40320,
            description="Number of minutes before the event to trigger a popup reminder.",
        ),
    ] = 10,

    allow_conflict: Annotated[
        bool,
        Field(
            default=False,
            description="Set True to create the event even when its time overlaps existing events.",
        ),
    ] = False,

) -> dict:
    """
    Create a Google Calendar event with optional recurrence,
    reminders, location and availability checking.
    """

    # Runtime Pydantic validation
    payload = CreateEventSchema.model_validate({
        "title": title,
        "start": start,
        "end": end,
        "description": description,
        "location": location,
        "all_day": all_day,
        "recurrence_frequency": recurrence_frequency,
        "recurrence_interval": recurrence_interval,
        "recurrence_days": recurrence_days,
        "reminder_minutes": reminder_minutes,
        "allow_conflict": allow_conflict,
    })

    """
    Create a Google Calendar event.

    start and end should be ISO date or datetime strings.
    For all-day events use YYYY-MM-DD.
    For timed events use ISO datetime with timezone when possible.
    """

    start_value = (
        resolve_date_expression(start)
        if all_day else parse_datetime(start)
    )

    if end:
        end_value = (
            resolve_date_expression(end)
            if all_day else parse_datetime(end)
        )
    else:
        end_value = None

    recurrence = None

    if recurrence_frequency:
        recurrence = build_recurrence_rule(
            frequency=recurrence_frequency,
            interval=recurrence_interval,
            byday=recurrence_days,
        )

    if not all_day:
        if end_value is None:
            from datetime import timedelta
            end_value = start_value + timedelta(hours=1)

        availability = check_availability(
            start_value,
            end_value
        )

        if not availability["available"] and not allow_conflict:
            return {
                "success": False,
                "conflict": True,
                "message": "This time slot is busy. Confirm whether you want to proceed.",
                "busy_periods": availability["busy_periods"],
            }

    event = create_event(
        title=title,
        start=start_value,
        end=end_value,
        description=description or None,
        location=location or None,
        all_day=all_day,
        recurrence=recurrence,
        reminder_minutes=reminder_minutes,
    )

    return {
        "success": True,
        "event": event,
    }


@mcp.tool()
def edit_calendar_event(
    event_id: str,
    updates: dict,
) -> dict:
    """Edit title, description, time, location or reminder settings."""

    return update_event(event_id, updates)


@mcp.tool()
def remove_calendar_event(
    event_id: str,
    confirmed: bool = False,
) -> dict:
    """Delete a calendar event after explicit confirmation."""

    return delete_event(event_id, confirmed)


@mcp.tool()
def get_calendar_event(event_id: str) -> dict:
    """Get full details of a specific calendar event."""

    return get_event_details(event_id)


@mcp.tool()
def postpone_calendar_event(
    event_id: str,
    new_start: str,
    new_end: str,
) -> dict:
    """Postpone an event to a new start and end time."""

    return postpone_event(
        event_id,
        parse_datetime(new_start),
        parse_datetime(new_end),
    )


@mcp.tool()
def find_calendar_events(
    start: str,
    end: str,
    title: str = "",
) -> list:
    """Search events between two dates, optionally by title."""

    return search_events(
        parse_datetime(start),
        parse_datetime(end),
        title or None,
    )


@mcp.tool()
def find_similar_calendar_events(
    title: str,
    start: str,
    end: str,
) -> list:
    """Find events with titles similar to the user's search."""

    return find_similar_events(
        title,
        parse_datetime(start),
        parse_datetime(end),
    )


@mcp.tool()
def get_calendar_overview(
    period: str,
    value: str = "",
) -> dict:
    """
    Get event lists and counts for day, week or month.

    Examples:
    period='day', value='tomorrow'
    period='week', value='next week'
    period='month', value='November 2026'
    """

    return get_calendar_summary(
        period,
        value or None
    )


@mcp.tool()
def check_calendar_availability(
    start: str,
    end: str,
) -> dict:
    """Check whether a time slot is available."""

    return check_availability(
        parse_datetime(start),
        parse_datetime(end),
    )


@mcp.tool()
def suggest_available_slots(
    start: str,
    end: str,
    duration_minutes: int = 60,
) -> list:
    """Find free time slots within a requested date range."""

    return get_available_slots(
        parse_datetime(start),
        parse_datetime(end),
        duration_minutes,
    )


@mcp.tool()
def get_calendar_list() -> list:
    """List calendars accessible to the authorized user."""

    calendars = list_calendars()

    return [
        {
            "id": calendar.get("id"),
            "summary": calendar.get("summary"),
            "primary": calendar.get("primary", False),
            "timeZone": calendar.get("timeZone"),
        }
        for calendar in calendars
    ]


if __name__ == "__main__":
    mcp.run()
