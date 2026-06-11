"""Per-candidate state persistence (state_delta events) in PerCandidateAnalysis.

The custom loop mutates ``ctx.session.state`` directly, which the live
sub-agents see but persisted sessions (Agent Engine, ``SESSION_SERVICE_URI``)
do NOT — those are reconstructed from event ``state_delta``s. These tests run
the loop offline with stub sub-agents and assert every per-candidate write is
also recorded as a delta on some event:

* the candidate selection (``current_candidate``) per iteration,
* the guard's "Datos insuficientes" verdict when research fails,
* an ``analyses`` checkpoint after every candidate (mid-run crash keeps
  the candidates completed so far).

Run: ``uv run python -m pytest tests/test_pipeline_state.py -q``
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, SequentialAgent
from google.adk.events import Event, EventActions
from google.adk.runners import InMemoryRunner
from google.genai import types

from agents.pipeline import PerCandidateAnalysis


class StubWriter(BaseAgent):
    """Writes fixed key/values to state via a proper state_delta event."""

    payload: dict

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(state_delta=dict(self.payload)),
        )


SHORTLIST = {
    "thesis": {"sector": "AI", "stage": "seed", "geography": "EU", "signals": []},
    "candidates": [
        {"name": "Alpha", "website": "https://alpha.com", "one_liner": "a",
         "source": "yc"},
        {"name": "Beta", "website": "https://beta.com", "one_liner": "b",
         "source": "github"},
    ],
}


def _build(research_payload: dict) -> PerCandidateAnalysis:
    analysis = SequentialAgent(
        name="analysis",
        sub_agents=[
            StubWriter(name="research_stub", payload=research_payload),
            StubWriter(
                name="analysts_stub",
                payload={"business": "b", "metrics": "m", "market": "k"},
            ),
        ],
    )
    return PerCandidateAnalysis(
        name="per_candidate_analysis",
        analysis_agent=analysis,
        synthesizer=StubWriter(name="synth_stub", payload={"diagnosis": "ok"}),
        max_candidates=8,
    )


async def _run(agent: BaseAgent) -> tuple[list[dict], dict]:
    """Run the loop once; return (state_deltas seen on events, final state)."""
    runner = InMemoryRunner(agent=agent, app_name="t")
    session = await runner.session_service.create_session(
        app_name="t", user_id="u", state={"shortlist": SHORTLIST}
    )
    deltas: list[dict] = []
    msg = types.Content(role="user", parts=[types.Part(text="go")])
    async for event in runner.run_async(
        user_id="u", session_id=session.id, new_message=msg
    ):
        sd = getattr(event.actions, "state_delta", None) if event.actions else None
        if sd:
            deltas.append(dict(sd))
    s = await runner.session_service.get_session(
        app_name="t", user_id="u", session_id=session.id
    )
    return deltas, dict(s.state)


def test_per_candidate_state_is_recorded_as_deltas() -> None:
    agent = _build({"research": "RESEARCH_STATUS: OK\ndatos reales."})
    deltas, state = asyncio.run(_run(agent))

    # Each candidate's selection is a recorded delta (replayable), in order.
    cands = [d["current_candidate"]["name"] for d in deltas if "current_candidate" in d]
    assert cands == ["Alpha", "Beta"]

    # The accumulated analyses are checkpointed after every candidate, so a run
    # that dies mid-loop still persists the candidates completed so far.
    checkpoints = [d["analyses"] for d in deltas if "analyses" in d]
    assert [len(c) for c in checkpoints[:2]] == [1, 2]
    assert state["analyses"][1]["candidate"]["name"] == "Beta"
    assert state["analyses"][0]["diagnosis"] == "ok"


def test_guard_verdict_is_recorded_as_delta() -> None:
    agent = _build({"research": "RESEARCH_STATUS: SIN_DATOS\nla web devolvió 404."})
    deltas, state = asyncio.run(_run(agent))

    guard = [d for d in deltas if "Datos insuficientes" in str(d.get("diagnosis", ""))]
    assert len(guard) == 2  # one per candidate; research failed for both
    assert state["analyses"][0]["business"] == "Datos insuficientes."
    assert "no se emite diagnóstico" in state["analyses"][0]["diagnosis"].lower()


class StubBoom(BaseAgent):
    """Simulates a transient model failure (e.g. Vertex 429 inside a TaskGroup)."""

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        raise RuntimeError("429 RESOURCE_EXHAUSTED (simulated)")
        yield  # pragma: no cover  (makes this an async generator)


def test_one_candidate_analyst_crash_does_not_lose_the_run() -> None:
    # Regression for the 2026-06-10 prod failure: a single Vertex 429 in one
    # parallel analyst killed the WHOLE run via the TaskGroup. A failing
    # analysts stage must yield an honest "incompleto" entry for that candidate
    # and the loop must continue to the next one.
    analysis = SequentialAgent(
        name="analysis",
        sub_agents=[
            StubWriter(
                name="research_stub",
                payload={"research": "RESEARCH_STATUS: OK\ndatos reales."},
            ),
            StubBoom(name="analysts_stub"),
        ],
    )
    agent = PerCandidateAnalysis(
        name="per_candidate_analysis",
        analysis_agent=analysis,
        synthesizer=StubWriter(name="synth_stub", payload={"diagnosis": "ok"}),
        max_candidates=8,
    )
    deltas, state = asyncio.run(_run(agent))

    analyses = state["analyses"]
    assert [a["candidate"]["name"] for a in analyses] == ["Alpha", "Beta"]
    for a in analyses:
        # The research that DID succeed is kept; the missing analyses carry an
        # explicit incomplete marker instead of a fabricated verdict.
        assert "RESEARCH_STATUS: OK" in a["research"]
        assert "incompleto" in a["business"].lower()
        assert "incompleto" in a["diagnosis"].lower()
    # And the recovery verdicts were recorded as deltas for persisted sessions.
    assert any("incompleto" in str(d.get("diagnosis", "")).lower() for d in deltas)


def test_research_crash_falls_back_to_guard() -> None:
    analysis = SequentialAgent(
        name="analysis",
        sub_agents=[
            StubBoom(name="research_stub"),
            StubWriter(
                name="analysts_stub",
                payload={"business": "b", "metrics": "m", "market": "k"},
            ),
        ],
    )
    agent = PerCandidateAnalysis(
        name="per_candidate_analysis",
        analysis_agent=analysis,
        synthesizer=StubWriter(name="synth_stub", payload={"diagnosis": "ok"}),
        max_candidates=8,
    )
    _, state = asyncio.run(_run(agent))

    analyses = state["analyses"]
    assert len(analyses) == 2
    for a in analyses:
        # A crashed research step is treated like failed research: the
        # anti-hallucination guard refuses to diagnose.
        assert "datos insuficientes" in a["diagnosis"].lower()
        assert a["business"] == "Datos insuficientes."
