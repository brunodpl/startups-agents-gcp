"""Assembles the 4-stage pipeline (F3).

Top level is a SequentialAgent:

    discovery  ->  PerCandidateAnalysis  ->  reporting

``PerCandidateAnalysis`` is a custom BaseAgent that loops over the shortlist
Discovery produced and, for each candidate, runs:

    research  ->  ParallelAgent(business, metrics, market)  ->  synthesizer

accumulating one diagnosis per candidate into ``state["analyses"]``.

Note (deviation from the plan): the plan grouped research with the three
analysts in a single ParallelAgent and ran the synthesizer once at the top
level. Both are corrected here — the analysts read ``{research}`` so research
must finish first (Sequential then Parallel), and the synthesizer runs per
candidate so every candidate gets its own grounded verdict for ranking.

State is JSON-serialised by ADK, so candidates/analyses are kept as plain dicts.
"""

from __future__ import annotations

import json
import logging
import re
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, ParallelAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from .config import Settings
from .sub_agents.business_model import business_model_agent
from .sub_agents.diagnosis import synthesizer_agent
from .sub_agents.discovery import discovery_agent
from .sub_agents.market import market_agent
from .sub_agents.metrics import metrics_agent
from .sub_agents.reporting import reporting_agent
from .sub_agents.research import research_agent

logger = logging.getLogger(__name__)


def _strip_and_parse(text: str) -> dict | list:
    """Parse a JSON blob that may be wrapped in a ```json fence or prose."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: grab the outermost {...} object.
        i, j = text.find("{"), text.rfind("}")
        if 0 <= i < j:
            return json.loads(text[i : j + 1])
        raise


def parse_shortlist(raw: object) -> tuple[dict | None, list[dict]]:
    """Turn Discovery's ``state["shortlist"]`` into (thesis, candidates).

    ``raw`` may already be a dict (rare) or, more commonly, the agent's JSON
    text output. Always returns plain dicts so the rest of the pipeline can put
    them straight back into session state.
    """
    if raw is None:
        return None, []
    try:
        data = raw if isinstance(raw, dict) else _strip_and_parse(str(raw))
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Could not parse shortlist: %s", e)
        return None, []
    if isinstance(data, list):
        return None, data
    return data.get("thesis"), data.get("candidates") or []


class PerCandidateAnalysis(BaseAgent):
    """Runs analysis + diagnosis once per shortlisted candidate."""

    analysis_agent: BaseAgent
    synthesizer: BaseAgent
    top_n: int = 3

    def __init__(
        self,
        name: str,
        analysis_agent: BaseAgent,
        synthesizer: BaseAgent,
        top_n: int = 3,
    ) -> None:
        super().__init__(
            name=name,
            analysis_agent=analysis_agent,
            synthesizer=synthesizer,
            top_n=top_n,
            sub_agents=[analysis_agent, synthesizer],
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        thesis, candidates = parse_shortlist(state.get("shortlist"))
        candidates = candidates[: self.top_n]
        logger.info("PerCandidateAnalysis: %d candidate(s)", len(candidates))

        analyses: list[dict] = []
        for cand in candidates:
            # Make the candidate (and thesis) visible to the sub-agents. Direct
            # mutation shares the live state dict the sub-agents read.
            state["current_candidate"] = cand
            if thesis is not None:
                state["thesis"] = thesis

            async for event in self.analysis_agent.run_async(ctx):
                yield event
            async for event in self.synthesizer.run_async(ctx):
                yield event

            analyses.append(
                {
                    "candidate": cand,
                    "research": state.get("research"),
                    "business": state.get("business"),
                    "metrics": state.get("metrics"),
                    "market": state.get("market"),
                    "diagnosis": state.get("diagnosis"),
                }
            )

        state["analyses"] = analyses
        # Record a delta so the accumulated analyses persist on the session.
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(state_delta={"analyses": analyses}),
        )


_PIPELINE: SequentialAgent | None = None


def build_pipeline() -> SequentialAgent:
    """Build the full discovery -> per-candidate analysis/diagnosis pipeline.

    Memoised: the sub-agents are module singletons and ADK lets an agent have a
    single parent, so the tree is built once and reused.
    """
    global _PIPELINE
    if _PIPELINE is not None:
        return _PIPELINE

    analysis_agent = SequentialAgent(
        name="analysis",
        description="Research a candidate, then analyse 3 dimensions in parallel.",
        sub_agents=[
            research_agent,
            ParallelAgent(
                name="dimension_analysts",
                sub_agents=[business_model_agent, metrics_agent, market_agent],
            ),
        ],
    )
    per_candidate = PerCandidateAnalysis(
        name="per_candidate_analysis",
        analysis_agent=analysis_agent,
        synthesizer=synthesizer_agent,
        top_n=Settings.TOP_N,
    )
    _PIPELINE = SequentialAgent(
        name="startup_diagnostics_pipeline",
        description="Thesis -> scored shortlist -> per-candidate diagnosis -> report.",
        sub_agents=[discovery_agent, per_candidate, reporting_agent],
    )
    return _PIPELINE
