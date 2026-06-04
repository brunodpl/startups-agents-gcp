"""ResearchAgent (F2): fetch a startup's site and return a structured summary."""

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
)
