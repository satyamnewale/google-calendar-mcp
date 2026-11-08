
import pytest
from pydantic import ValidationError

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

from utils.recurrence_utils import build_recurrence_rule

@pytest.mark.unit
def get_payload(**overrides):

    payload = {
        "title": "Workout Prep",
        "start": "2026-11-09T15:30:00+05:30",
        "recurrence_frequency": "DAILY",
        "recurrence_interval": 1,
        "recurrence_count": 21,
    }

    payload.update(overrides)

    return payload

@pytest.mark.unit
def test_valid_daily_recurrence_count():

    event = CreateEventSchema.model_validate(
        get_payload()
    )

    assert event.recurrence_count == 21

@pytest.mark.unit
def test_recurrence_requires_termination():

    with pytest.raises(ValidationError):

        CreateEventSchema.model_validate(
            get_payload(recurrence_count=None)
        )

@pytest.mark.unit
def test_recurrence_count_and_until_mutually_exclusive():

    with pytest.raises(ValidationError):

        CreateEventSchema.model_validate(
            get_payload(
                recurrence_count=21,
                recurrence_until="2026-11-29",
            )
        )

@pytest.mark.unit
def test_indefinite_recurrence_requires_explicit_flag():

    event = CreateEventSchema.model_validate(
        get_payload(
            recurrence_count=None,
            recurrence_indefinite=True,
        )
    )

    assert event.recurrence_indefinite is True

@pytest.mark.unit
def test_boolean_not_accepted_as_recurrence_count():

    with pytest.raises(ValidationError):

        CreateEventSchema.model_validate(
            get_payload(recurrence_count=True)
        )

@pytest.mark.unit
def test_daily_recurrence_rule_count():

    rule = build_recurrence_rule(
        frequency="DAILY",
        interval=1,
        count=21,
    )

    assert rule == [
        "RRULE:FREQ=DAILY;INTERVAL=1;COUNT=21"
    ]

@pytest.mark.unit
def test_daily_recurrence_rule_until():

    rule = build_recurrence_rule(
        frequency="DAILY",
        interval=1,
        until="2026-11-29",
    )

    assert rule[0].startswith(
        "RRULE:FREQ=DAILY;INTERVAL=1;UNTIL="
    )

# --------------------------------------------------
# CREATE EVENT SCHEMA
# --------------------------------------------------
@pytest.mark.unit
def test_valid_create_event():
    payload = {
        "title": "Team Meeting",
        "start": "2026-11-10T10:00:00+05:30",
        "all_day": False,
    }

    result = CreateEventSchema.model_validate(payload)

    assert result.title == "Team Meeting"

@pytest.mark.unit
def test_create_event_missing_title():
    payload = {
        "start": "2026-11-10T10:00:00+05:30",
    }

    with pytest.raises(ValidationError):
        CreateEventSchema.model_validate(payload)

@pytest.mark.unit
def test_create_event_empty_title():
    payload = {
        "title": "",
        "start": "2026-11-10T10:00:00+05:30",
    }

    with pytest.raises(ValidationError):
        CreateEventSchema.model_validate(payload)

@pytest.mark.unit
def test_create_event_invalid_recurrence_frequency():
    payload = {
        "title": "Meeting",
        "start": "2026-11-10T10:00:00+05:30",
        "recurrence_frequency": "HOURLY",
    }

    with pytest.raises(ValidationError):
        CreateEventSchema.model_validate(payload)

@pytest.mark.unit
def test_create_event_invalid_recurrence_interval():
    payload = {
        "title": "Meeting",
        "start": "2026-11-10T10:00:00+05:30",
        "recurrence_frequency": "DAILY",
        "recurrence_interval": 0,
    }

    with pytest.raises(ValidationError):
        CreateEventSchema.model_validate(payload)

@pytest.mark.unit
def test_create_event_invalid_reminder():
    payload = {
        "title": "Meeting",
        "start": "2026-11-10T10:00:00+05:30",
        "reminder_minutes": -1,
    }

    with pytest.raises(ValidationError):
        CreateEventSchema.model_validate(payload)

@pytest.mark.unit
def test_create_event_recurrence_days():

    payload = {
        "title": "Meeting",
        "start": "2026-11-10T10:00:00+05:30",
        "recurrence_frequency": "WEEKLY",
        "recurrence_days": ["MO", "WE"],
        "recurrence_count": 10,
    }

    result = CreateEventSchema.model_validate(payload)

    assert result.recurrence_days == ["MO", "WE"]
    assert result.recurrence_count == 10


# --------------------------------------------------
# UPDATE EVENT SCHEMA
# --------------------------------------------------
@pytest.mark.unit
def test_valid_update_event():
    payload = {
        "event_id": "event_001",
        "updates": {
            "summary": "Updated Meeting",
        },
    }

    result = UpdateEventSchema.model_validate(payload)

    assert result.event_id == "event_001"

@pytest.mark.unit
def test_update_event_missing_id():
    payload = {
        "updates": {
            "summary": "Updated Meeting",
        },
    }

    with pytest.raises(ValidationError):
        UpdateEventSchema.model_validate(payload)

@pytest.mark.unit
def test_update_event_empty_updates():
    payload = {
        "event_id": "event_001",
        "updates": {},
    }

    with pytest.raises(ValidationError):
        UpdateEventSchema.model_validate(payload)


# --------------------------------------------------
# DELETE EVENT SCHEMA
# --------------------------------------------------
@pytest.mark.unit
def test_valid_delete_event():
    payload = {
        "event_id": "event_001",
        "confirmed": True,
    }

    result = DeleteEventSchema.model_validate(payload)

    assert result.confirmed is True

@pytest.mark.unit
def test_delete_event_missing_id():
    payload = {
        "confirmed": True,
    }

    with pytest.raises(ValidationError):
        DeleteEventSchema.model_validate(payload)


# --------------------------------------------------
# GET EVENT SCHEMA
# --------------------------------------------------
@pytest.mark.unit
def test_valid_get_event():
    payload = {
        "event_id": "event_001",
    }

    result = GetEventSchema.model_validate(payload)

    assert result.event_id == "event_001"

@pytest.mark.unit
def test_get_event_empty_id():
    payload = {
        "event_id": "",
    }

    with pytest.raises(ValidationError):
        GetEventSchema.model_validate(payload)


# --------------------------------------------------
# POSTPONE EVENT SCHEMA
# --------------------------------------------------
@pytest.mark.unit
def test_valid_postpone_event():
    payload = {
        "event_id": "event_001",
        "new_start": "2026-11-11T10:00:00+05:30",
        "new_end": "2026-11-11T11:00:00+05:30",
    }

    result = PostponeEventSchema.model_validate(payload)

    assert result.event_id == "event_001"

@pytest.mark.unit
def test_postpone_event_missing_new_end():
    payload = {
        "event_id": "event_001",
        "new_start": "2026-11-11T10:00:00+05:30",
    }

    with pytest.raises(ValidationError):
        PostponeEventSchema.model_validate(payload)


# --------------------------------------------------
# SEARCH EVENTS SCHEMA
# --------------------------------------------------
@pytest.mark.unit
def test_valid_search_events():
    payload = {
        "start": "2026-11-10T00:00:00+05:30",
        "end": "2026-11-11T00:00:00+05:30",
        "title": "Meeting",
    }

    result = SearchEventsSchema.model_validate(payload)

    assert result.title == "Meeting"

@pytest.mark.unit
def test_search_events_missing_start():
    payload = {
        "end": "2026-11-11T00:00:00+05:30",
    }

    with pytest.raises(ValidationError):
        SearchEventsSchema.model_validate(payload)


# --------------------------------------------------
# SIMILAR EVENTS SCHEMA
# --------------------------------------------------
@pytest.mark.unit
def test_valid_similar_events():
    payload = {
        "title": "Team Meeting",
        "start": "2026-11-10T00:00:00+05:30",
        "end": "2026-11-11T00:00:00+05:30",
    }

    result = SimilarEventsSchema.model_validate(payload)

    assert result.title == "Team Meeting"

@pytest.mark.unit
def test_similar_events_empty_title():
    payload = {
        "title": "",
        "start": "2026-11-10T00:00:00+05:30",
        "end": "2026-11-11T00:00:00+05:30",
    }

    with pytest.raises(ValidationError):
        SimilarEventsSchema.model_validate(payload)


# --------------------------------------------------
# CALENDAR OVERVIEW SCHEMA
# --------------------------------------------------
@pytest.mark.unit
def test_valid_calendar_overview():
    payload = {
        "period": "week",
        "value": "next week",
    }

    result = CalendarOverviewSchema.model_validate(payload)

    assert result.period == "week"

@pytest.mark.unit
def test_invalid_calendar_overview_period():
    payload = {
        "period": "year",
    }

    with pytest.raises(ValidationError):
        CalendarOverviewSchema.model_validate(payload)


# --------------------------------------------------
# AVAILABILITY SCHEMA
# --------------------------------------------------
@pytest.mark.unit
def test_valid_availability():
    payload = {
        "start": "2026-11-10T10:00:00+05:30",
        "end": "2026-11-10T11:00:00+05:30",
    }

    result = AvailabilitySchema.model_validate(payload)

    assert result.start is not None


# --------------------------------------------------
# AVAILABLE SLOTS SCHEMA
# --------------------------------------------------
@pytest.mark.unit
def test_valid_available_slots():
    payload = {
        "start": "2026-11-10T09:00:00+05:30",
        "end": "2026-11-10T18:00:00+05:30",
        "duration_minutes": 60,
    }

    result = AvailableSlotsSchema.model_validate(payload)

    assert result.duration_minutes == 60

@pytest.mark.unit
def test_available_slots_duration_above_limit():
    payload = {
        "start": "2026-11-10T09:00:00+05:30",
        "end": "2026-11-10T18:00:00+05:30",
        "duration_minutes": 1441,
    }

    with pytest.raises(ValidationError):
        AvailableSlotsSchema.model_validate(payload)

@pytest.mark.unit
def test_available_slots_zero_duration():
    payload = {
        "start": "2026-11-10T09:00:00+05:30",
        "end": "2026-11-10T18:00:00+05:30",
        "duration_minutes": 0,
    }

    with pytest.raises(ValidationError):
        AvailableSlotsSchema.model_validate(payload)
