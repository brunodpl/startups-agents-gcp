"""Unified discovery source: grounding + Spanish press + YC + GitHub, deduped.

The DiscoveryAgent calls ``find_candidates`` (one tool) so deduplication is
deterministic instead of relying on the LLM to spot duplicates across separate
tool calls. Four sources are combined:

* ``grounded`` — Gemini + Google Search via Vertex: REAL, region-relevant
  startups (P0.2). Listed first so it wins domain conflicts.
* ``spain``    — Spanish startup press/directories via Firecrawl (El Referente,
  Startupxplore, accelerator cohorts). Second: beats YC/GitHub on conflicts.
* ``yc``       — Y Combinator OSS directory.
* ``github``   — open-source projects by topic.
"""

from concurrent.futures import ThreadPoolExecutor
from itertools import zip_longest
from urllib.parse import urlparse

from .gh_source import search_github_projects
from .grounded_source import search_grounded
from .spain_source import search_spain
from .yc_source import search_startups


def _interleave_all(lists: list[list[dict]]) -> list[dict]:
    """Round-robin several lists so every source survives a later cap."""
    out: list[dict] = []
    for row in zip_longest(*lists):
        out.extend(x for x in row if x is not None)
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


def _region_matches(candidate: dict, region: str) -> bool:
    """True if any of the candidate's regions contains ``region`` (substring, ci)."""
    region_l = region.lower()
    return any(region_l in (r or "").lower() for r in candidate.get("regions") or [])


def find_candidates(
    sector: str, region: str | None = None, limit: int = 20
) -> list[dict]:
    """Busca startups candidatas en CUATRO fuentes y deduplica por dominio.

    Combina (1) grounding con Google Search vía Vertex —startups reales y
    regionalmente relevantes—, (2) prensa/directorios de startups españoles vía
    Firecrawl, (3) la API pública de YC y (4) la de GitHub. Etiqueta cada
    candidata con su `source` ("grounded" | "spain" | "yc" | "github"),
    deduplica por dominio web (gana la primera aparición → grounded) y, si hay
    región, sube las candidatas cuyo `regions` casa con ella.

    Args:
        sector: Sector o tema a buscar (p. ej. "artificial intelligence").
        region: Región objetivo (substring). None = sin filtro / sin geo-rerank.
        limit: Número máximo de candidatas a devolver tras deduplicar.

    Returns:
        Lista de dicts {name, website, one_liner, industries, regions, stage,
        source} (la fuente YC añade también `batch`).
    """
    # The four sources are independent blocking I/O (grounded is an LLM+search
    # round-trip, spain is several Firecrawl scrapes) → fetch them concurrently.
    # Each source swallows its own failures and returns [], so .result() is as
    # safe as the previous sequential calls.
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_grounded = pool.submit(search_grounded, sector, region, limit)
        f_es = pool.submit(search_spain, sector, region, limit)
        f_yc = pool.submit(search_startups, sector, region, limit)
        f_gh = pool.submit(search_github_projects, sector, limit)
        grounded = f_grounded.result()
        es = f_es.result()
        yc = [{**c, "source": "yc"} for c in f_yc.result()]
        gh = f_gh.result()
    # Grounded first so it wins domain conflicts (most relevant + regional);
    # spain second so the Spanish press beats YC/GitHub on conflicts.
    merged = dedupe_by_domain(_interleave_all([grounded, es, yc, gh]))
    if region:
        # Stable sort: region-matched candidates rank ahead of global ones.
        merged = sorted(merged, key=lambda c: 0 if _region_matches(c, region) else 1)
    return merged[:limit]
