"""ReportingAgent (F4): turn the per-candidate diagnoses into a ranked report.

Reads ``{analyses}`` from state and writes a readable ranked summary + a JSON
block (matching schemas.Report) to ``state["report"]``. No tools.
"""

from google.adk.agents import Agent

from ..config import Settings
from ..prompts import REPORTING_INSTRUCTION

reporting_agent = Agent(
    model=Settings.MODEL_FLASH,
    name="reporting_agent",
    description="Ranks the diagnosed candidates into a final investor report.",
    instruction=REPORTING_INSTRUCTION,
    output_key="report",
)
