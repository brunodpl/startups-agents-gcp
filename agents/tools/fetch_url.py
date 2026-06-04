"""Tool: fetch_url — download a startup's web page as readable text (F2)."""

from firecrawl import Firecrawl

from ..config import Settings


def fetch_url(url: str) -> str:
    """Fetch a web page and return its readable text.

    Use this to retrieve a startup's website content (landing page, about,
    product pages) before analysing it.

    Args:
        url: Public URL of the startup (e.g. https://example.com).

    Returns:
        The readable text extracted from the page, without HTML or navigation.
    """
    api_key = Settings.FIRECRAWL_API_KEY
    if not api_key:
        return "Error: FIRECRAWL_API_KEY no está configurada."

    client = Firecrawl(api_key=api_key)
    try:
        doc = client.scrape(url, formats=["markdown"], only_main_content=True)
    except Exception as e:
        # La tool nunca debe reventar al agente: el error vuelve como texto.
        return f"Error al descargar {url}: {e}"

    text = doc.markdown
    if not text:
        return f"Error: {url} no devolvió texto legible."

    # Cap para controlar coste de tokens en Vertex (las landings largas no aportan más).
    return text[:20000]
