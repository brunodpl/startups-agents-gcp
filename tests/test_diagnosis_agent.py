"""Wiring smoke for the F3 SynthesizerAgent.

Run: ``uv run python -m pytest tests/test_diagnosis_agent.py -q``
"""

from agents.sub_agents.diagnosis import synthesizer_agent


def test_synthesizer_uses_pro_and_writes_diagnosis() -> None:
    assert "pro" in synthesizer_agent.model
    assert synthesizer_agent.output_key == "diagnosis"
    assert not synthesizer_agent.tools  # reasons over state, no tools


def test_synthesizer_instruction_embeds_frameworks() -> None:
    instr = synthesizer_agent.instruction
    # Frameworks are injected in-context (NO RAG).
    assert "# Framework:" in instr
    assert "Marco de evaluación de startups" in instr
