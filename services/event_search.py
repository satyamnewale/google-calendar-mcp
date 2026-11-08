
from difflib import SequenceMatcher

from services.calendar_service import list_events_in_range

from utils.datetime_utils import (
    get_day_range,
    get_week_range,
    get_month_range,
    parse_datetime,
)
from utils.validators import validate_time_range

from config.settings import SIMILARITY_THRESHOLD


def search_events(
    start_date,
    end_date,
    title: str | None = None,
):
    """Search events within a date range, optionally filtering by title."""
    validate_time_range(start_date, end_date)

    events = list_events_in_range(start_date, end_date)

    if title is None or not title.strip():
        return events

    query = title.strip().casefold()

    return [
        event
        for event in events
        if query in event.get("summary", "").casefold()
    ]

def get_event_for_day(day: str):
    start, end = get_day_range(day)
    return search_events(start, end)


def get_event_for_week(week: str | None = None):
    start, end = get_week_range(week)
    return search_events(start, end)


def get_event_for_month(month: str | None = None):
    start, end = get_month_range(month)
    return search_events(start, end)


def find_similar_events(
    title: str,
    start_date,
    end_date,
    threshold: float = SIMILARITY_THRESHOLD,
):
    if not title or not title.strip():
        raise ValueError("Search title cannot be empty.")

    if not 0 <= threshold <= 1:
        raise ValueError("Similarity threshold must be between 0 and 1.")

    validate_time_range(start_date, end_date)
    events = list_events_in_range(start_date, end_date)

    query = title.casefold().strip()
    matches = []

    for event in events:
        event_title = event.get("summary", "")

        if not event_title:
            continue

        score = SequenceMatcher(
            None,
            query,
            event_title.casefold()
        ).ratio()

        if score >= threshold:
            matches.append({
                "event": event,
                "similarity": round(score, 3),
            })

    return sorted(
        matches,
        key=lambda item: item["similarity"],
        reverse=True,
    )
