"""The 4 eval levels (F5).

Each level is a pure function over a ``RunCapture`` (one pipeline run), so the
logic is testable offline. The Level-4 LLM judge is injected as a callable so
this module never touches the network.

  1. Step       — every stage produced non-empty output, no errors.
  2. Trajectory — discovery -> research -> analysts -> synthesizer -> reporting.
  3. Tool calls — find_candidates was called, and fetch_url's URL came from a
                  discovered candidate in state (not hardcoded).
  4. Final      — the report cites real frameworks and covers the dataset's
                  expected criteria (LLM-as-judge).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from agents.tools.sources import _domain

# Authors expected in the trajectory.
DISCOVERY = "discovery_agent"
RESEARCH = "startup_research_agent"
ANALYSTS = ("business_model_agent", "metrics_agent", "market_agent")
SYNTH = "synthesizer_agent"
REPORTING = "reporting_agent"

# Framework names a grounded report must cite (must exist in knowledge/).
FRAMEWORK_NAMES = ("Marco de evaluación de startups", "Marco Lean & Growth")


@dataclass
class RunCapture:
    """Everything one pipeline run produced, for the levels to inspect."""

    thesis: str
    authors: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)  # {"name", "args"}
    state: dict = field(default_factory=dict)
    error_events: list[str] = field(default_factory=list)


@dataclass
class LevelResult:
    name: str
    passed: bool
    details: list[str] = field(default_factory=list)


def _first_index(seq: list[str], value: str) -> int:
    return seq.index(value) if value in seq else -1


def level1_step(run: RunCapture) -> LevelResult:
    d: list[str] = []
    ok = True

    if run.error_events:
        ok = False
        d.append(f"error events: {run.error_events[:2]}")

    if not run.state.get("shortlist"):
        ok = False
        d.append("shortlist missing/empty")

    analyses = run.state.get("analyses") or []
    if not analyses:
        ok = False
        d.append("analyses missing/empty")
    for i, a in enumerate(analyses):
        for key in ("research", "business", "metrics", "market", "diagnosis"):
            if not (a.get(key) or "").strip():
                ok = False
                d.append(f"analyses[{i}].{key} empty")

    if not (run.state.get("report") or "").strip():
        ok = False
        d.append("report missing/empty")

    if ok:
        d.append(f"{len(analyses)} candidate(s) fully analysed; report present")
    return LevelResult("1-step", ok, d)


def level2_trajectory(run: RunCapture) -> LevelResult:
    d: list[str] = []
    a = run.authors
    i_disc = _first_index(a, DISCOVERY)
    i_res = _first_index(a, RESEARCH)
    i_syn = _first_index(a, SYNTH)
    i_rep = _first_index(a, REPORTING)

    ok = True
    for name, idx in [
        (DISCOVERY, i_disc),
        (RESEARCH, i_res),
        (SYNTH, i_syn),
        (REPORTING, i_rep),
    ]:
        if idx < 0:
            ok = False
            d.append(f"{name} never ran")

    if ok and not (i_disc < i_res < i_syn < i_rep):
        ok = False
        d.append(f"order wrong: disc={i_disc} res={i_res} syn={i_syn} rep={i_rep}")

    # Analysts must run after research and before synthesis.
    for an in ANALYSTS:
        idx = _first_index(a, an)
        if idx < 0:
            ok = False
            d.append(f"{an} never ran")
        elif not (i_res < idx < i_syn):
            ok = False
            d.append(f"{an} out of order ({idx})")

    if ok:
        d.append("discovery -> research -> analysts -> synthesizer -> reporting")
    return LevelResult("2-trajectory", ok, d)


def _candidate_domains(run: RunCapture) -> set[str]:
    domains = set()
    for a in run.state.get("analyses") or []:
        site = (a.get("candidate") or {}).get("website", "")
        if _domain(site):
            domains.add(_domain(site))
    return domains


def level3_tools(run: RunCapture) -> LevelResult:
    d: list[str] = []
    ok = True
    names = [t["name"] for t in run.tool_calls]

    if "find_candidates" not in names:
        ok = False
        d.append("find_candidates was not called")
    else:
        fc = next(t for t in run.tool_calls if t["name"] == "find_candidates")
        if not (fc["args"] or {}).get("sector"):
            ok = False
            d.append("find_candidates called without a sector")

    fetches = [t for t in run.tool_calls if t["name"] == "fetch_url"]
    if not fetches:
        ok = False
        d.append("fetch_url was not called")
    else:
        cand_domains = _candidate_domains(run)
        for t in fetches:
            url = (t["args"] or {}).get("url", "")
            if _domain(url) not in cand_domains:
                ok = False
                d.append(f"fetch_url url {url!r} not from a discovered candidate")
        if ok:
            d.append(f"{len(fetches)} fetch_url call(s), all from state candidates")

    return LevelResult("3-tools", ok, d)


def level4_final(
    run: RunCapture,
    expected_criteria: list[str],
    judge: Callable[[str, list[str]], dict[str, bool]],
    coverage_threshold: float = 0.7,
) -> LevelResult:
    d: list[str] = []
    report = run.state.get("report") or ""
    ok = True

    cited = [fw for fw in FRAMEWORK_NAMES if fw in report]
    if not cited:
        ok = False
        d.append("report cites no known framework by name")
    else:
        d.append(f"cites: {', '.join(cited)}")

    verdicts = judge(report, expected_criteria)
    covered = sum(1 for v in verdicts.values() if v)
    total = len(expected_criteria) or 1
    ratio = covered / total
    d.append(f"criteria covered: {covered}/{total} ({ratio:.0%})")
    for crit, v in verdicts.items():
        if not v:
            d.append(f"  missing: {crit}")
    if ratio < coverage_threshold:
        ok = False

    return LevelResult("4-final", ok, d)
