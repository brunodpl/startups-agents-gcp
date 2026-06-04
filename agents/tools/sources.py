"""Unified discovery source (F4): query YC + GitHub and dedupe by domain.

The DiscoveryAgent calls ``find_candidates`` (one tool) so deduplication is
deterministic instead of relying on the LLM to spot duplicates across two
separate tool calls.
"""

from itertools import zip_longest
from urllib.parse import urlparse

from .gh_source import search_github_projects
from .yc_source import search_startups


def _interleave(a: list[dict], b: list[dict]) -> list[dict]:
    """Round-robin two lists so both sources survive a later cap."""
    out: list[dict] = []
    for x, y in zip_longest(a, b):
        if x is not None:
            out.append(x)
        if y is not None:
            out.append(y)
    return out


def _domain(website: str) -> str:
    """Bare registrable host of a URL, lowercased and without ``www.``."""
    if not website:
        return ""
    netloc = urlparse(
        website if "://" in website else f"https://{website}"
    ).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def dedupe_by_domain(candidates: list[dict]) -> list[dict]:
    """Drop later candidates that share a website domain with an earlier one.

    Candidates without a usable domain are always kept (we can't tell them
    apart). Order is preserved, so the first source listed wins on conflicts.
    """
    seen: set[str] = set()
    out: list[dict] = []
    for c in candidates:
        d = _domain(c.get("website", ""))
        if d and d in seen:
            continue
        if d:
            seen.add(d)
        out.append(c)
    return out


def find_candidates(
    sector: str, region: str | None = None, limit: int = 20
) -> list[dict]:
    """Busca startups candidatas en DOS fuentes (YC y GitHub) y deduplica.

    Combina la API pública de YC (Y Combinator) y la de GitHub, etiqueta cada
    candidata con su `source` ("yc" o "github") y elimina duplicados por dominio
    web (gana la primera aparición, que es YC).

    Args:
        sector: Sector o tema a buscar (p. ej. "artificial intelligence").
        region: Región para filtrar la fuente YC (substring). None = sin filtro.
        limit: Número máximo de candidatas a devolver tras deduplicar.

    Returns:
        Lista de dicts con las claves {name, website, one_liner, industries,
        regions, stage, source} (la fuente YC añade también `batch`).
    """
    yc = [{**c, "source": "yc"} for c in search_startups(sector, region, limit)]
    gh = search_github_projects(sector, limit)
    # Interleave so a small `limit` still draws from both sources; dedupe keeps
    # the first occurrence (YC wins on domain conflicts).
    return dedupe_by_domain(_interleave(yc, gh))[:limit]
