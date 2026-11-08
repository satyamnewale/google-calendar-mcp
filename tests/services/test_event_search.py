from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from services import event_search

TZ = ZoneInfo("Asia/Kolkata")


def dt(day=10, hour=0):
    return datetime(2026, 11, day, hour, 0, tzinfo=TZ)


@pytest.fixture
def sample_events():
    return [
        {"id": "event_001", "summary": "Team Meeting", "status": "confirmed"},
        {"id": "event_002", "summary": "Project Discussion", "status": "confirmed"},
        {"id": "event_003", "summary": "Client Meeting", "status": "confirmed"},
    ]


def test_search_events_without_title_returns_all(monkeypatch, sample_events):
    monkeypatch.setattr(event_search, "list_events_in_range", lambda start, end: sample_events)

    result = event_search.search_events(dt(), dt(11))

    assert result == sample_events


@pytest.mark.parametrize(
    ("title", "expected_ids"),
    [
        ("Team Meeting", ["event_001"]),
        ("Meeting", ["event_001", "event_003"]),
        ("team meeting", ["event_001"]),
        ("  PROJECT  ", ["event_002"]),
    ],
)
def test_search_events_filters_title_case_insensitively(
    monkeypatch, sample_events, title, expected_ids
):
    monkeypatch.setattr(event_search, "list_events_in_range", lambda start, end: sample_events)

    result = event_search.search_events(dt(), dt(11), title=title)

    assert [event["id"] for event in result] == expected_ids


def test_search_events_with_blank_title_returns_all(monkeypatch, sample_events):
    monkeypatch.setattr(event_search, "list_events_in_range", lambda start, end: sample_events)

    assert event_search.search_events(dt(), dt(11), title="   ") == sample_events


def test_search_events_returns_empty_when_no_title_matches(monkeypatch, sample_events):
    monkeypatch.setattr(event_search, "list_events_in_range", lambda start, end: sample_events)

    assert event_search.search_events(dt(), dt(11), title="missing") == []


def test_search_events_rejects_invalid_range(monkeypatch):
    def list_events(start, end):
        if start >= end:
            raise ValueError("End date must be after start date.")
        return []

    monkeypatch.setattr(event_search, "list_events_in_range", list_events)

    with pytest.raises(ValueError):
        event_search.search_events(dt(11), dt())


def test_get_event_for_day_uses_day_range(monkeypatch):
    expected = [{"id": "event_001"}]
    captured = {}
    monkeypatch.setattr(
        event_search, "get_day_range",
        lambda day: (dt(), dt(11)),
    )
    monkeypatch.setattr(
        event_search, "search_events",
        lambda start, end: captured.setdefault("range", (start, end)) or expected,
    )
    # Use a simple explicit stub to preserve the expected return value.
    def search(start, end):
        captured["range"] = (start, end)
        return expected
    monkeypatch.setattr(event_search, "search_events", search)

    assert event_search.get_event_for_day("2026-11-10") == expected
    assert captured["range"] == (dt(), dt(11))


def test_get_event_for_week_delegates_to_search(monkeypatch):
    expected = [{"id": "event_001"}]
    monkeypatch.setattr(event_search, "get_week_range", lambda week: (dt(), dt(11)))
    monkeypatch.setattr(event_search, "search_events", lambda start, end: expected)

    assert event_search.get_event_for_week("2026-11-10") == expected


def test_get_event_for_month_delegates_to_search(monkeypatch):
    expected = [{"id": "event_001"}]
    monkeypatch.setattr(event_search, "get_month_range", lambda month: (dt(), dt(11)))
    monkeypatch.setattr(event_search, "search_events", lambda start, end: expected)

    assert event_search.get_event_for_month("2026-11") == expected


def test_find_similar_events_returns_event_and_similarity(monkeypatch, sample_events):
    monkeypatch.setattr(event_search, "list_events_in_range", lambda start, end: sample_events)

    result = event_search.find_similar_events("Team Meeting", dt(), dt(11))

    assert result
    assert result[0]["event"]["id"] == "event_001"
    assert result[0]["similarity"] == 1.0


def test_find_similar_events_sorts_by_similarity(monkeypatch):
    events = [
        {"id": "a", "summary": "Team Meet"},
        {"id": "b", "summary": "Team Meeting"},
        {"id": "c", "summary": "Completely different"},
    ]
    monkeypatch.setattr(event_search, "list_events_in_range", lambda start, end: events)

    result = event_search.find_similar_events("Team Meeting", dt(), dt(11), threshold=0.3)

    scores = [item["similarity"] for item in result]
    assert scores == sorted(scores, reverse=True)
    assert result[0]["event"]["id"] == "b"


def test_find_similar_events_returns_empty_for_no_matches(monkeypatch):
    monkeypatch.setattr(
        event_search, "list_events_in_range",
        lambda start, end: [{"id": "x", "summary": "Unrelated"}],
    )

    assert event_search.find_similar_events("Team Meeting", dt(), dt(11), threshold=0.99) == []


def test_find_similar_events_rejects_blank_title():
    with pytest.raises(ValueError, match="Search title cannot be empty"):
        event_search.find_similar_events("  ", dt(), dt(11))


@pytest.mark.parametrize("threshold", [-0.1, 1.1])
def test_find_similar_events_rejects_invalid_threshold(threshold):
    with pytest.raises(ValueError, match="Similarity threshold"):
        event_search.find_similar_events("Meeting", dt(), dt(11), threshold=threshold)
