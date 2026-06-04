"""Business-model analyst (F3): reads {research} + {current_candidate}, writes
its analysis to state["business"]. No tools — it reasons over session state."""

from google.adk.agents import Agent

from ..config import Settings
from ..prompts import BUSINESS_MODEL_INSTRUCTION

business_model_agent = Agent(
    model=Settings.MODEL_FLASH,
    name="business_model_agent",
    description="Analyses a candidate's business model from the research summary.",
    instruction=BUSINESS_MODEL_INSTRUCTION,
    output_key="business",
)
