import os

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "your-gcp-project")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west1")

from google.adk.agents.llm_agent import Agent
from google.genai import types

from .config import Settings
from .prompts import AGENT_INSTRUCTION
from .tools.read_csv_attachment import read_csv_attachment
from .tools.transform_csv import transform_csv

root_agent = Agent(
    model=Settings.ADK_MODEL,
    name="csv_transformer_agent",
    description=(
        "Transforms CSV files based on natural language instructions: "
        "rename columns, reorder columns, and drop columns."
    ),
    instruction=AGENT_INSTRUCTION,
    tools=[
        read_csv_attachment,
        transform_csv,
    ],
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_budget=0
        )
    ),
)
