from typing import Annotated, Literal
from datetime import date, datetime
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

# --------------------------------------------------
# COMMON CONFIGURATION
# --------------------------------------------------


class StrictSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


# --------------------------------------------------
# 1. CREATE EVENT
# --------------------------------------------------


class CreateEventSchema(StrictSchema):

    title: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description=(
                "Title or subject of the calendar event. "
                "Must contain at least one non-whitespace character."
            ),
        ),
    ]

    start: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Start date or datetime of the event. "
                "Use YYYY-MM-DD for all-day events or ISO datetime for timed events. "
                "Natural expressions such as 'tomorrow' are also supported."
            ),
        ),
    ]

    end: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "End date or datetime of the event. "
                "Must use the same event type as start. "
                "Optional; defaults to one hour after start for timed events."
            ),
        ),
    ] = None

    description: Annotated[
        str | None,
        Field(
            default=None,
            max_length=8192,
            description=(
                "Additional information, agenda, or notes associated with the event. "
                "Optional; leave empty when no description is required."
            ),
        ),
    ] = None

    location: Annotated[
        str | None,
        Field(
            default=None,
            max_length=500,
            description=(
                "Physical address, office location, or meeting venue. "
                "Optional; can also contain an online meeting location."
            ),
        ),
    ] = None

    all_day: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "Set True when creating an event lasting an entire calendar day. "
                "When enabled, start and end must represent dates rather than timed datetimes."
            ),
        ),
    ] = False

    recurrence_frequency: Annotated[
        Literal["DAILY", "WEEKLY", "MONTHLY", "YEARLY"] | None,
        Field(
            default=None,
            description=(
                "Frequency for repeating the event. "
                "Supported values: DAILY, WEEKLY, MONTHLY, YEARLY. "
                "Leave empty for a one-time event."
            ),
        ),
    ] = None

    recurrence_interval: Annotated[
        int,
        Field(
            default=1,
            ge=1,
            le=365,
            description=(
                "Number of frequency units between recurring events. "
                "For example, 2 with WEEKLY creates an event every two weeks. "
                "Requires recurrence_frequency."
            ),
        ),
    ] = 1

    recurrence_days: Annotated[
        list[Literal["MO", "TU", "WE", "TH", "FR", "SA", "SU"]] | None,
        Field(
            default=None,
            description=(
                "Weekdays for recurring events using two-letter day codes: MO, TU, WE, TH, FR, SA, SU. "
                "Primarily used with WEEKLY recurrence."
            ),
        ),
    ] = None

    recurrence_count: Annotated[
        int | None,
        Field(
            default=None,
            gt=0,
            le = 500,
            strict=True,
            description=(
                "Total number of occurrences, including the first occurrence. "
                "Maximum 500."
            ),
        ),
    ] = None

    recurrence_until: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "End date or datetime for recurring events. "
                "Must use the same event type as start. "
                "Requires recurrence_frequency."
            ),
        ),
    ] = None

    recurrence_indefinite: Annotated[
        bool,
        Field(
            default=False,
            strict=True,
            description=(
                "Set True to repeat the event indefinitely. "
                "Requires recurrence_frequency."
            ),
        ),
    ] = False

    reminder_minutes: Annotated[
        int,
        Field(
            default=10,
            ge=0,
            le=40320,
            description=(
                "Number of minutes before the event to trigger a popup reminder. "
                "For example, 10 sends a reminder ten minutes before the event. "
                "Use 0 for an immediate reminder."
            ),
        ),
    ] = 10

    allow_conflict: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "Set True to create the event even when the requested time overlaps existing events. "
                "When False, conflicting time slots require confirmation before creation."
            ),
        ),
    ] = False

    @field_validator("recurrence_until")
    @classmethod
    def validate_recurrence_until(cls, value):

        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError(
                "Recurrence end date cannot be empty."
            )

        # Check ISO date: YYYY-MM-DD
        try:
            date.fromisoformat(value)
            return value
        except ValueError:
            pass

        # Check ISO datetime
        try:
            datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
            return value

        except ValueError as exc:
            raise ValueError(
                "recurrence_until must be an ISO date "
                "or ISO datetime."
            ) from exc

    @field_validator("recurrence_days")
    @classmethod
    def validate_recurrence_days(cls, days):

        if days is not None and len(days) != len(set(days)):
            raise ValueError(
                "Recurrence weekdays cannot contain duplicates."
            )

        return days

    @model_validator(mode="after")
    def validate_recurrence(self):

        has_count = self.recurrence_count is not None
        has_until = self.recurrence_until is not None
        is_indefinite = self.recurrence_indefinite

        termination_options = sum([
            has_count,
            has_until,
            is_indefinite,
        ])

        if self.recurrence_frequency is None:

            if self.recurrence_days:
                raise ValueError(
                    "recurrence_days requires recurrence_frequency."
                )

            if self.recurrence_interval != 1:
                raise ValueError(
                    "recurrence_interval requires recurrence_frequency."
                )

            if termination_options:
                raise ValueError(
                    "Recurrence termination options require "
                    "recurrence_frequency."
                )

            return self

        if termination_options != 1:
            raise ValueError(
                "A recurring event must specify exactly one of "
                "recurrence_count, recurrence_until, "
                "or recurrence_indefinite=True."
            )

        if (
            self.recurrence_days
            and self.recurrence_frequency != "WEEKLY"
        ):
            raise ValueError(
                "recurrence_days is supported only for WEEKLY recurrence."
            )

        if self.recurrence_until and self.all_day:

            try:
                date.fromisoformat(
                    self.recurrence_until
                )

            except ValueError as exc:
                raise ValueError(
                    "All-day recurring events require a "
                    "date-only recurrence_until value."
                ) from exc

        return self


# --------------------------------------------------
# 2. UPDATE EVENT
# --------------------------------------------------


class UpdateEventSchema(StrictSchema):

    event_id: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Unique Google Calendar event ID identifying the existing event to modify. "
                "Obtain this identifier from event search or event details."
            ),
        ),
    ]

    updates: Annotated[
        dict,
        Field(
            min_length=1,
            description=(
                "Dictionary containing the event fields to modify. "
                "Supported fields include summary, description, location, start, end, reminders, and recurrence. "
                "Provide only the fields requiring changes."
            ),
        ),
    ]

    @field_validator("updates")
    @classmethod
    def validate_update_fields(cls, updates):

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

        invalid_fields = set(updates.keys()) - allowed_fields

        if invalid_fields:
            raise ValueError(
                f"Unsupported update fields: {', '.join(sorted(invalid_fields))}"
            )

        return updates


# --------------------------------------------------
# 3. DELETE EVENT
# --------------------------------------------------


class DeleteEventSchema(StrictSchema):

    event_id: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Unique Google Calendar event ID identifying the event to delete. "
                "Obtain this identifier from event search or event details."
            ),
        ),
    ]

    confirmed: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "Explicit user confirmation to permanently delete the selected event. "
                "Must be True before the deletion operation can proceed."
            ),
        ),
    ] = False

    
    recurrence_scope: Annotated[
        Literal["series", "event"] | None,
        Field(
            default=None,
            description=(
                "Use 'event' to delete one recurring occurrence. "
                "Use 'series' to delete the entire recurring series. "
                "Leave None for a normal one-time event."
            ),
        ),
    ] = None


# --------------------------------------------------
# 4. GET EVENT DETAILS
# --------------------------------------------------


class GetEventSchema(StrictSchema):

    event_id: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Unique Google Calendar event ID for retrieving complete event details, "
                "including title, description, location, start time, end time, and recurrence."
            ),
        ),
    ]


# --------------------------------------------------
# 5. POSTPONE EVENT
# --------------------------------------------------


class PostponeEventSchema(StrictSchema):

    event_id: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Unique Google Calendar event ID identifying the existing event to reschedule. "
                "Obtain this identifier from event search or event details."
            ),
        ),
    ]

    new_start: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "New start date or datetime for the postponed event. "
                "Use YYYY-MM-DD for all-day events or ISO datetime for timed events. "
                "Natural date expressions are also supported."
            ),
        ),
    ]

    new_end: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "New end date or datetime for the postponed event. "
                "Must match the original event type and occur after new_start."
            ),
        ),
    ]


# --------------------------------------------------
# 6. SEARCH EVENTS
# --------------------------------------------------


class SearchEventsSchema(StrictSchema):

    start: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Beginning of the calendar search range. "
                "Use an ISO date or datetime string, or a supported natural date expression."
            ),
        ),
    ]

    end: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Ending of the calendar search range. "
                "Must occur after start. Defines the upper boundary of the event search."
            ),
        ),
    ]

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
    ] = None


# --------------------------------------------------
# 7. FIND SIMILAR EVENTS
# --------------------------------------------------


class SimilarEventsSchema(StrictSchema):

    title: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description=(
                "Event title or phrase used to find existing events with similar names. "
                "Similarity scores determine how closely event titles match the supplied query."
            ),
        ),
    ]

    start: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Beginning of the date or datetime range for searching similar events. "
                "Use ISO format or a supported natural date expression."
            ),
        ),
    ]

    end: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Ending of the date or datetime range for searching similar events. "
                "Must occur after start and defines the search boundary."
            ),
        ),
    ]


# --------------------------------------------------
# 8. CALENDAR OVERVIEW
# --------------------------------------------------


class CalendarOverviewSchema(StrictSchema):

    period: Annotated[
        Literal["day", "week", "month"],
        Field(
            description=(
                "Time period for generating the calendar overview. "
                "Supported values: day, week, or month."
            ),
        ),
    ]

    value: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Date or period expression used to select the requested calendar overview. "
                "Examples: 'tomorrow', 'next week', or 'November 2026'. "
                "Defaults to the current period when omitted."
            ),
        ),
    ] = None


# --------------------------------------------------
# 9. CHECK AVAILABILITY
# --------------------------------------------------


class AvailabilitySchema(StrictSchema):

    start: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Beginning of the requested availability time slot. "
                "Provide an ISO datetime containing the desired date and time."
            ),
        ),
    ]

    end: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Ending of the requested availability time slot. "
                "Must occur after start and defines the period checked for existing calendar conflicts."
            ),
        ),
    ]


# --------------------------------------------------
# 10. SUGGEST AVAILABLE SLOTS
# --------------------------------------------------



class AvailableSlotsSchema(StrictSchema):

    start: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Beginning of the date or datetime range "
                "for available slot discovery."
            ),
        ),
    ]

    end: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Ending of the date or datetime range "
                "for available slot discovery."
            ),
        ),
    ]

    duration_minutes: Annotated[
        int,
        Field(
            default=60,
            gt=0,
            le=1440,
            description="Exact duration of each suggested slot in minutes.",
        ),
    ] = 60

    slot_interval_minutes: Annotated[
        int,
        Field(
            default=15,
            gt=0,
            le=1440,
            description=(
                "Minutes between consecutive suggested start times."
            ),
        ),
    ] = 15

    max_suggestions: Annotated[
        int,
        Field(
            default=10,
            ge=1,
            le=50,
            description="Maximum number of candidate slots to return.",
        ),
    ] = 10


# --------------------------------------------------
# 11. DELETE EVENT
# --------------------------------------------------


class DeleteEventSchema(StrictSchema):

    event_id: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Unique Google Calendar event ID identifying "
                "the event to delete."
            ),
        ),
    ]

    confirmed: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "Explicit user confirmation required before deletion."
            ),
        ),
    ] = False

    recurrence_scope: Annotated[
        Literal["series", "event"] | None,
        Field(
            default=None,
            description=(
                "'event' deletes one recurring occurrence. "
                "'series' deletes the entire recurring series. "
                "None is used for a normal event."
            ),
        ),
    ] = None
