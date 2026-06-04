"""Root agent for the startup-diagnostics demo.

F2: the root agent is the ResearchAgent — given a startup URL it fetches the
site (fetch_url tool) and returns a structured summary. Becomes the full 360º
Orchestrator (SequentialAgent) in F3.
"""

import os

# Vertex AI routing MUST be set before google.adk resolves the model backend,
# so LLM calls go through aiplatform.googleapis.com (Marketing credit) even on
# Cloud Run without a .env file. See the `consuming-gcp-credits` skill.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "your-gcp-project")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west1")

from .sub_agents.research import research_agent  # noqa: E402

# F2: the ResearchAgent is the root. In F3 this becomes a SequentialAgent that
# chains research -> business_model -> metrics -> growth_levers -> synthesizer.
root_agent = research_agent
