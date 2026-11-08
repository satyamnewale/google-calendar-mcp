from datetime import datetime

from auth.google_auth import get_calendar_service

from config.settings import (
    CALENDAR_ID,
    DEFAULT_MAX_RESULTS,
    MAX_RESULTS_LIMIT,
)

from errors.exceptions import (
    CalendarConcurrencyError,
    CalendarResultLimitExceededError,
)


def list_calendars():
    service = get_calendar_service()

    response = service.calendarList().list(
        maxResults=100
    ).execute()

    return response.get("items", [])


def get_event_by_id(event_id: str, calendar_id=CALENDAR_ID):
    service = get_calendar_service()

    return service.events().get(
        calendarId=calendar_id,
        eventId=event_id
    ).execute()


def list_events_in_range(
    start_date: datetime,
    end_date: datetime,
    calendar_id=CALENDAR_ID,
    max_results=DEFAULT_MAX_RESULTS,
    include_cancelled=False,
):
    """
    Retrieve events with pagination.

    If the result set exceeds max_results, raise an explicit
    error instead of silently returning incomplete results.
    """

    if not isinstance(start_date, datetime):
        raise ValueError(
            "start_date must be a datetime."
        )

    if not isinstance(end_date, datetime):
        raise ValueError(
            "end_date must be a datetime."
        )

    if start_date.tzinfo is None or end_date.tzinfo is None:
        raise ValueError(
            "Start and end must be timezone-aware."
        )

    if start_date >= end_date:
        raise ValueError(
            "End date must be after start date."
        )

    if (
        not isinstance(max_results, int)
        or isinstance(max_results, bool)
        or not 1 <= max_results <= MAX_RESULTS_LIMIT
    ):
        raise ValueError(
            f"max_results must be between 1 and {MAX_RESULTS_LIMIT}."
        )

    service = get_calendar_service()

    events = []
    page_token = None

    while True:

        remaining = max_results - len(events)

        page_size = min(
            remaining,
            2500,
        )

        response = service.events().list(
            calendarId=calendar_id,
            timeMin=start_date.isoformat(),
            timeMax=end_date.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            showDeleted=include_cancelled,
            maxResults=page_size,
            pageToken=page_token,
        ).execute()

        events.extend(
            response.get("items", [])
        )

        next_page_token = response.get(
            "nextPageToken"
        )

        # More results exist, but the configured cap was reached.
        if next_page_token and len(events) >= max_results:

            raise CalendarResultLimitExceededError(
                f"More than {max_results} events match the requested "
                "range. Narrow the date range or increase the configured limit."
            )

        if not next_page_token:
            break

        page_token = next_page_token

    return events


def insert_calendar_event(
    event_body: dict,
    calendar_id=CALENDAR_ID,
):
    service = get_calendar_service()

    return service.events().insert(
        calendarId=calendar_id,
        body=event_body,
    ).execute()


def update_calendar_event(
    event_id: str,
    updates: dict,
    calendar_id=CALENDAR_ID,
    existing_event: dict | None = None,
):
    """
    Update an event using GET followed by conditional UPDATE.

    Uses the event ETag to prevent overwriting changes made
    by another client after the GET operation.
    """

    service = get_calendar_service()

    if existing_event is None:

        existing_event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id,
        ).execute()

    etag = existing_event.get("etag")

    if not etag:
        raise CalendarConcurrencyError(
            "Cannot safely update this event because its ETag is missing. "
            "Retrieve the event again before updating."
        )

    updated_event = existing_event.copy()
    updated_event.update(updates)

    request = service.events().update(
        calendarId=calendar_id,
        eventId=event_id,
        body=updated_event,
    )

    request.headers["If-Match"] = etag

    return request.execute()


def delete_calendar_event(
    event_id: str,
    calendar_id=CALENDAR_ID,
    existing_event: dict | None = None,
):
    """
    Delete an event only if it has not changed since retrieval.
    """

    service = get_calendar_service()

    if existing_event is None:

        existing_event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id,
        ).execute()

    etag = existing_event.get("etag")

    if not etag:
        raise CalendarConcurrencyError(
            "Cannot safely delete this event because its ETag is missing. "
            "Retrieve the event again before deletion."
        )

    request = service.events().delete(
        calendarId=calendar_id,
        eventId=event_id,
    )

    request.headers["If-Match"] = etag

    request.execute()

    return {
        "success": True,
        "event_id": event_id,
        "message": "Event deleted successfully.",
    }
