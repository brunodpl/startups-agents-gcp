"""Unit tests for the pipeline helpers + wiring (F3).

Run: ``uv run python -m pytest tests/test_pipeline.py -q``
"""

from agents.pipeline import build_pipeline, parse_shortlist


def test_parse_shortlist_plain_json() -> None:
    raw = '{"thesis": {"sector": "AI"}, "candidates": [{"name": "X"}]}'
    thesis, candidates = parse_shortlist(raw)
    assert thesis == {"sector": "AI"}
    assert candidates == [{"name": "X"}]


def test_parse_shortlist_code_fenced() -> None:
    raw = '```json\n{"thesis": {"sector": "AI"}, "candidates": []}\n```'
    thesis, candidates = parse_shortlist(raw)
    assert thesis == {"sector": "AI"}
    assert candidates == []


def test_parse_shortlist_with_prose_fallback() -> None:
    raw = 'Aquí tienes la shortlist:\n{"candidates": [{"name": "Y"}]}\nFin.'
    thesis, candidates = parse_shortlist(raw)
    assert thesis is None
    assert candidates == [{"name": "Y"}]


def test_parse_shortlist_already_dict() -> None:
    raw = {"thesis": {"sector": "AI"}, "candidates": [{"name": "Z"}]}
    thesis, candidates = parse_shortlist(raw)
    assert candidates == [{"name": "Z"}]


def test_parse_shortlist_garbage_returns_empty() -> None:
    thesis, candidates = parse_shortlist("no json here at all")
    assert thesis is None
    assert candidates == []


def test_parse_shortlist_none() -> None:
    assert parse_shortlist(None) == (None, [])


def test_pipeline_structure() -> None:
    root = build_pipeline()
    sub = {a.name for a in root.sub_agents}
    assert "discovery_agent" in sub
    assert "per_candidate_analysis" in sub

    per = next(a for a in root.sub_agents if a.name == "per_candidate_analysis")
    # Analysis must be research FIRST, then the parallel analysts.
    analysis = per.analysis_agent
    assert analysis.sub_agents[0].name == "startup_research_agent"
    assert analysis.sub_agents[1].name == "dimension_analysts"
    assert {a.name for a in analysis.sub_agents[1].sub_agents} == {
        "business_model_agent",
        "metrics_agent",
        "market_agent",
    }
