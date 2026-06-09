"""Unit tests for the GitHub source + multi-source dedupe (F4).

Deterministic: GitHub HTTP and the YC tool are monkeypatched.

Run: ``uv run python -m pytest tests/test_sources.py -q``
"""

import httpx

from agents.tools import sources
from agents.tools.gh_source import normalize_repo, search_github_projects


def test_normalize_repo_prefers_homepage() -> None:
    raw = {
        "name": "langflow",
        "homepage": "https://langflow.org",
        "html_url": "https://github.com/x/langflow",
        "description": "Low-code app builder for RAG.",
        "topics": ["llm", "rag"],
    }
    out = normalize_repo(raw)
    assert out["name"] == "langflow"
    assert out["website"] == "https://langflow.org"
    assert out["one_liner"] == "Low-code app builder for RAG."
    assert out["industries"] == ["llm", "rag"]
    assert out["source"] == "github"


def test_normalize_repo_falls_back_to_html_url() -> None:
    out = normalize_repo({"name": "x", "html_url": "https://github.com/a/x"})
    assert out["website"] == "https://github.com/a/x"
    assert out["one_liner"] == ""


def test_search_github_projects_empty_on_error(monkeypatch) -> None:
    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "get", boom)
    assert search_github_projects("anything") == []


def test_dedupe_by_domain_keeps_first() -> None:
    cands = [
        {"name": "A", "website": "https://www.example.com/", "source": "yc"},
        {"name": "A-dup", "website": "http://example.com", "source": "github"},
        {"name": "B", "website": "https://other.com", "source": "github"},
        {"name": "NoSite", "website": "", "source": "github"},
    ]
    out = sources.dedupe_by_domain(cands)
    names = [c["name"] for c in out]
    assert names == ["A", "B", "NoSite"]  # A-dup dropped, blank kept


def test_find_candidates_merges_and_dedupes(monkeypatch) -> None:
    monkeypatch.setattr(sources, "search_grounded", lambda *a, **k: [])
    monkeypatch.setattr(
        sources,
        "search_startups",
        lambda *a, **k: [
            {"name": "Shared", "website": "https://shared.com"},
            {"name": "YCOnly", "website": "https://yc-only.com"},
        ],
    )
    monkeypatch.setattr(
        sources,
        "search_github_projects",
        lambda *a, **k: [
            {"name": "SharedGH", "website": "https://www.shared.com", "source": "github"},
            {"name": "GHOnly", "website": "https://gh-only.com", "source": "github"},
        ],
    )
    out = sources.find_candidates("ai", limit=10)
    names = [c["name"] for c in out]
    # YC entries tagged, GitHub duplicate of shared.com dropped.
    assert "Shared" in names and "SharedGH" not in names
    assert {"YCOnly", "GHOnly"} <= set(names)
    yc_entry = next(c for c in out if c["name"] == "Shared")
    assert yc_entry["source"] == "yc"


def test_find_candidates_grounded_wins_and_geo_ranks(monkeypatch) -> None:
    monkeypatch.setattr(
        sources,
        "search_grounded",
        lambda *a, **k: [
            {"name": "GroundedShared", "website": "https://shared.com",
             "regions": ["Galicia"], "source": "grounded"},
            {"name": "GroundedGalicia", "website": "https://g2.com",
             "regions": ["Galicia, Spain"], "source": "grounded"},
        ],
    )
    monkeypatch.setattr(
        sources,
        "search_startups",
        lambda *a, **k: [
            {"name": "YCShared", "website": "https://www.shared.com"},
            {"name": "YCGlobal", "website": "https://yc-global.com",
             "regions": ["United States"]},
        ],
    )
    monkeypatch.setattr(
        sources,
        "search_github_projects",
        lambda *a, **k: [
            {"name": "GHGlobal", "website": "https://gh.com", "source": "github"},
        ],
    )
    out = sources.find_candidates("ai", region="Galicia", limit=10)
    names = [c["name"] for c in out]
    # Grounded wins the shared.com domain conflict over YC.
    assert "GroundedShared" in names and "YCShared" not in names
    # Region-matched candidates rank ahead of global ones.
    galicia = [n for n in names if n in {"GroundedShared", "GroundedGalicia"}]
    globals_ = [n for n in names if n in {"YCGlobal", "GHGlobal"}]
    assert names.index(galicia[-1]) < names.index(globals_[0])
