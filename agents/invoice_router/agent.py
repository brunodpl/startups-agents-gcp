import os

# ── Vertex AI routing (consuming-gcp-credits SKILL) ──────────────────────────
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "your-gcp-project")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west1")
# ─────────────────────────────────────────────────────────────────────────────

from google.adk.agents.llm_agent import Agent
from google.genai import types

from .config import Settings
from .prompts import AGENT_INSTRUCTION
from .tools.channels import normalize_incoming_message
from .tools.classify import classify_document_intent
from .tools.route import suggest_delivery_target
from .tools.upload import handle_uploaded_file

root_agent = Agent(
    model=Settings.ADK_MODEL,
    name="invoice_router_agent",
    description=(
        "Receives inbound invoices from any channel (web upload, WhatsApp, "
        "email) and routes each document to the appropriate delivery target."
    ),
    instruction=AGENT_INSTRUCTION,
    tools=[
        handle_uploaded_file,
        normalize_incoming_message,
        classify_document_intent,
        suggest_delivery_target,
    ],
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_budget=0  # desactiva reasoning — 6x ahorro en tokens
        )
    ),
)
