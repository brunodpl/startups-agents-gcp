"""Tool: gh_source — second discovery source via the public GitHub API (F4).

Searches GitHub repositories by topic and normalises them to the same flat
candidate shape as yc_source. Many early-stage dev-tool startups have a strong
open-source presence, so this complements the YC directory. No API key needed
(unauthenticated search, low rate limit — fine for a demo).
"""

import logging

import httpx

logger = logging.getLogger(__name__)

GH_SEARCH_URL = "https://api.github.com/search/repositories"


def normalize_repo(raw: dict) -> dict:
    """Map one GitHub repo object to our flat candidate shape (source=github)."""
    return {
        "name": raw.get("name", ""),
        # Prefer the project homepage; fall back to the repo URL.
        "website": (raw.get("homepage") or raw.get("html_url") or ""),
        "one_liner": raw.get("description") or "",
        "industries": raw.get("topics") or [],
        "regions": [],
        "stage": None,
        "source": "github",
    }


def search_github_projects(topic: str, limit: int = 20) -> list[dict]:
    """Busca proyectos/startups open-source en GitHub por tema.

    Útil como segunda fuente de descubrimiento: muchas startups de developer
    tools nacen como proyectos open-source.

    Args:
        topic: Tema o sector a buscar (p. ej. "developer tools", "llm agents").
        limit: Número máximo de proyectos a devolver.

    Returns:
        Lista de dicts {name, website, one_liner, industries, regions, stage,
        source="github"}. Lista vacía si la consulta falla.
    """
    params = {
        "q": f"{topic} in:name,description,topics",
        "sort": "stars",
        "order": "desc",
        "per_page": min(max(limit, 1), 50),
    }
    headers = {"Accept": "application/vnd.github+json"}
    try:
        resp = httpx.get(GH_SEARCH_URL, params=params, headers=headers, timeout=30.0)
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except Exception as e:
        logger.warning("GitHub search failed for topic=%r: %s", topic, e)
        return []

    return [normalize_repo(r) for r in items[:limit]]
