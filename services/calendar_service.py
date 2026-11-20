from datetime import datetime
import asyncio

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

async def _execute(request):
    return await asyncio.to_thread(request.execute)

async def list_calendars():
    service = await asyncio.to_thread(get_calendar_service)

    response = await _execute(
        service.calendarList().list(maxResults=100)
    )

    return response.get("items", [])


async def get_event_by_id(
    event_id: str,
    calendar_id=CALENDAR_ID,
):
    service = await asyncio.to_thread(get_calendar_service)

    request = service.events().get(
        calendarId=calendar_id,
        eventId=event_id,
    )

    return await _execute(request)


async def list_events_in_range(
    start_date: datetime,
    end_date: datetime,
    calendar_id=CALENDAR_ID,
    max_results=DEFAULT_MAX_RESULTS,
    include_cancelled=False,
):
    if not isinstance(start_date, datetime):
        raise ValueError("start_date must be a datetime.")

    if not isinstance(end_date, datetime):
        raise ValueError("end_date must be a datetime.")

    if start_date.tzinfo is None or end_date.tzinfo is None:
        raise ValueError("Start and end must be timezone-aware.")

    if start_date >= end_date:
        raise ValueError("End date must be after start date.")

    if (
        not isinstance(max_results, int)
        or isinstance(max_results, bool)
        or not 1 <= max_results <= MAX_RESULTS_LIMIT
    ):
        raise ValueError(
            f"max_results must be between 1 and {MAX_RESULTS_LIMIT}."
        )

    service = await asyncio.to_thread(get_calendar_service)

    events = []
    page_token = None

    while True:
        remaining = max_results - len(events)
        page_size = min(remaining, 2500)

        request = service.events().list(
            calendarId=calendar_id,
            timeMin=start_date.isoformat(),
            timeMax=end_date.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            showDeleted=include_cancelled,
            maxResults=page_size,
            pageToken=page_token,
        )

        response = await _execute(request)

        events.extend(response.get("items", []))

        next_page_token = response.get("nextPageToken")

        if next_page_token and len(events) >= max_results:
            raise CalendarResultLimitExceededError(
                f"More than {max_results} events match the requested "
                "range. Narrow the date range or increase the configured limit."
            )

        if not next_page_token:
            break

        page_token = next_page_token

    return events


async def insert_calendar_event(
    event_body: dict,
    calendar_id=CALENDAR_ID,
):
    service = await asyncio.to_thread(get_calendar_service)

    request = service.events().insert(
        calendarId=calendar_id,
        body=event_body,
    )

    return await _execute(request)

async def update_calendar_event(
    event_id: str,
    updates: dict,
    calendar_id=CALENDAR_ID,
    existing_event: dict | None = None,
):
    if existing_event is None:
        existing_event = await get_event_by_id(
            event_id,
            calendar_id,
        )

    etag = existing_event.get("etag")

    if not etag:
        raise CalendarConcurrencyError(
            "Cannot safely update this event because its ETag is missing."
        )

    updated_event = existing_event.copy()
    updated_event.update(updates)

    service = await asyncio.to_thread(get_calendar_service)

    request = service.events().update(
        calendarId=calendar_id,
        eventId=event_id,
        body=updated_event,
    )

    request.headers["If-Match"] = etag

    return await _execute(request)


async def delete_calendar_event(
    event_id: str,
    calendar_id=CALENDAR_ID,
    existing_event: dict | None = None,
):
    if existing_event is None:
        existing_event = await get_event_by_id(
            event_id,
            calendar_id,
        )

    etag = existing_event.get("etag")

    if not etag:
        raise CalendarConcurrencyError(
            "Cannot safely delete this event because its ETag is missing."
        )

    service = await asyncio.to_thread(get_calendar_service)

    request = service.events().delete(
        calendarId=calendar_id,
        eventId=event_id,
    )

    request.headers["If-Match"] = etag

    await _execute(request)

    return {
        "success": True,
        "event_id": event_id,
        "message": "Event deleted successfully.",
    }