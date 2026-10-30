
from auth.google_auth import get_calendar_service
from config.settings import CALENDAR_ID, DEFAULT_MAX_RESULTS


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
    start_date,
    end_date,
    calendar_id=CALENDAR_ID,
    max_results=DEFAULT_MAX_RESULTS,
    include_cancelled=False,
):
    if start_date >= end_date:
        raise ValueError("End date must be after start date.")

    if max_results < 1:
        raise ValueError("max_results must be at least 1.")

    if start_date.tzinfo is None or end_date.tzinfo is None:
        raise ValueError("Start and end must be timezone-aware.")

    service = get_calendar_service()

    events = []
    page_token = None

    while True:
        page_size = min(max_results - len(events), 2500)

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

        events.extend(response.get("items", []))

        if len(events) >= max_results:
            break

        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return events[:max_results]


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
    Update an event using GET followed by UPDATE.

    No PATCH request is used.

    If existing_event is supplied, it avoids another GET.
    """

    service = get_calendar_service()

    # 1. Retrieve the existing event
    if existing_event is None:
        existing_event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id,
        ).execute()

    # 2. Preserve existing fields and apply changes
    updated_event = existing_event.copy()
    updated_event.update(updates)

    # 3. Send full event resource using UPDATE
    return service.events().update(
        calendarId=calendar_id,
        eventId=event_id,
        body=updated_event,
    ).execute()


def delete_calendar_event(
    event_id: str,
    calendar_id=CALENDAR_ID,
):
    service = get_calendar_service()

    service.events().delete(
        calendarId=calendar_id,
        eventId=event_id,
    ).execute()

    return {
        "success": True,
        "event_id": event_id,
        "message": "Event deleted successfully.",
    }
