"""Metrics/traction analyst (F3): reads {research} + {current_candidate}, writes
its analysis to state["metrics"]. No tools — it reasons over session state."""

from google.adk.agents import Agent

from ..config import Settings
from ..prompts import METRICS_INSTRUCTION

metrics_agent = Agent(
    model=Settings.MODEL_FLASH,
    name="metrics_agent",
    description="Analyses a candidate's traction and unit economics signals.",
    instruction=METRICS_INSTRUCTION,
    output_key="metrics",
)
