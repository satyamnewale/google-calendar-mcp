from datetime import date, datetime, time, timedelta
from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from errors.error_handler import handle_tool_errors
from errors.exceptions import ConfirmationRequiredError

from services.event_service import (
    create_event,
    update_event,
    delete_event,
    get_event_details,
    postpone_event,
)
from services.event_search import search_events, find_similar_events
from services.calendar_summary import get_calendar_summary
from services.availability_service import (
    check_availability,
    get_available_slots,
    find_occurrence_conflicts,
)
from services.calendar_service import list_calendars

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
            description=(
                "Event title. Must contain at least one non-whitespace "
                "character and cannot exceed 200 characters."
            ),
        ),
    ],
    start: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Event start date or datetime. Use YYYY-MM-DD for an "
                "all-day event or an ISO datetime for a timed event. "
                "Supported natural-language date expressions are also accepted."
            ),
        ),
    ],
    end: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "End date or datetime. For an all-day event, this is the "
                "inclusive final date. For a timed event, it is the exact "
                "end datetime. Must match the type of start. If omitted, "
                "defaults to one hour for timed events or one day for "
                "all-day events."
            ),
        ),
    ] = None,
    description: Annotated[
        str | None,
        Field(
            default=None,
            max_length=8192,
            description="Optional event description, agenda, or notes.",
        ),
    ] = None,
    location: Annotated[
        str | None,
        Field(
            default=None,
            max_length=500,
            description="Optional physical or online event location.",
        ),
    ] = None,
    all_day: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "True when the event occupies one or more complete " "calendar dates."
            ),
        ),
    ] = False,
    recurrence_frequency: Annotated[
        Literal["DAILY", "WEEKLY", "MONTHLY", "YEARLY"] | None,
        Field(
            default=None,
            description=("Recurrence frequency: DAILY, WEEKLY, MONTHLY, or YEARLY."),
        ),
    ] = None,
    recurrence_interval: Annotated[
        int,
        Field(
            default=1,
            ge=1,
            le=365,
            description="Number of frequency periods between occurrences.",
        ),
    ] = 1,
    recurrence_days: Annotated[
        list[Literal["MO", "TU", "WE", "TH", "FR", "SA", "SU"]] | None,
        Field(
            default=None,
            description=(
                "Weekdays for a weekly recurrence, using MO, TU, WE, " "TH, FR, SA, SU."
            ),
        ),
    ] = None,
    recurrence_count: Annotated[
        int | None,
        Field(
            default=None,
            gt=0,
            le=500,
            strict=True,
            description=("Total number of occurrences, including the first."),
        ),
    ] = None,
    recurrence_until: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Inclusive final recurrence date or datetime. "
                "Mutually exclusive with recurrence_count and "
                "recurrence_indefinite."
            ),
        ),
    ] = None,
    recurrence_indefinite: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "True for an indefinite recurrence. Mutually exclusive "
                "with recurrence_count and recurrence_until."
            ),
        ),
    ] = False,
    reminder_minutes: Annotated[
        int,
        Field(
            default=10,
            ge=0,
            le=40320,
            description="Popup reminder lead time in minutes.",
        ),
    ] = 10,
    allow_conflict: Annotated[
        bool,
        Field(
            default=False,
            description=("True to create despite conflicts. Defaults to False."),
        ),
    ] = False,
) -> dict:
    """
    Create an event or recurring event series.

    For all-day events, `end` is the inclusive final date. The tool
    converts it to Google Calendar's exclusive end date internally.

    Recurring events must specify exactly one of recurrence_count,
    recurrence_until, or recurrence_indefinite=True.
    """

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

    start_value = parse_date_or_datetime(
        payload.start,
        all_day=payload.all_day,
    )

    requested_end_inclusive = None

    if payload.all_day:

        if payload.end:
            requested_end_inclusive = parse_date_or_datetime(
                payload.end,
                all_day=True,
            )

            if requested_end_inclusive < start_value:
                raise ValueError(
                    "The inclusive all-day end date cannot be before start."
                )

            end_value = requested_end_inclusive + timedelta(days=1)

        else:
            requested_end_inclusive = start_value
            end_value = start_value + timedelta(days=1)

    elif payload.end:
        end_value = parse_date_or_datetime(
            payload.end,
            all_day=False,
        )

    else:
        end_value = start_value + timedelta(hours=1)

    if payload.recurrence_frequency and payload.recurrence_days:

        weekday_codes = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]

        event_date = (
            start_value
            if isinstance(start_value, date) and not isinstance(start_value, datetime)
            else start_value.date()
        )

        actual_weekday = weekday_codes[event_date.weekday()]

        if actual_weekday not in payload.recurrence_days:
            raise ValueError(
                f"The starting date falls on {actual_weekday}, which "
                "is not included in recurrence_days."
            )

    if payload.recurrence_until:

        if payload.all_day:
            until_value = date.fromisoformat(payload.recurrence_until)

            if until_value < start_value:
                raise ValueError("Recurrence end date cannot be before event start.")

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

    occurrences = generate_occurrence_windows(
        start=start_value,
        end=end_value,
        recurrence=recurrence,
        all_day=payload.all_day,
        indefinite=payload.recurrence_indefinite,
    )

    range_start = min(item[0] for item in occurrences)
    range_end = max(item[1] for item in occurrences)

    availability = check_availability(
        range_start,
        range_end,
    )

    occurrence_conflicts = find_occurrence_conflicts(
        occurrences,
        availability["busy_periods"],
    )

    user_visible_range = None

    if payload.all_day:
        user_visible_range = {
            "start_date": start_value.isoformat(),
            "end_date_inclusive": requested_end_inclusive.isoformat(),
        }

    if occurrence_conflicts and not payload.allow_conflict:
        result = {
            "success": False,
            "conflict": True,
            "message": (
                "One or more event occurrences overlap existing "
                "calendar commitments. Confirm whether you want to proceed."
            ),
            "conflicting_occurrences": occurrence_conflicts,
            "busy_periods": availability.get("busy_periods", []),
        }

        if user_visible_range is not None:
            result["user_visible_range"] = user_visible_range

        return result

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

    if user_visible_range is not None:
        result["user_visible_range"] = user_visible_range

    if payload.recurrence_indefinite:
        result["availability_check"] = {
            "complete": False,
            "horizon_days": 90,
            "message": (
                "Conflicts were checked only within the next 90 days "
                "because this recurrence is indefinite."
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
            description="Unique Google Calendar event identifier. Obtain it from an event search or event details result.",
        ),
    ],
    updates: Annotated[
        dict,
        Field(
            min_length=1,
            description=(
                "Non-empty dictionary of fields to update. Supported keys: "
                "summary, description, location, start, end, reminders, "
                "recurrence, visibility, transparency. Supply only fields "
                "that should change. When changing the schedule, provide "
                "both start and end as Google Calendar event date objects."
            ),
        ),
    ],
) -> dict:
    """
    Update selected fields of an existing Google Calendar event.

    INPUTS:
    - event_id: Unique identifier of the existing event.
    - updates: Non-empty dictionary containing one or more supported fields.

    SUPPORTED UPDATE FIELDS:
    - summary: Event title.
    - description: Event description.
    - location: Event location.
    - start and end: Event date or datetime objects.
    - reminders: Reminder configuration.
    - recurrence: Google Calendar recurrence rule.
    - visibility: Event visibility.
    - transparency: Availability transparency.

    BEHAVIOR:
    - Only supplied fields are modified; other event fields are preserved.
    - Unsupported update keys are rejected.
    - At least one update field is required.
    - Schedule changes require both start and end.
    - Start and end must use matching date or dateTime representations.
    - Recurrence updates are validated.
    - Updates use the event's current ETag to avoid overwriting
      changes made by another client after retrieval.

    OUTPUT:
    Returns the updated Google Calendar event resource.
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
            description="Unique Google Calendar event identifier of the event to delete.",
        ),
    ],
    confirmed: Annotated[
        bool,
        Field(
            default=False,
            description="Explicit confirmation that deletion is authorized. Must be True for deletion to proceed.",
        ),
    ] = False,
    recurrence_scope: Annotated[
        Literal["event", "series"] | None,
        Field(
            default=None,
            description=(
                "Deletion scope for recurring events. Use 'event' to delete "
                "one recurring occurrence or 'series' to delete the entire "
                "recurring series. Leave unset for a normal one-time event."
            ),
        ),
    ] = None,
) -> dict:
    """
    Delete an existing Google Calendar event.

    INPUTS:
    - event_id: Unique identifier of the event.
    - confirmed: Must be True before deletion can proceed.
    - recurrence_scope:
      - event: Delete one recurring occurrence.
      - series: Delete the entire recurring series.
      - None: Normal one-time event.

    BEHAVIOR:
    - Requires explicit confirmation.
    - Retrieves the existing event before deletion.
    - A recurring master event requires recurrence_scope='series'.
    - A recurring occurrence can be deleted individually.
    - A non-recurring event cannot use recurrence_scope='series'.
    - Already-cancelled events are not deleted again.
    - Uses the event ETag to prevent deleting an event that changed
      after it was retrieved.

    OUTPUT:
    Returns the deletion status, event identifier, and status message.
    """

    payload = DeleteEventSchema.model_validate(
        {
            "event_id": event_id,
            "confirmed": confirmed,
            "recurrence_scope": recurrence_scope,
        }
    )

    if not payload.confirmed:
        raise ConfirmationRequiredError(
            "Event deletion requires explicit user confirmation."
        )

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
            description="Unique Google Calendar event identifier.",
        ),
    ],
) -> dict:
    """
    Retrieve the details of one Google Calendar event.

    INPUT:
    - event_id: Unique identifier of the event.

    BEHAVIOR:
    Fetches the event resource associated with the supplied identifier.
    This operation does not modify the event.

    OUTPUT:
    Returns the available Google Calendar event resource, including
    fields such as event ID, title, description, location, start,
    end, recurrence, reminders, attendees, and status when present.
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
            description="Unique Google Calendar event ID to reschedule.",
        ),
    ],
    new_start: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "New start date or datetime. Use a date for an all-day "
                "event or an ISO datetime for a timed event."
            ),
        ),
    ],
    new_end: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "For an all-day event, the inclusive final date. For a "
                "timed event, the exact end datetime."
            ),
        ),
    ],
) -> dict:
    """
    Change the scheduled start and end of an existing calendar event.

    INPUTS:
    - event_id: Unique identifier of the existing event.
    - new_start: Replacement start date or datetime.
    - new_end: Replacement end date or datetime.

    BEHAVIOR:
    - Retrieves the existing event to determine whether it is all-day
      or timed.
    - Parses the supplied values according to the existing event type.
    - Validates that the new end is after the new start.
    - Preserves other event information, including title, description,
      location, reminders, and recurrence settings.
    - Cancelled events cannot be postponed.
    - Uses conditional event updating to protect against concurrent changes.

    OUTPUT:
    Returns the updated Google Calendar event resource.
    """

    payload = PostponeEventSchema.model_validate(
        {
            "event_id": event_id,
            "new_start": new_start,
            "new_end": new_end,
        }
    )

    existing = get_event_details(payload.event_id)
    is_all_day = "date" in existing.get("start", {})

    if is_all_day:
        parsed_start = resolve_date_expression(payload.new_start)
        parsed_end_inclusive = resolve_date_expression(payload.new_end)

        if parsed_end_inclusive < parsed_start:
            raise ValueError("The inclusive all-day end date cannot be before start.")

        parsed_end = parsed_end_inclusive + timedelta(days=1)

    else:
        parsed_start = parse_datetime(payload.new_start)
        parsed_end = parse_datetime(payload.new_end)
        parsed_end_inclusive = None

    updated_event = postpone_event(
        payload.event_id,
        parsed_start,
        parsed_end,
        existing_event=existing,
    )

    if is_all_day:
        return {
            "success": True,
            "event": updated_event,
            "user_visible_range": {
                "start_date": parsed_start.isoformat(),
                "end_date_inclusive": parsed_end_inclusive.isoformat(),
            },
        }

    return updated_event


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
            description="Inclusive beginning of the event search range. Accepts an ISO date, ISO datetime, or supported natural date expression.",
        ),
    ],
    end: Annotated[
        str,
        Field(
            min_length=1,
            description="End of the event search range. Accepts an ISO date, ISO datetime, or supported natural date expression. Must resolve to a value after start.",
        ),
    ],
    title: Annotated[
        str | None,
        Field(
            default=None,
            max_length=200,
            description="Optional full or partial event title filter. Matching is case-insensitive and uses substring matching. Leave unset to retrieve all events in the range.",
        ),
    ] = None,
) -> list:
    """
    Retrieve calendar events within a specified date or datetime range.

    INPUTS:
    - start: Beginning of the search range.
    - end: End of the search range.
    - title: Optional full or partial event title.

    BEHAVIOR:
    - Accepts ISO date, ISO datetime, and supported natural date expressions.
    - Date-only end boundaries are treated as inclusive.
    - Explicit datetime boundaries retain their supplied time values.
    - If title is supplied, results are filtered using case-insensitive
      substring matching.
    - If title is omitted, all matching events in the range are returned.
    - Results are retrieved in chronological order.
    - The configured event retrieval limit applies; exceeding it produces
      an explicit error rather than silently returning incomplete results.

    OUTPUT:
    Returns a list of matching Google Calendar event resources.
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
            description="Event title or search phrase used to identify events with similar names. Maximum 200 characters.",
        ),
    ],
    start: Annotated[
        str,
        Field(
            min_length=1,
            description="Beginning of the search range. Accepts an ISO date, ISO datetime, or supported natural date expression.",
        ),
    ],
    end: Annotated[
        str,
        Field(
            min_length=1,
            description="End of the search range. Accepts an ISO date, ISO datetime, or supported natural date expression.",
        ),
    ],
) -> list:
    """
    Find calendar events with titles similar to a supplied search phrase.

    INPUTS:
    - title: Required event title or phrase.
    - start: Beginning of the search range.
    - end: End of the search range.

    BEHAVIOR:
    - Retrieves events within the supplied range.
    - Compares the supplied phrase with each event title using
      character-sequence similarity.
    - Uses the configured similarity threshold.
    - Excludes events without a title.
    - Orders matching results from highest to lowest similarity.
    - Search-range validation and event retrieval limits apply.

    OUTPUT:
    Returns a list of objects containing:
    - event: Matching Google Calendar event resource.
    - similarity: Similarity score rounded to three decimal places.

    This is title similarity matching, not semantic or embedding-based search.
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
            description="Calendar aggregation period. Supported values: day, week, month.",
        ),
    ],
    value: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional date or period expression identifying the requested period. Examples include today, tomorrow, next week, and November 2026. Defaults to the current period.",
        ),
    ] = None,
) -> dict:
    """
    Generate a calendar overview for a day, week, or month.

    INPUTS:
    - period: day, week, or month.
    - value: Optional date or period expression.

    BEHAVIOR:
    - If value is omitted, the current period is used.
    - A day overview retrieves events for the selected day.
    - A week overview groups events by the dates they occupy.
    - A month overview aggregates event counts by date.
    - Multi-day events can appear on each date they occupy.
    - All-day and timed events are handled using their respective
      date and datetime boundaries.

    OUTPUT:
    - Day: Selected date, total event count, and event list.
    - Week: Total event count and events grouped by date.
    - Month: Total event count and daily event counts.

    Supported period values are limited to day, week, and month.
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
            description="Start of the availability interval. Provide an ISO datetime with a date and time.",
        ),
    ],
    end: Annotated[
        str,
        Field(
            min_length=1,
            description="End of the availability interval. Provide an ISO datetime with a date and time. Must occur after start.",
        ),
    ],
) -> dict:
    """
    Check whether a calendar time interval contains existing commitments.

    INPUTS:
    - start: Start datetime of the interval.
    - end: End datetime of the interval.

    BEHAVIOR:
    - Parses the supplied datetime values.
    - Requires a valid interval with end after start.
    - Queries the Google Calendar FreeBusy API.
    - Returns busy periods that overlap the requested interval.
    - Does not create, modify, or reserve an event.

    OUTPUT:
    Returns:
    - available: True when no busy periods overlap the interval;
      otherwise False.
    - busy_periods: List of overlapping busy intervals, each containing
      start and end timestamps.

    The supplied values should be unambiguous ISO datetimes.
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
            description=("Start boundary as an ISO 8601 datetime with timezone."),
        ),
    ],
    end: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "End of the search range. A date-only end includes that whole day; "
                "an ISO datetime is an exact boundary."
            )
        ),
    ],
    duration_minutes: Annotated[
        int,
        Field(
            default=60,
            gt=0,
            le=1440,
            description="Exact duration of each suggested slot in minutes.",
        ),
    ] = 60,
    slot_interval_minutes: Annotated[
        int,
        Field(
            default=15,
            gt=0,
            le=1440,
            description="Minutes between consecutive candidate start times.",
        ),
    ] = 15,
    max_suggestions: Annotated[
        int,
        Field(
            default=10,
            ge=1,
            le=50,
            description="Maximum number of candidate slots to return.",
        ),
    ] = 10,
    workday_start_time: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional daily working-hours start in HH:MM format.",
        ),
    ] = None,
    workday_end_time: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional daily working-hours end in HH:MM format.",
        ),
    ] = None,
    exclude_weekends: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "Skip Saturdays and Sundays. Without workday times, "
                "search the full weekday portions of the requested range."
            ),
        ),
    ] = False,
) -> list:
    """
    Find free candidate slots in chronological order.

    Without working-hour boundaries, the full supplied interval is searched.
    If weekends are excluded without working hours, full weekdays are searched.
    The end boundary is exclusive. This tool only suggests slots; it does not
    create or reserve an event.
    """

    payload = AvailableSlotsSchema.model_validate(
        {
            "start": start,
            "end": end,
            "duration_minutes": duration_minutes,
            "slot_interval_minutes": slot_interval_minutes,
            "max_suggestions": max_suggestions,
            "workday_start_time": workday_start_time,
            "workday_end_time": workday_end_time,
            "exclude_weekends": exclude_weekends,
        }
    )

    start_value, end_value = parse_search_range(
        payload.start,
        payload.end,
    )

    return get_available_slots(
        start_value,
        end_value,
        payload.duration_minutes,
        payload.slot_interval_minutes,
        payload.max_suggestions,
        payload.workday_start_time,
        payload.workday_end_time,
        payload.exclude_weekends,
    )


# ==================================================
# 11. LIST CALENDARS
# ==================================================


@mcp.tool()
@handle_tool_errors
def get_calendar_list() -> list:
    """
    Retrieve calendars accessible to the authenticated Google account.

    INPUTS:
    This tool does not require any input parameters.

    BEHAVIOR:
    - Retrieves the calendars available through the authenticated account.
    - Does not create, modify, or delete calendars.
    - Returns selected metadata for each accessible calendar.

    OUTPUT:
    Returns a list of calendar objects containing:
    - id: Calendar identifier.
    - summary: Calendar display name.
    - primary: Whether this is the primary calendar.
    - timeZone: Calendar timezone when available.
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
