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
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, ParallelAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from pydantic import ValidationError

from .config import Settings
from .schemas import Shortlist
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
    # Enforce the schema when the data is complete; fall back tolerantly to the
    # raw dicts otherwise (the model may emit a partial thesis on some runs).
    try:
        sl = Shortlist.model_validate(data)
        return sl.thesis.model_dump(), [c.model_dump() for c in sl.candidates]
    except ValidationError as e:
        logger.warning("Shortlist failed schema validation, using raw dicts: %s", e)
        return data.get("thesis"), data.get("candidates") or []


# Markers meaning the research step produced no usable data: the RESEARCH_STATUS
# sentinel the ResearchAgent emits, plus the literal error strings fetch_url
# returns (in case they pass through verbatim).
_FAIL_MARKERS = (
    "research_status: sin_datos",
    "no devolvió texto legible",
    "error al descargar",
    "firecrawl_api_key no está configurada",
    "datos insuficientes",
)


def _research_failed(research: object) -> bool:
    """True if research is empty or signals a fetch failure (404/error/no data).

    Guards the pipeline so a candidate with no real data does NOT receive a
    confident, fabricated diagnosis.
    """
    if not research or not str(research).strip():
        return True
    text = str(research).strip().lower()
    if text.startswith("error"):
        return True
    return any(m in text for m in _FAIL_MARKERS)


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

        # analysis_agent = Sequential(research, ParallelAgent(analysts)); split
        # the two stages so we can gate the analysts + synthesizer on research
        # actually producing data.
        research_stage = self.analysis_agent.sub_agents[0]
        analysts_stage = self.analysis_agent.sub_agents[1]

        analyses: list[dict] = []
        for cand in candidates:
            # Make the candidate (and thesis) visible to the sub-agents. Direct
            # mutation shares the live state dict the sub-agents read. Clear the
            # per-candidate outputs first so a failed candidate can't inherit the
            # previous one's analysis (state bleed).
            state["current_candidate"] = cand
            if thesis is not None:
                state["thesis"] = thesis
            for key in ("research", "business", "metrics", "market", "diagnosis"):
                state.pop(key, None)

            async for event in research_stage.run_async(ctx):
                yield event

            if _research_failed(state.get("research")):
                # Anti-hallucination guard: no real data → no invented verdict.
                logger.info(
                    "Guard: insufficient research for %r; skipping diagnosis.",
                    cand.get("name"),
                )
                state["business"] = "Datos insuficientes."
                state["metrics"] = "Datos insuficientes."
                state["market"] = "Datos insuficientes."
                state["diagnosis"] = (
                    "Datos insuficientes: no se pudo obtener información fiable de "
                    f"la web de {cand.get('name', 'la candidata')} (la fuente "
                    "devolvió error o estaba vacía). No se emite diagnóstico para "
                    "evitar conclusiones inventadas. Confianza: baja."
                )
            else:
                async for event in analysts_stage.run_async(ctx):
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
