from datetime import timedelta
from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field
from errors.error_handler import handle_tool_errors

# --------------------------------------------------
# SERVICES
# --------------------------------------------------

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

from services.calendar_summary import (
    get_calendar_summary,
)

from services.availability_service import (
    check_availability,
    get_available_slots,
)

from services.calendar_service import list_calendars

# --------------------------------------------------
# UTILITIES
# --------------------------------------------------
from utils.datetime_utils import (
    parse_datetime,
    parse_date,
    parse_date_or_datetime,
    resolve_date_expression,
)

from utils.recurrence_utils import build_recurrence_rule

# --------------------------------------------------
# PYDANTIC SCHEMAS
# --------------------------------------------------

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

mcp = FastMCP("Google Calendar MCP", mask_error_details=True)


# ==================================================
# 1. CREATE CALENDAR EVENT
# ==================================================


@mcp.tool()
@handle_tool_errors
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
            min_length=1,
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
    Create a new Google Calendar event with a specified title, start time,
    and optional end time, description, location, and reminder.

    Supports both all-day and timed events, including recurring events
    with daily, weekly, monthly, or yearly frequency.

    Before creating a timed event, the tool checks calendar availability
    to identify scheduling conflicts. If a conflict exists, it returns
    the conflicting periods and requests confirmation before proceeding.

    Set allow_conflict=True only when the user explicitly agrees to
    schedule the event despite existing conflicts.

    If the end time is omitted, a default one-hour duration is used
    for timed events.
    """

    # Pydantic validation
    payload = CreateEventSchema.model_validate(
        {
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
        }
    )

    # Resolve start
    start_value = parse_date_or_datetime(payload.start, all_day=payload.all_day)

    # Resolve end
    end_value = (
        parse_date_or_datetime(payload.end, all_day=payload.all_day)
        if payload.end
        else None
    )

    # Build recurrence
    recurrence = None

    if payload.recurrence_frequency:
        recurrence = build_recurrence_rule(
            frequency=payload.recurrence_frequency,
            interval=payload.recurrence_interval,
            byday=payload.recurrence_days,
        )

    # Check availability for timed events
    if not payload.all_day:

        if end_value is None:
            end_value = start_value + timedelta(hours=1)

        availability = check_availability(
            start_value,
            end_value,
        )

        if not availability["available"] and not payload.allow_conflict:
            return {
                "success": False,
                "conflict": True,
                "message": (
                    "This time slot is busy. " "Confirm whether you want to proceed."
                ),
                "busy_periods": availability["busy_periods"],
            }

    # Create event
    event = create_event(
        title=payload.title,
        start=start_value,
        end=end_value,
        description=payload.description,
        location=payload.location,
        all_day=payload.all_day,
        recurrence=recurrence,
        reminder_minutes=payload.reminder_minutes,
    )

    return {
        "success": True,
        "event": event,
    }


# ==================================================
# 2. EDIT CALENDAR EVENT
# ==================================================


@mcp.tool()
@handle_tool_errors
def edit_calendar_event(
    event_id: Annotated[
        str,
        Field(
            min_length=1,
            description="Unique Google Calendar event ID identifying the existing event to modify.",
        ),
    ],
    updates: Annotated[
        dict,
        Field(
            description=(
                "Dictionary containing fields to modify. "
                "Supported fields include summary, description, location, start, end, reminders and recurrence. "
                "Provide only the fields requiring changes."
            ),
        ),
    ],
) -> dict:
    """
    Modify an existing Google Calendar event using its unique event ID
    and a dictionary containing the fields to update.

    Supports changes to the event title, description, location, start
    time, end time, reminders, and recurrence settings.

    Only provide the fields that need modification. Unspecified fields
    should remain unchanged.

    When changing the event schedule, provide both start and end values.
    The event must first be identified using its event ID, which can be
    obtained through event search or event details.

    Use this tool when the user requests changes to an existing event
    rather than creating a new event.
    """

    payload = UpdateEventSchema.model_validate(
        {
            "event_id": event_id,
            "updates": updates,
        }
    )

    return update_event(
        payload.event_id,
        payload.updates,
    )


# ==================================================
# 3. DELETE CALENDAR EVENT
# ==================================================


@mcp.tool()
@handle_tool_errors
def remove_calendar_event(
    event_id: Annotated[
        str,
        Field(
            min_length=1,
            description="Unique Google Calendar event ID identifying the event to delete.",
        ),
    ],
    confirmed: Annotated[
        bool,
        Field(
            default=False,
            description="Explicit user confirmation required before permanently deleting the selected event.",
        ),
    ] = False,
) -> dict:
    """
    Delete an existing Google Calendar event using its unique event ID.
    Requires explicit user confirmation before deletion. Use event search
    or event details to identify the correct event before requesting deletion.
    Already cancelled events are handled without performing another deletion.
    Returns the deletion status and event identifier.
    """

    payload = DeleteEventSchema.model_validate(
        {
            "event_id": event_id,
            "confirmed": confirmed,
        }
    )

    if not payload.confirmed:
        raise ValueError(
            "Deletion requires explicit user confirmation. "
            "Set confirmed=True after the user approves."
        )

    return delete_event(
        payload.event_id,
        payload.confirmed,
    )


# ==================================================
# 4. GET CALENDAR EVENT
# ==================================================


@mcp.tool()
@handle_tool_errors
def get_calendar_event(
    event_id: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Unique Google Calendar event ID for retrieving complete event details, "
                "including title, description, location, start time and end time."
            ),
        ),
    ],
) -> dict:
    """
    Retrieve complete details of a specific Google Calendar event using
    its unique event ID. Use this tool when the user requests information
    about an existing event or when additional details are required before
    editing, postponing or deleting it. Returns available event information,
    including title, description, location, start and end times, recurrence,
    reminders and event status.
    """

    payload = GetEventSchema.model_validate(
        {
            "event_id": event_id,
        }
    )

    return get_event_details(payload.event_id)


# ==================================================
# 5. POSTPONE CALENDAR EVENT
# ==================================================


@mcp.tool()
@handle_tool_errors
def postpone_calendar_event(
    event_id: Annotated[
        str,
        Field(
            min_length=1,
            description="Unique Google Calendar event ID identifying the existing event to reschedule.",
        ),
    ],
    new_start: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "New start date or datetime for the postponed event. "
                "Use YYYY-MM-DD for all-day events or ISO datetime for timed events."
            ),
        ),
    ],
    new_end: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "New end date or datetime for the postponed event. "
                "Must match the original event type and occur after new_start."
            ),
        ),
    ],
) -> dict:
    """
    Reschedule an existing Google Calendar event by changing its start
    and end times while preserving its other event details. Requires the
    event ID and new start and end values. Supports both timed and all-day
    events when the supplied values match the original event type.
    Use this tool when the user wants to postpone or move an existing event.
    Returns the updated event details.
    """

    payload = PostponeEventSchema.model_validate(
        {
            "event_id": event_id,
            "new_start": new_start,
            "new_end": new_end,
        }
    )

    # The service checks whether the existing event is all-day.
    # Parse both values here as dates or datetimes based on the existing event.
    existing = get_event_details(payload.event_id)

    if "date" in existing.get("start", {}):
        parsed_start = resolve_date_expression(payload.new_start)
        parsed_end = resolve_date_expression(payload.new_end)
    else:
        parsed_start = parse_datetime(payload.new_start)
        parsed_end = parse_datetime(payload.new_end)

    return postpone_event(
        payload.event_id,
        parsed_start,
        parsed_end
    )


# ==================================================
# 6. SEARCH CALENDAR EVENTS
# ==================================================


@mcp.tool()
@handle_tool_errors
def find_calendar_events(
    start: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Beginning of the calendar search range. "
                "Use an ISO date or datetime string, or a supported natural date expression."
            ),
        ),
    ],
    end: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Ending of the calendar search range. "
                "Must occur after start and defines the upper boundary of the event search."
            ),
        ),
    ],
    title: Annotated[
        str | None,
        Field(
            default=None,
            max_length=200,
            description=(
                "Full or partial event title to filter search results. "
                "Matching is case-insensitive. Leave empty to retrieve all events within the specified range."
            ),
        ),
    ] = None,
) -> list:
    """
    Search Google Calendar events within a specified start and end range.
    An optional title filter can retrieve events matching a full or partial
    event name. Use this tool when the user asks to find meetings, appointments,
    scheduled activities or events during a particular period. Without a
    title filter, all matching events within the requested range are returned.
    Results include the available Google Calendar event details.
    """

    payload = SearchEventsSchema.model_validate(
        {
            "start": start,
            "end": end,
            "title": title,
        }
    )

    return search_events(
        parse_datetime(payload.start),
        parse_datetime(payload.end),
        payload.title,
    )


# ==================================================
# 7. FIND SIMILAR CALENDAR EVENTS
# ==================================================


@mcp.tool()
@handle_tool_errors
def find_similar_calendar_events(
    title: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description=(
                "Event title or phrase used to find existing events with similar names. "
                "Results are ranked by title similarity."
            ),
        ),
    ],
    start: Annotated[
        str,
        Field(
            min_length=1,
            description="Beginning of the date or datetime range for searching similar events.",
        ),
    ],
    end: Annotated[
        str,
        Field(
            min_length=1,
            description="Ending of the date or datetime range. Must occur after start.",
        ),
    ],
) -> list:
    """
    Find existing Google Calendar events whose titles closely resemble
    a supplied search phrase. Searches within the specified date range and
    calculates title similarity scores to identify potentially matching events.
    Use this tool when the user remembers only part of an event title or
    when an exact title search may not find the intended event. Returns
    matching events ranked by similarity score.
    """

    payload = SimilarEventsSchema.model_validate(
        {
            "title": title,
            "start": start,
            "end": end,
        }
    )

    return find_similar_events(
        payload.title,
        parse_datetime(payload.start),
        parse_datetime(payload.end),
    )


# ==================================================
# 8. GET CALENDAR OVERVIEW
# ==================================================


@mcp.tool()
@handle_tool_errors
def get_calendar_overview(
    period: Annotated[
        Literal["day", "week", "month"],
        Field(
            description=(
                "Time period for generating the calendar overview. "
                "Supported values: day, week or month."
            ),
        ),
    ],
    value: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Date or period expression used to select the requested overview. "
                "Examples: tomorrow, next week or November 2026. "
                "Defaults to the current period when omitted."
            ),
        ),
    ] = None,
) -> dict:
    """
    Retrieve a calendar overview for a specific day, week or month.
    Supports date expressions such as today, tomorrow, next week and
    specific month names. Provides scheduled event information and
    aggregated counts for the requested period. Use this tool when the
    user wants a daily schedule, weekly agenda or monthly event summary.
    Defaults to the current period when no value is supplied.
    """

    payload = CalendarOverviewSchema.model_validate(
        {
            "period": period,
            "value": value,
        }
    )

    return get_calendar_summary(
        payload.period,
        payload.value,
    )


# ==================================================
# 9. CHECK CALENDAR AVAILABILITY
# ==================================================


@mcp.tool()
@handle_tool_errors
def check_calendar_availability(
    start: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Beginning of the requested availability time slot. "
                "Provide an ISO datetime containing the desired date and time."
            ),
        ),
    ],
    end: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Ending of the requested availability time slot. "
                "Must occur after start and defines the period checked for existing calendar conflicts."
            ),
        ),
    ],
) -> dict:
    """
    Check whether a requested start and end time is available in the
    Google Calendar. Queries existing calendar commitments to identify
    overlapping busy periods. Use this tool before scheduling a meeting
    or when the user asks whether a particular time slot is free.
    Returns an availability status and the conflicting time periods
    when existing events overlap the requested range.
    """

    payload = AvailabilitySchema.model_validate(
        {
            "start": start,
            "end": end,
        }
    )

    return check_availability(
        parse_datetime(payload.start),
        parse_datetime(payload.end),
    )


# ==================================================
# 10. SUGGEST AVAILABLE SLOTS
# ==================================================


@mcp.tool()
@handle_tool_errors
def suggest_available_slots(
    start: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Beginning of the date or datetime range in which available slots should be identified. "
                "Provide an ISO datetime or supported date expression."
            ),
        ),
    ],
    end: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Ending of the date or datetime range for finding available slots. "
                "Must occur after start and defines the scheduling window."
            ),
        ),
    ],
    duration_minutes: Annotated[
        int,
        Field(
            default=60,
            gt=0,
            le=1440,
            description=(
                "Minimum duration required for each suggested available slot, expressed in minutes. "
                "For example, 60 identifies free periods lasting at least one hour."
            ),
        ),
    ] = 60,
) -> list:
    """
    Find available time slots within a specified date and time range.
    Checks existing calendar commitments and identifies uninterrupted
    free periods that satisfy the requested minimum duration. Use this
    tool when the user wants alternative meeting times or asks for
    available scheduling options. Returns suggested start and end times
    for each qualifying free period.
    """

    payload = AvailableSlotsSchema.model_validate(
        {
            "start": start,
            "end": end,
            "duration_minutes": duration_minutes,
        }
    )

    return get_available_slots(
        parse_datetime(payload.start),
        parse_datetime(payload.end),
        payload.duration_minutes,
    )


# ==================================================
# 11. LIST CALENDARS
# ==================================================


@mcp.tool()
@handle_tool_errors
def get_calendar_list() -> list:
    """
    Retrieve the list of Google Calendars accessible to the authenticated
    user. Provides calendar identifiers, names, primary calendar status
    and timezone information. Use this tool when the user wants to inspect
    available calendars or when identifying which calendar is accessible
    for scheduling operations. Does not create, modify or delete calendars.
    """

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


# ==================================================
# SERVER ENTRY POINT
# ==================================================

if __name__ == "__main__":
    mcp.run()
