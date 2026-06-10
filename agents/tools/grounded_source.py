"""Tool source: grounded_source — discover REAL, region-relevant startups via
Gemini + Google Search grounding on Vertex (P0.2).

YC OSS + GitHub return global open-source projects with no geography, so a
regional thesis ("startups de videojuegos en Galicia") cannot be satisfied.
This source asks Gemini, grounded on live Google Search, for real startups
matching the sector and region, normalised to the same flat candidate shape as
the other sources.

Routes through Vertex (``genai.Client(vertexai=True, ...)``) so it consumes the
Marketing AI Agents credit — never ``google.generativeai`` / ``GOOGLE_API_KEY``.
See the consuming-gcp-credits skill.
"""

from __future__ import annotations

import logging

from google import genai
from google.genai import types

from ..config import Settings
from ._json import parse_json_array as _parse_json_array

logger = logging.getLogger(__name__)


def _normalize(raw: dict, region: str | None) -> dict:
    """Map one grounded result to the flat candidate shape (source=grounded)."""
    return {
        "name": raw.get("name", ""),
        "website": raw.get("website", ""),
        "one_liner": raw.get("one_liner", ""),
        "industries": raw.get("industries") or [],
        "regions": raw.get("regions") or ([region] if region else []),
        "stage": raw.get("stage"),
        "source": "grounded",
    }


def search_grounded(
    sector: str, region: str | None = None, limit: int = 10
) -> list[dict]:
    """Find REAL startups for a sector/region using Gemini + Google Search (Vertex).

    Args:
        sector: Sector keyword (English works best, e.g. "video games").
        region: Region/geography to target (e.g. "Galicia"). None = global.
        limit: Max candidates to return.

    Returns:
        Flat candidate dicts {name, website, one_liner, industries, regions,
        stage, source="grounded"}. Empty list on any failure.
    """
    if not Settings.GOOGLE_CLOUD_PROJECT:
        return []
    region_clause = (
        f", con sede o foco principal en '{region}'" if region else " (ámbito global)"
    )
    prompt = (
        "Eres un analista de venture capital. Usando Google Search, encuentra "
        f"startups REALES e invertibles del sector '{sector}'{region_clause}. "
        "Solo datos verificables de fuentes reales; NO inventes ni incluyas "
        "proyectos open-source genéricos que no sean empresas. "
        "Devuelve EXCLUSIVAMENTE un array JSON (sin texto ni ```), cada objeto con: "
        "name, website, one_liner, industries (array), regions (array), stage "
        f"(o null). Máximo {limit} resultados. Si no hay startups de esa región, "
        "devuelve un array vacío []."
    )
    try:
        client = genai.Client(
            vertexai=True,
            project=Settings.GOOGLE_CLOUD_PROJECT,
            location=Settings.GOOGLE_CLOUD_LOCATION,
        )
        resp = client.models.generate_content(
            model=Settings.MODEL_FLASH,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2,
            ),
        )
        rows = _parse_json_array(resp.text or "[]")
    except Exception as e:  # a source must never break discovery
        logger.warning("grounded search failed (%s/%s): %s", sector, region, e)
        return []

    out = [_normalize(r, region) for r in rows if isinstance(r, dict)]
    return [c for c in out if c["name"] and c["website"]][:limit]
