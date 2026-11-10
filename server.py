from datetime import date, datetime, time, timedelta
from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field
from errors.error_handler import handle_tool_errors
from errors.exceptions import ConfirmationRequiredError

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
    find_occurrence_conflicts,
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
    get_timezone,
    parse_search_range,
)

from utils.recurrence_utils import (
    build_recurrence_rule,
    generate_occurrence_windows,
)

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
    recurrence_count: Annotated[
        int | None,
        Field(
            default=None,
            gt=0,
            le = 500,
            strict=True,
            description=(
                "Total number of occurrences, including the first occurrence. "
                "For example, 21 means 21 events in total. "
                "Mutually exclusive with recurrence_until."
            ),
        ),
    ] = None,
    recurrence_until: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Last occurrence date (inclusive), in YYYY-MM-DD format, "
                "or an ISO datetime. Mutually exclusive with recurrence_count."
            ),
        ),
    ] = None,
    recurrence_indefinite: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "Set True only when the user explicitly requests "
                "an unlimited recurring event."
            ),
        ),
    ] = False,
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
    Create a new Google Calendar event, including one-time and recurring events.

    WHEN TO USE:
    - Use for meetings, reminders, workouts, tasks, appointments, and other scheduled activities.
    - Use this tool once to create an entire recurring series. Never create recurring occurrences individually.

    REQUIRED INPUTS:
    - title: A meaningful event title.
    - start: Start date and time of the first occurrence. Must be an unambiguous date/time.
    - end: End date and time of the first occurrence. Omit when the default event duration is appropriate, if supported by the schema.

    OPTIONAL INPUTS:
    - description: Additional event information.
    - location: Event location.
    - all_day: Whether this is an all-day event.
    - reminder_minutes: Reminder before the event.
    - allow_conflict: Whether to permit creation when an occurrence overlaps an existing event.

    RECURRENCE PARAMETERS:
    - recurrence_frequency: DAILY, WEEKLY, MONTHLY, or YEARLY.
    - recurrence_interval: Repeat every N frequency units. For example, 1 means every day; 2 means every two days.
    - recurrence_days: Weekdays for weekly recurrence, such as ["MO", "WE", "FR"].
    - recurrence_count: Total number of occurrences, INCLUDING the first occurrence.
    - recurrence_until: Final recurrence date. Mutually exclusive with recurrence_count.
    - recurrence_indefinite: Create an ongoing series. Use only when explicitly requested.

    RECURRENCE EXAMPLES:
    - "Every day for 21 days": frequency=DAILY, interval=1, count=21.
    - "Every Monday and Wednesday for 10 occurrences": frequency=WEEKLY, days=["MO","WE"], count=10.
    - "Every two weeks until December 31": frequency=WEEKLY, interval=2, until=<final date>.

    EXECUTION RULES:
    1. Resolve relative dates before calling this tool. Use Date-Time MCP only when the requested date/time requires clarification or calculation.
    2. Validate start, end, timezone, and recurrence parameters.
    3. For recurring events, validate availability across ALL generated occurrences, not just the first.
    4. Perform recurrence-wide conflict checking internally. Do not require the agent to call availability separately for every occurrence.
    5. If conflicts exist and allow_conflict is false, return the conflicting occurrence dates and do not create the event.
    6. If allow_conflict is true, proceed with creation while reporting the conflicts.
    7. Create the complete recurrence series using ONE Google Calendar insertion.
    8. Return the event ID, title, start/end, recurrence details, timezone, and conflict information.

    IMPORTANT:
    - Never interpret "for 21 days" as an indefinite recurrence.
    - Never make separate availability calls for each recurring date.
    - Do not silently change the user's requested date, time, or recurrence pattern.
    """

    # Pydantic validation
    # --------------------------------------------------
    # 1. VALIDATE INPUT
    # --------------------------------------------------

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
            "recurrence_count": recurrence_count,
            "recurrence_until": recurrence_until,
            "recurrence_indefinite": recurrence_indefinite,
            "reminder_minutes": reminder_minutes,
            "allow_conflict": allow_conflict,
        }
    )

    # --------------------------------------------------
    # 2. PARSE EVENT START AND END
    # --------------------------------------------------

    start_value = parse_date_or_datetime(
        payload.start,
        all_day=payload.all_day,
    )

    if payload.end:

        end_value = parse_date_or_datetime(
            payload.end,
            all_day=payload.all_day,
        )

    elif payload.all_day:

        # All-day event ends are exclusive.
        end_value = start_value + timedelta(days=1)

    else:

        end_value = start_value + timedelta(hours=1)

    # --------------------------------------------------
    # 3. VALIDATE RECURRENCE START AND TERMINATION
    # --------------------------------------------------

    if payload.recurrence_frequency:

        if payload.recurrence_days:

            weekday_codes = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]

            event_date = (
                start_value
                if isinstance(start_value, date)
                and not isinstance(start_value, datetime)
                else start_value.date()
            )

            actual_weekday = weekday_codes[event_date.weekday()]

            if actual_weekday not in payload.recurrence_days:

                raise ValueError(
                    f"The starting date falls on {actual_weekday}, "
                    f"which is not included in recurrence_days. "
                    f"Choose a matching start date or change the weekdays."
                )

        if payload.recurrence_until:

            if payload.all_day:

                until_value = date.fromisoformat(payload.recurrence_until)

                if until_value < start_value:

                    raise ValueError(
                        "Recurrence end date cannot be before event start."
                    )

            else:

                try:
                    until_date = date.fromisoformat(payload.recurrence_until)

                    until_datetime = datetime.combine(
                        until_date,
                        time.max,
                        tzinfo=get_timezone(),
                    )

                except ValueError:

                    until_datetime = parse_datetime(payload.recurrence_until)

                if until_datetime < start_value:

                    raise ValueError(
                        "Recurrence end datetime cannot be before event start."
                    )

    # --------------------------------------------------
    # 4. BUILD RECURRENCE RULE
    # --------------------------------------------------

    recurrence = None

    if payload.recurrence_frequency:

        recurrence = build_recurrence_rule(
            frequency=payload.recurrence_frequency,
            interval=payload.recurrence_interval,
            byday=payload.recurrence_days,
            count=payload.recurrence_count,
            until=payload.recurrence_until,
            all_day=payload.all_day,
        )

    # --------------------------------------------------
    # 5. GENERATE OCCURRENCE WINDOWS
    # --------------------------------------------------

    occurrences = generate_occurrence_windows(
        start=start_value,
        end=end_value,
        recurrence=recurrence,
        all_day=payload.all_day,
        indefinite=payload.recurrence_indefinite,
    )

    # --------------------------------------------------
    # 6. CHECK ALL OCCURRENCES FOR CONFLICTS
    # --------------------------------------------------

    range_start = min(occurrence[0] for occurrence in occurrences)

    range_end = max(occurrence[1] for occurrence in occurrences)

    availability = check_availability(
        range_start,
        range_end,
    )

    occurrence_conflicts = find_occurrence_conflicts(
        occurrences,
        availability["busy_periods"],
    )

    if occurrence_conflicts and not payload.allow_conflict:

        return {
            "success": False,
            "conflict": True,
            "message": (
                "One or more event occurrences overlap "
                "existing calendar commitments. "
                "Confirm whether you want to proceed."
            ),
            "conflicting_occurrences": occurrence_conflicts,
            "busy_periods": availability.get("busy_periods", []),
        }

    # --------------------------------------------------
    # 7. CREATE EVENT
    # --------------------------------------------------

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

    result = {
        "success": True,
        "event": event,
    }

    if payload.recurrence_indefinite:

        result["availability_check"] = {
            "complete": False,
            "horizon_days": 90,
            "message": (
                "Conflicts were checked only within the next "
                "90 days because this recurrence is indefinite."
            ),
        }

    else:

        result["availability_check"] = {
            "complete": True,
            "occurrences_checked": len(occurrences),
        }

    return result


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
    recurrence_scope: Annotated[
        Literal["event", "series"] | None,
        Field(
            default=None,
            description=(
                "For recurring master events, use 'series' only when "
                "the user explicitly confirms deletion of the entire series. "
                "For an individual occurrence, use 'event'."
            ),
        ),
    ] = None,
) -> dict:
    """
    Delete an existing Google Calendar event using its unique event ID.
    Requires explicit user confirmation before deletion. Use event search
    or event details to identify the correct event before requesting deletion.
    Already cancelled events are handled without performing another deletion.
    Returns the deletion status and event identifier.
    """

    payload = DeleteEventSchema.model_validate({
        "event_id": event_id,
        "confirmed": confirmed,
        "recurrence_scope": recurrence_scope,
    })

    # Confirmation must be checked before calling the service.
    if not payload.confirmed:
        raise ConfirmationRequiredError(
            "Event deletion requires explicit user confirmation."
        )

    # Preserve the ordinary deletion call signature.
    if payload.recurrence_scope is None:
        return delete_event(
            payload.event_id,
            payload.confirmed,
        )

    return delete_event(
        payload.event_id,
        payload.confirmed,
        payload.recurrence_scope,
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
        parsed_end,
        existing_event=existing,
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

    start_datetime, end_datetime = parse_search_range(
        payload.start,
        payload.end,
    )

    return search_events(
        start_datetime,
        end_datetime,
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

    start_datetime, end_datetime = parse_search_range(
        payload.start,
        payload.end,
    )

    return find_similar_events(
        payload.title,
        start_datetime,
        end_datetime,
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
    mcp.run(transport="stdio")
