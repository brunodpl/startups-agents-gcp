"""DiscoveryAgent (F2): thesis -> scored shortlist of candidate startups.

Calls the YC OSS source tool, scores each candidate against the thesis, and
writes the resulting shortlist (as JSON text) to ``state["shortlist"]`` via
``output_key`` so the rest of the pipeline can consume it.
"""

from google.adk.agents import Agent

from ..config import Settings
from ..prompts import DISCOVERY_INSTRUCTION
from ..tools.sources import find_candidates

# TOP_N is injected with an f-string (not str.format) so the JSON braces inside
# DISCOVERY_INSTRUCTION are left untouched.
discovery_agent = Agent(
    model=Settings.MODEL_FLASH,
    name="discovery_agent",
    description="Turns an investment thesis into a scored shortlist of startups.",
    instruction=(
        DISCOVERY_INSTRUCTION
        + f"\nDevuelve EXACTAMENTE las {Settings.TOP_N} mejores candidatas "
        "(o menos si la tool devuelve menos)."
    ),
    tools=[find_candidates],
    output_key="shortlist",
)
