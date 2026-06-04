"""SynthesizerAgent / Diagnosis (F3).

Uses the Pro model to turn the four analyses (research/business/metrics/market)
into a grounded verdict that MUST cite the VC frameworks. The frameworks are
injected in-context (NO RAG) by appending load_frameworks() to the instruction
at build time, and the verdict is written to state["diagnosis"].
"""

from google.adk.agents import Agent

from ..config import Settings
from ..knowledge import load_frameworks
from ..prompts import DIAGNOSIS_INSTRUCTION

synthesizer_agent = Agent(
    model=Settings.MODEL_PRO,
    name="synthesizer_agent",
    description="Synthesises a grounded, framework-cited diagnosis of a candidate.",
    instruction=DIAGNOSIS_INSTRUCTION + "\n" + load_frameworks(),
    output_key="diagnosis",
)
