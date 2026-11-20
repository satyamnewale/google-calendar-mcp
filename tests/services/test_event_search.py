
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from services import event_search


@pytest.fixture
def event_range():
    return (
        datetime.fromisoformat("2026-11-10T00:00:00+05:30"),
        datetime.fromisoformat("2026-11-11T00:00:00+05:30"),
    )


@pytest.mark.asyncio
@pytest.mark.services
async def test_search_events_returns_all_events(monkeypatch, event_range):
    events = [
        {"id": "1", "summary": "Team Meeting"},
        {"id": "2", "summary": "Project Review"},
    ]
    list_events = AsyncMock(return_value=events)
    monkeypatch.setattr(event_search, "list_events_in_range", list_events)

    result = await event_search.search_events(*event_range)

    assert result == events
    list_events.assert_awaited_once_with(*event_range)


@pytest.mark.asyncio
@pytest.mark.services
async def test_search_events_filters_by_title(monkeypatch, event_range):
    events = [
        {"id": "1", "summary": "Team Meeting"},
        {"id": "2", "summary": "Project Review"},
        {"id": "3", "summary": "TEAM Planning"},
    ]
    monkeypatch.setattr(
        event_search,
        "list_events_in_range",
        AsyncMock(return_value=events),
    )

    result = await event_search.search_events(
        *event_range,
        title=" team ",
    )

    assert [event["id"] for event in result] == ["1", "3"]


@pytest.mark.asyncio
@pytest.mark.services
async def test_search_events_empty_title_returns_all(monkeypatch, event_range):
    events = [{"id": "1", "summary": "Meeting"}]
    monkeypatch.setattr(
        event_search,
        "list_events_in_range",
        AsyncMock(return_value=events),
    )

    assert await event_search.search_events(
        *event_range,
        title="   ",
    ) == events


@pytest.mark.asyncio
@pytest.mark.services
async def test_find_similar_events(monkeypatch, event_range):
    events = [
        {"id": "1", "summary": "Team Meeting"},
        {"id": "2", "summary": "Team Meet"},
        {"id": "3", "summary": "Dentist"},
    ]
    monkeypatch.setattr(
        event_search,
        "list_events_in_range",
        AsyncMock(return_value=events),
    )

    result = await event_search.find_similar_events(
        "Team Meeting",
        *event_range,
        threshold=0.7,
    )

    assert result
    assert result[0]["event"]["id"] == "1"
    assert result[0]["similarity"] == 1.0


@pytest.mark.asyncio
@pytest.mark.services
async def test_find_similar_events_rejects_empty_title(event_range):
    with pytest.raises(ValueError, match="cannot be empty"):
        await event_search.find_similar_events(
            "   ",
            *event_range,
        )


@pytest.mark.asyncio
@pytest.mark.services
async def test_find_similar_events_rejects_invalid_threshold(event_range):
    with pytest.raises(ValueError, match="threshold"):
        await event_search.find_similar_events(
            "Meeting",
            *event_range,
            threshold=1.5,
        )
