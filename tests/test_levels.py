"""Offline tests for the eval level logic (F5). No network.

Run: ``uv run python -m pytest tests/test_levels.py -q``
"""

from evals.levels import (
    RunCapture,
    level1_step,
    level2_trajectory,
    level3_tools,
    level4_final,
)


def _good_capture() -> RunCapture:
    return RunCapture(
        thesis="t",
        authors=[
            "discovery_agent",
            "startup_research_agent",
            "business_model_agent",
            "metrics_agent",
            "market_agent",
            "synthesizer_agent",
            "reporting_agent",
        ],
        tool_calls=[
            {"name": "find_candidates", "args": {"sector": "ai"}},
            {"name": "fetch_url", "args": {"url": "https://example.com/about"}},
        ],
        state={
            "shortlist": '{"candidates": [{"name": "X"}]}',
            "analyses": [
                {
                    "candidate": {"name": "X", "website": "https://example.com"},
                    "research": "r",
                    "business": "b",
                    "metrics": "m",
                    "market": "mk",
                    "diagnosis": "d",
                }
            ],
            "report": "Veredicto. según el Marco de evaluación de startups y el Marco Lean & Growth.",
        },
    )


def _all_true_judge(report, criteria):
    return {c: True for c in criteria}


def test_all_levels_pass_on_good_capture() -> None:
    cap = _good_capture()
    assert level1_step(cap).passed
    assert level2_trajectory(cap).passed
    assert level3_tools(cap).passed
    assert level4_final(cap, ["x", "y"], _all_true_judge).passed


def test_level1_fails_on_empty_stage() -> None:
    cap = _good_capture()
    cap.state["analyses"][0]["diagnosis"] = ""
    assert not level1_step(cap).passed


def test_level2_fails_when_synth_before_research() -> None:
    cap = _good_capture()
    cap.authors = [
        "discovery_agent",
        "synthesizer_agent",
        "startup_research_agent",
        "reporting_agent",
    ]
    assert not level2_trajectory(cap).passed


def test_level3_fails_when_fetch_url_not_from_state() -> None:
    cap = _good_capture()
    cap.tool_calls[1]["args"]["url"] = "https://unrelated-hardcoded.com"
    assert not level3_tools(cap).passed


def test_level3_fails_without_find_candidates() -> None:
    cap = _good_capture()
    cap.tool_calls = [t for t in cap.tool_calls if t["name"] != "find_candidates"]
    assert not level3_tools(cap).passed


def test_level4_fails_below_threshold() -> None:
    cap = _good_capture()

    def half_judge(report, criteria):
        return {c: (i % 2 == 0) for i, c in enumerate(criteria)}

    res = level4_final(cap, ["a", "b", "c", "d"], half_judge, coverage_threshold=0.7)
    assert not res.passed


def test_level4_fails_without_framework_citation() -> None:
    cap = _good_capture()
    cap.state["report"] = "Veredicto sin citar ningún framework."
    assert not level4_final(cap, ["a"], _all_true_judge).passed
