"""Unit tests for the pydantic schemas (F2).

Run: ``uv run python -m pytest tests/test_schemas.py -q``
"""

from agents.schemas import Candidate, Shortlist, Thesis


def test_thesis_minimal() -> None:
    t = Thesis(
        sector="AI dev tools", stage="early", geography="global", signals=["tracción"]
    )
    assert t.sector == "AI dev tools"
    assert t.signals == ["tracción"]


def test_candidate_from_yc() -> None:
    c = Candidate(name="X", website="https://x.com", one_liner="y", source="yc")
    assert c.score is None  # score se rellena en Discovery
    assert c.industries == []  # defaults vacíos, no None
    assert c.regions == []


def test_candidate_scored() -> None:
    c = Candidate(
        name="X",
        website="https://x.com",
        one_liner="y",
        source="yc",
        score=0.8,
        rationale="encaja con la tesis",
    )
    assert c.score == 0.8
    assert c.rationale == "encaja con la tesis"


def test_shortlist_holds_thesis_and_candidates() -> None:
    t = Thesis(sector="AI", stage="early", geography="EU", signals=[])
    c = Candidate(name="X", website="https://x.com", one_liner="y", source="yc")
    sl = Shortlist(thesis=t, candidates=[c])
    assert sl.thesis.sector == "AI"
    assert len(sl.candidates) == 1
