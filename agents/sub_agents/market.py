"""Market analyst (F3): reads {research} + {current_candidate}, writes its
analysis to state["market"]. No tools — it reasons over session state."""

from google.adk.agents import Agent

from ..config import Settings
from ..prompts import MARKET_INSTRUCTION

market_agent = Agent(
    model=Settings.MODEL_FLASH,
    name="market_agent",
    description="Analyses a candidate's market size, timing and competition.",
    instruction=MARKET_INSTRUCTION,
    output_key="market",
)
