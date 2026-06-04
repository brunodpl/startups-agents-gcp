"""Tool: yc_source — find candidate startups from the YC OSS public API (F2).

The YC OSS project mirrors the public Y Combinator company directory as static
JSON. We try the per-tag endpoint for the sector (and for bigrams/words derived
from it, so a messy multi-word sector like "AI developer tools" still resolves to
the real "developer-tools" tag), and fall back to the full company list with a
word-level match otherwise.

Only public data and YC's published API are used (ToS-friendly, GDPR-aware).
"""

import logging
import re

import httpx

logger = logging.getLogger(__name__)

YC_TAG_URL = "https://yc-oss.github.io/api/tags/{slug}.json"
YC_ALL_URL = "https://yc-oss.github.io/api/companies/all.json"


def _significant_words(sector: str) -> list[str]:
    """Lowercased words of length > 2 (drops stopwords like 'para', 'and')."""
    return [w for w in re.split(r"[^a-z0-9]+", sector.lower()) if len(w) > 2]


def _candidate_slugs(sector: str) -> list[str]:
    """YC tag slugs to try, best-first: full phrase, then bigrams, then words."""
    s = sector.lower().strip()
    full = "-".join(s.replace("-", " ").split())
    words = _significant_words(sector)
    slugs = [full]
    slugs += [f"{words[i]}-{words[i + 1]}" for i in range(len(words) - 1)]
    slugs += words
    seen: set[str] = set()
    out: list[str] = []
    for sl in slugs:
        if sl and sl not in seen:
            seen.add(sl)
            out.append(sl)
    return out


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


def _matches_words(company: dict, words: list[str]) -> bool:
    hay = " ".join(
        (company.get("tags") or [])
        + (company.get("industries") or [])
        + [company.get("one_liner") or ""]
    ).lower()
    return any(w in hay for w in words)


def search_startups(
    sector: str, region: str | None = None, limit: int = 20
) -> list[dict]:
    """Busca startups candidatas en YC (Y Combinator) por sector y región.

    Consulta la API pública de YC OSS. Prueba el endpoint del tag del sector (y
    de los bigramas/palabras que contiene, p. ej. "developer-tools"); si ninguno
    existe, cae a la lista completa y filtra por coincidencia de palabras.

    Args:
        sector: Sector o tema EN INGLÉS (p. ej. "artificial intelligence",
            "developer tools", "fintech").
        region: Región para filtrar (substring, p. ej. "Europe", "Spain").
            Si es None no filtra por región.
        limit: Número máximo de candidatas a devolver.

    Returns:
        Lista de dicts {name, website, one_liner, industries, regions, stage,
        batch}. Lista vacía si la consulta falla.
    """
    companies: list[dict] = []
    for slug in _candidate_slugs(sector):
        try:
            resp = httpx.get(YC_TAG_URL.format(slug=slug), timeout=30.0)
        except Exception as e:
            logger.warning("YC tag fetch failed for slug=%r: %s", slug, e)
            continue
        if resp.status_code == 200:
            companies = resp.json()
            break

    if not companies:
        # No tag matched → full list, lenient word-level filter.
        try:
            resp = httpx.get(YC_ALL_URL, timeout=60.0)
            resp.raise_for_status()
            words = _significant_words(sector)
            companies = [c for c in resp.json() if _matches_words(c, words)]
        except Exception as e:
            logger.warning("YC all.json fetch failed for sector=%r: %s", sector, e)
            return []

    normalized = [normalize_company(c) for c in companies]
    if region:
        normalized = [c for c in normalized if _matches_region(c, region)]
    return normalized[:limit]
