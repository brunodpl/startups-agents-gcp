"""Root agent for the startup-diagnostics demo.

F1: a trivial "hello-world" LlmAgent whose only job is to prove the
Vertex AI + ADK + Cloud Run pipeline end to end (get a working URL FIRST).
It grows into the 360º diagnosis Orchestrator (SequentialAgent) in F3.
"""

import os

# Vertex AI routing MUST be set before google.adk resolves the model backend,
# so LLM calls go through aiplatform.googleapis.com (Marketing credit) even on
# Cloud Run without a .env file.  See the `consuming-gcp-credits` skill.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "your-gcp-project")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west1")

from google.adk.agents import Agent  # noqa: E402
from google.genai import types  # noqa: E402

from .config import Settings  # noqa: E402
from .prompts import HELLO_INSTRUCTION  # noqa: E402

root_agent = Agent(
    model=Settings.MODEL_FLASH,
    name="startup_diagnostics_agent",
    description=(
        "Demo F1: greets the user and asks for a startup URL. Will become the "
        "360º startup-diagnosis orchestrator."
    ),
    instruction=HELLO_INSTRUCTION,
    # Disable thinking for a fast, cheap demo response (F1 has no reasoning yet).
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
)
