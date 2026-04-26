from google.adk.agents.llm_agent import Agent

from .config import Settings
from .prompts import AGENT_INSTRUCTION
from .tools.channels import normalize_incoming_message
from .tools.classify import classify_document_intent
from .tools.route import suggest_delivery_target

root_agent = Agent(
    model=Settings.ADK_MODEL,
    name="invoice_router_agent",
    description=(
        "Receives an inbound WhatsApp or email message, detects whether it "
        "contains an invoice-related document, and suggests a delivery target."
    ),
    instruction=AGENT_INSTRUCTION,
    tools=[
        normalize_incoming_message,
        classify_document_intent,
        suggest_delivery_target,
    ],
)
