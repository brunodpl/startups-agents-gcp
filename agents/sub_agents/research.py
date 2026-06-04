"""ResearchAgent: fetch a candidate's site and return a structured summary.

F3: reads the candidate to research from ``state["current_candidate"]`` (set by
PerCandidateAnalysis) and writes its summary to ``state["research"]`` via
``output_key`` so the business/metrics/market analysts can read ``{research}``.
"""

from google.adk.agents import Agent

from ..config import Settings
from ..prompts import RESEARCH_INSTRUCTION
from ..tools.fetch_url import fetch_url

research_agent = Agent(
    model=Settings.MODEL_FLASH,
    name="startup_research_agent",
    description="Fetches a startup's website and produces a structured summary.",
    instruction=RESEARCH_INSTRUCTION,
    tools=[fetch_url],
    output_key="research",
)
