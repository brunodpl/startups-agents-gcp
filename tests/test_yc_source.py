"""Unit tests for the YC OSS source tool (F2).

Deterministic: ``normalize_company`` runs offline, and ``search_startups`` is
tested with ``httpx.get`` monkeypatched so no real network call happens.

Run: ``uv run python -m pytest tests/test_yc_source.py -q``
"""

import httpx

from agents.tools.yc_source import (
    _candidate_slugs,
    normalize_company,
    search_startups,
)


def test_candidate_slugs_prefers_full_then_bigrams_then_words() -> None:
    slugs = _candidate_slugs("AI developer tools")
    assert slugs[0] == "ai-developer-tools"  # full phrase first
    assert "developer-tools" in slugs  # bigram (a real YC tag)
    assert "developer" in slugs and "tools" in slugs  # single words last


def test_candidate_slugs_skips_short_stopwords() -> None:
    # 'para' (4 chars) stays, but 'de' (2) would be dropped.
    slugs = _candidate_slugs("inteligencia artificial para developer tools")
    assert "developer-tools" in slugs

# Mirrors the real YC OSS company shape (snake_case fields).
RAW = {
    "name": "Directed Edge",
    "website": "http://directededge.com",
    "one_liner": "Product recommendations.",
    "industries": ["Consumer", "Home and Personal"],
    "regions": ["United States of America", "America / Canada"],
    "stage": "Early",
    "batch": "Summer 2009",
    "status": "Active",
    "tags": ["AI"],
}


def test_normalize_company_maps_fields() -> None:
    out = normalize_company(RAW)
    assert out["name"] == "Directed Edge"
    assert out["website"] == "http://directededge.com"
    assert out["one_liner"] == "Product recommendations."
    assert out["industries"] == ["Consumer", "Home and Personal"]
    assert out["regions"] == ["United States of America", "America / Canada"]
    assert out["stage"] == "Early"
    assert out["batch"] == "Summer 2009"


def test_normalize_company_handles_missing_fields() -> None:
    out = normalize_company({"name": "X"})
    assert out["name"] == "X"
    assert out["website"] == ""
    assert out["one_liner"] == ""
    assert out["industries"] == []
    assert out["regions"] == []
    assert out["stage"] is None
    assert out["batch"] is None


def _payload() -> list[dict]:
    return [
        {"name": "A", "website": "https://a.com", "one_liner": "a",
         "industries": ["AI"], "regions": ["United States of America"],
         "stage": "Early", "batch": "W20", "tags": ["AI"]},
        {"name": "B", "website": "https://b.com", "one_liner": "b",
         "industries": ["AI"], "regions": ["Europe"],
         "stage": "Early", "batch": "W21", "tags": ["AI"]},
        {"name": "C", "website": "https://c.com", "one_liner": "c",
         "industries": ["AI"], "regions": ["Europe", "Spain"],
         "stage": "Seed", "batch": "W22", "tags": ["AI"]},
    ]


def test_search_startups_filters_region_and_limit(monkeypatch) -> None:
    class FakeResp:
        status_code = 200

        def json(self):
            return _payload()

        def raise_for_status(self):
            pass

    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResp())
    out = search_startups("artificial-intelligence", region="Europe", limit=1)
    assert len(out) == 1
    assert out[0]["name"] == "B"  # first Europe match, limited to 1


def test_search_startups_returns_empty_on_error(monkeypatch) -> None:
    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "get", boom)
    assert search_startups("anything") == []
