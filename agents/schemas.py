"""Pydantic schemas shared across the pipeline.

F2 lands the Discovery models (``Thesis``, ``Candidate``, ``Shortlist``).
Analysis/Diagnosis/Report models are added in F3/F4 as those phases land.

These models double as the contract that flows through ADK session state via
``output_key``. ADK serialises state to JSON, so keep every field JSON-friendly
(no arbitrary Python objects).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Thesis(BaseModel):
    """An investment thesis: what kind of startup we are hunting for."""

    sector: str
    stage: str
    geography: str
    signals: list[str] = Field(default_factory=list)


class Candidate(BaseModel):
    """A startup surfaced by Discovery.

    ``score`` and ``rationale`` are left empty by the source tools and filled
    in by the DiscoveryAgent when it ranks candidates against the thesis.
    """

    name: str
    website: str
    one_liner: str
    industries: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    stage: str | None = None
    source: str
    score: float | None = None
    rationale: str | None = None


class Shortlist(BaseModel):
    """The thesis plus the ranked candidates Discovery decided to keep."""

    thesis: Thesis
    candidates: list[Candidate] = Field(default_factory=list)


class ReportItem(BaseModel):
    """One candidate's entry in the final ranked report (F4)."""

    name: str
    score: float | None = None
    fortalezas: list[str] = Field(default_factory=list)
    riesgos: list[str] = Field(default_factory=list)
    palancas: list[str] = Field(default_factory=list)
    experimentos: list[str] = Field(default_factory=list)
    citas: list[str] = Field(default_factory=list)


class Report(BaseModel):
    """The final ranked report produced by the ReportingAgent (F4)."""

    ranking: list[ReportItem] = Field(default_factory=list)
    resumen: str | None = None
