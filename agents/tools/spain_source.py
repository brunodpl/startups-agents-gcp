"""Tool source: spain_source — discover Spanish/Galician startups from the
Spanish startup press and directories via Firecrawl search/scrape + Gemini.

YC and GitHub barely cover early-stage Spanish startups, and grounded search is
generic. This source targets the publications that actually announce pre-seed
rounds and accelerator cohorts in Spain (El Referente, Startupxplore, regional
accelerator press), scrapes the top articles with Firecrawl, and asks Gemini
Flash to extract ONLY the startups explicitly named in the scraped text,
normalised to the same flat candidate shape as the other sources.

Extraction routes through Vertex (``genai.Client(vertexai=True, ...)``) so it
consumes the Marketing AI Agents credit — never ``GOOGLE_API_KEY``. See the
consuming-gcp-credits skill.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from firecrawl import Firecrawl
from google import genai
from google.genai import types

from ..config import Settings
from ._json import parse_json_array

logger = logging.getLogger(__name__)

# Publications/directories that announce Spanish rounds and cohorts.
PRESS_DOMAINS = ["elreferente.es", "startupxplore.com"]

_MAX_PAGES = 4  # articles scraped per call (Firecrawl credits + token cost)
_PAGE_CHAR_CAP = 8_000
_TOTAL_CHAR_CAP = 25_000
_SEARCH_LIMIT = 5  # results per query

# Press articles name startups but rarely link their websites, so we resolve
# missing sites with one extra search per candidate. Domains that can never be
# a startup's own site are skipped when picking the resolved URL.
_MAX_RESOLVE = 6
_NON_STARTUP_DOMAINS = (
    "elreferente.es",
    "startupxplore.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "crunchbase.com",
    "wikipedia.org",
)


def _normalize(raw: dict, region: str | None) -> dict:
    """Map one extracted result to the flat candidate shape (source=spain)."""
    return {
        "name": raw.get("name", ""),
        "website": raw.get("website", ""),
        "one_liner": raw.get("one_liner", ""),
        "industries": raw.get("industries") or [],
        "regions": raw.get("regions") or [region or "España"],
        "stage": raw.get("stage"),
        "source": "spain",
    }


def _resolve_website(client: Firecrawl, name: str, region: str | None) -> str:
    """Find a startup's own website via one Firecrawl search.

    Returns the origin (scheme + host) of the first result that is not press,
    social media or a directory, or "" if none qualifies. The URL comes from a
    real search result, never from the LLM, so it cannot be hallucinated.
    """
    data = client.search(
        f'"{name}" startup {region or "España"} web oficial', limit=3
    )
    for hit in getattr(data, "web", None) or []:
        url = getattr(hit, "url", "") or ""
        if not url:
            continue
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if not host or any(d in host for d in _NON_STARTUP_DOMAINS):
            continue
        return f"{parsed.scheme}://{parsed.netloc}"
    return ""


def _collect_pages(
    client: Firecrawl, sector: str, region: str | None
) -> list[tuple[str, str]]:
    """Search the Spanish startup press and scrape the top articles.

    Returns up to ``_MAX_PAGES`` (url, markdown) tuples. A page that fails to
    scrape is skipped; a query that fails raises (caller isolates the error).
    """
    geo = region or "España"
    queries = [
        # Dedicated startup press/directories, any recency.
        (f"startups {sector} {geo}", PRESS_DOMAINS),
        # Open web: round/launch/cohort announcements (regional press, notes).
        (f"startup {sector} {geo} ronda OR lanzamiento OR aceleradora", None),
    ]
    urls: list[str] = []
    seen: set[str] = set()
    for query, domains in queries:
        data = client.search(
            query,
            limit=_SEARCH_LIMIT,
            **({"include_domains": domains} if domains else {}),
        )
        for hit in getattr(data, "web", None) or []:
            url = getattr(hit, "url", "") or ""
            if url and url not in seen:
                seen.add(url)
                urls.append(url)

    pages: list[tuple[str, str]] = []
    total = 0
    for url in urls:
        if len(pages) >= _MAX_PAGES or total >= _TOTAL_CHAR_CAP:
            break
        try:
            doc = client.scrape(url, formats=["markdown"], only_main_content=True)
        except Exception as e:  # one broken article must not kill the source
            logger.warning("spain source: scrape failed for %s: %s", url, e)
            continue
        text = (doc.markdown or "")[:_PAGE_CHAR_CAP]
        if not text.strip():
            continue
        pages.append((url, text))
        total += len(text)
    return pages


def search_spain(sector: str, region: str | None = None, limit: int = 10) -> list[dict]:
    """Find Spanish/Galician startups in the Spanish startup press (Firecrawl).

    Args:
        sector: Sector keyword (English works, e.g. "fintech").
        region: Region to target (e.g. "Galicia"). None = España.
        limit: Max candidates to return.

    Returns:
        Flat candidate dicts {name, website, one_liner, industries, regions,
        stage, source="spain"}. Empty list on any failure.
    """
    if not Settings.FIRECRAWL_API_KEY or not Settings.GOOGLE_CLOUD_PROJECT:
        return []
    try:
        client = Firecrawl(api_key=Settings.FIRECRAWL_API_KEY)
        pages = _collect_pages(client, sector, region)
    except Exception as e:  # a source must never break discovery
        logger.warning("spain source: search failed (%s/%s): %s", sector, region, e)
        return []
    if not pages:
        return []

    corpus = "\n\n".join(f"### Fuente: {url}\n{text}" for url, text in pages)
    prompt = (
        "Eres un analista de venture capital. Abajo tienes artículos de prensa "
        "y directorios de startups españoles. Extrae las startups REALES que se "
        "mencionan EXPLÍCITAMENTE en el texto y que encajen con el sector "
        f"'{sector}'. NO inventes ninguna: solo startups nombradas en el texto. "
        "El campo website solo si su web aparece en el texto (si no, \"\"). "
        "Devuelve EXCLUSIVAMENTE un array JSON (sin texto ni ```), cada objeto "
        "con: name, website, one_liner, industries (array), regions (array), "
        f"stage (o null). Máximo {limit} resultados. Si no hay ninguna, "
        "devuelve [].\n\n" + corpus
    )
    try:
        gclient = genai.Client(
            vertexai=True,
            project=Settings.GOOGLE_CLOUD_PROJECT,
            location=Settings.GOOGLE_CLOUD_LOCATION,
        )
        resp = gclient.models.generate_content(
            model=Settings.MODEL_FLASH,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1),
        )
        rows = parse_json_array(resp.text or "[]")
    except Exception as e:
        logger.warning("spain source: extraction failed (%s/%s): %s", sector, region, e)
        return []

    out = [_normalize(r, region) for r in rows if isinstance(r, dict)]
    # The press names startups without linking their site: resolve the missing
    # websites with one extra search each (capped), or the filter drops them.
    lookups = 0
    for c in out:
        if c["name"] and not c["website"] and lookups < _MAX_RESOLVE:
            lookups += 1
            try:
                c["website"] = _resolve_website(client, c["name"], region)
            except Exception as e:
                logger.warning(
                    "spain source: website resolution failed for %s: %s",
                    c["name"], e,
                )
    return [c for c in out if c["name"] and c["website"]][:limit]
