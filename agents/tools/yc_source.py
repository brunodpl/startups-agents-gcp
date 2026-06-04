"""Tool: yc_source — find candidate startups from the YC OSS public API (F2).

The YC OSS project mirrors the public Y Combinator company directory as static
JSON. We hit the per-tag endpoint when the sector maps to a known tag, and fall
back to the full company list (filtered by sector text) otherwise.

Only public data and YC's published API are used (ToS-friendly, GDPR-aware).
"""

import logging

import httpx

logger = logging.getLogger(__name__)

YC_TAG_URL = "https://yc-oss.github.io/api/tags/{slug}.json"
YC_ALL_URL = "https://yc-oss.github.io/api/companies/all.json"


def _slugify(text: str) -> str:
    """Turn a free-text sector into a YC tag slug (e.g. 'AI dev tools')."""
    return "-".join(text.lower().split())


def normalize_company(raw: dict) -> dict:
    """Map one raw YC OSS company object to our flat candidate shape.

    Missing fields degrade to empty defaults so downstream code never sees
    ``None`` where it expects a list.
    """
    return {
        "name": raw.get("name", ""),
        "website": raw.get("website", ""),
        "one_liner": raw.get("one_liner", ""),
        "industries": raw.get("industries") or [],
        "regions": raw.get("regions") or [],
        "stage": raw.get("stage"),
        "batch": raw.get("batch"),
    }


def _matches_region(company: dict, region: str) -> bool:
    region_l = region.lower()
    return any(region_l in r.lower() for r in company.get("regions") or [])


def search_startups(
    sector: str, region: str | None = None, limit: int = 20
) -> list[dict]:
    """Busca startups candidatas en YC (Y Combinator) por sector y región.

    Consulta la API pública de YC OSS. Primero intenta el endpoint del tag que
    corresponde al sector (p. ej. "artificial-intelligence"); si ese tag no
    existe, cae a la lista completa y filtra por coincidencia de texto del
    sector en tags/industries.

    Args:
        sector: Sector o tema a buscar (p. ej. "artificial intelligence",
            "developer tools", "fintech").
        region: Región para filtrar (substring, p. ej. "Europe", "Spain").
            Si es None no filtra por región.
        limit: Número máximo de candidatas a devolver.

    Returns:
        Lista de dicts con las claves {name, website, one_liner, industries,
        regions, stage, batch}. Lista vacía si la consulta falla.
    """
    slug = _slugify(sector)
    try:
        resp = httpx.get(YC_TAG_URL.format(slug=slug), timeout=30.0)
        if resp.status_code == 200:
            companies = resp.json()
        else:
            # Tag desconocido → lista completa, filtrada por texto del sector.
            resp = httpx.get(YC_ALL_URL, timeout=60.0)
            resp.raise_for_status()
            sector_l = sector.lower()
            companies = [
                c
                for c in resp.json()
                if sector_l
                in " ".join(
                    (c.get("tags") or []) + (c.get("industries") or [])
                ).lower()
            ]
    except Exception as e:
        logger.warning("YC OSS fetch failed for sector=%r: %s", sector, e)
        return []

    normalized = [normalize_company(c) for c in companies]
    if region:
        normalized = [c for c in normalized if _matches_region(c, region)]
    return normalized[:limit]
