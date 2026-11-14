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
                "end datetime. Must match the type of start."
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
Create a Google Calendar event or recurring event series.

WHEN TO USE:
- "Schedule a project meeting tomorrow at 5 PM."
- "Create a recurring weekly meeting."
- When a confirmed scheduling request needs execution.

INPUT:
- title: Event title.
- start and end: Event date/time.
- Optional description, location and timezone.
- Optional all-day, recurrence and reminder settings.
- Optional conflict handling.

WORKING:
- Validates event information.
- Constructs the Google Calendar event.
- Applies reminders and recurrence settings.
- Submits the event to Google Calendar.

OUTPUT:
- Creation status.
- Event ID.
- Event title.
- Start and end.
- Event details.

IMPORTANT:
- Use an explicit IANA timezone for timed events.
- All-day events use date boundaries.
- Check availability when appropriate.
- Never claim success without a successful API result.
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
                "recurrence, visibility, transparency."
            ),
        ),
    ],
) -> dict:
    """
Update selected properties of an existing Google Calendar event.

WHEN TO USE:
- "Change tomorrow's meeting location."
- "Rename the project discussion event."
- "Move the meeting to 6 PM."

INPUT:
- event_id: Existing Google Calendar event ID.
- updates: Dictionary containing supported fields.
- Schedule changes require both start and end.

WORKING:
- Retrieves the existing event.
- Validates requested changes.
- Applies only supplied updates.
- Protects against concurrent modifications using event version information.

OUTPUT:
- Updated event details.
- Event ID.
- Updated fields.
- Operation status.

IMPORTANT:
- Do not replace unspecified fields.
- Validate timezone when changing event times.
- Use get_calendar_event when event details are unknown.
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
Delete an existing Google Calendar event or recurring event occurrence.

WHEN TO USE:
- "Delete tomorrow's project meeting."
- "Remove the entire recurring meeting series."
- When the user explicitly requests event deletion.

INPUT:
- event_id: Existing event ID.
- confirmed: Explicit deletion confirmation.
- recurrence_scope: Optional event or series selection.

WORKING:
- Validates confirmation.
- Retrieves the existing event.
- Determines the requested deletion scope.
- Executes the Google Calendar deletion.

OUTPUT:
- Deletion status.
- Event ID.
- Deleted event information.

IMPORTANT:
- Requires confirmed=True.
- Recurring events require an explicit deletion scope.
- Never infer confirmation from unrelated conversation history.
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
Retrieve complete available details of one Google Calendar event.

WHEN TO USE:
- "Show me the details of my project meeting."
- "What time is my next meeting?"
- Before editing, postponing or deleting an event.

INPUT:
- event_id: Google Calendar event identifier.

WORKING:
- Retrieves the specified event.
- Extracts its available properties.
- Returns the event without modifying it.

OUTPUT:
- Event ID and title.
- Description and location.
- Start and end.
- Timezone and recurrence.
- Attendees, reminders and status.

IMPORTANT:
- Requires a valid event ID.
- Does not modify or delete events.
- Use find_calendar_events when the event ID is unknown.
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
Reschedule an existing Google Calendar event to a new date or time.

WHEN TO USE:
- "Move tomorrow's meeting to Friday."
- "Postpone the project meeting by two hours."
- When the user wants to change an existing event's schedule.

INPUT:
- event_id: Existing event ID.
- new_start: Requested new start.
- new_end: Requested new end.

WORKING:
- Retrieves the existing event.
- Identifies its event type.
- Validates the new schedule.
- Updates the event while preserving other properties.

OUTPUT:
- Updated event ID.
- New start and end.
- Updated event details.
- Operation status.

IMPORTANT:
- Requires a valid event ID.
- Start must precede end.
- Preserve the intended event timezone.
- Use edit_calendar_event for general property changes.
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
Search Google Calendar events within a specified date or datetime range.

WHEN TO USE:
- "Show my meetings tomorrow."
- "Find all project meetings this week."
- "Find events containing the word discussion."

INPUT:
- start: Search range beginning.
- end: Search range ending.
- title: Optional partial title filter.

WORKING:
- Validates search boundaries.
- Retrieves events within the requested range.
- Applies title filtering when supplied.
- Orders results chronologically.

OUTPUT:
- Matching event IDs.
- Titles and descriptions.
- Start and end.
- Locations and other available metadata.

IMPORTANT:
- Date-only end boundaries are inclusive.
- Specify timezone when interpreting local datetime boundaries.
- Retrieval limits apply.
- Use get_calendar_event for complete details of one event.
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
Find calendar events with titles similar to a supplied phrase.

WHEN TO USE:
- "Find meetings similar to project discussion."
- "Look for events related to the product review."
- When the exact event title is unknown.

INPUT:
- title: Search phrase.
- start: Search range beginning.
- end: Search range ending.

WORKING:
- Retrieves events within the specified range.
- Compares event titles using character-sequence similarity.
- Ranks matching events by similarity.

OUTPUT:
- Matching event details.
- Event IDs.
- Similarity scores.
- Chronologically relevant information.

IMPORTANT:
- Uses string similarity, not semantic search.
- Search range and retrieval limits apply.
- Use get_calendar_event to inspect a selected result.
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
Generate a calendar overview for a specified day, week, or month.

WHEN TO USE:
- "Show my calendar for today."
- "Give me this week's schedule."
- "How many meetings do I have this month?"

INPUT:
- period: Day, week, or month.
- value: Optional date or period expression.
- timezone: Optional timezone if supported by the implementation.

WORKING:
- Determines the requested calendar period.
- Retrieves relevant calendar events.
- Organizes results according to the selected period.
- Calculates daily event counts where applicable.

OUTPUT:
- Period boundaries.
- Event details.
- Daily event groups.
- Event counts.

IMPORTANT:
- Defaults to the current period when value is omitted.
- Multi-day events can occupy multiple calendar dates.
- Use find_calendar_events for custom date ranges.
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
Check whether a specified calendar interval contains existing commitments.

WHEN TO USE:
- "Am I free tomorrow at 5 PM?"
- "Check whether Friday afternoon is available."
- Before creating a meeting where conflicts matter.

INPUT:
- start: Requested interval beginning.
- end: Requested interval ending.

WORKING:
- Validates the requested interval.
- Queries Google Calendar FreeBusy.
- Identifies overlapping busy periods.
- Determines whether the interval is available.

OUTPUT:
- Availability status.
- Busy intervals.
- Requested start and end.
- Relevant calendar information.

IMPORTANT:
- End must be after start.
- Use unambiguous timezone-aware datetimes.
- This tool checks availability only.
- It does not create or reserve an event.
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
Find available meeting slots within a specified date or datetime range.

WHEN TO USE:
- "Find three available slots next week."
- "Suggest a one-hour meeting during working hours."
- When scheduling requires alternative time suggestions.

INPUT:
- start and end: Search boundaries.
- duration: Optional meeting duration.
- slot_interval: Optional interval between candidates.
- max_suggestions: Maximum number of suggestions.
- Optional working hours and weekend settings.

WORKING:
- Retrieves existing busy periods.
- Evaluates candidate time intervals.
- Applies working-hour and weekend restrictions.
- Returns suitable free slots.

OUTPUT:
- Suggested start and end times.
- Number of available suggestions.
- Relevant timezone information.

IMPORTANT:
- Suggestions are not reservations.
- End boundary is exclusive.
- Confirm availability again before creating an event.
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
Retrieve calendars accessible through the authenticated Google account.

WHEN TO USE:
- "Show my available calendars."
- "Which calendar should I use for this meeting?"
- When identifying a calendar before scheduling.

INPUT:
- No required input.

WORKING:
- Queries the authenticated Google Calendar account.
- Retrieves accessible calendar metadata.
- Identifies the primary calendar where available.

OUTPUT:
- Calendar IDs.
- Display names.
- Primary-calendar status.
- Timezone information when available.

IMPORTANT:
- Requires valid Google Calendar authentication.
- Does not create, update or delete calendars.
- Use the returned calendar ID when a tool supports calendar selection.
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
