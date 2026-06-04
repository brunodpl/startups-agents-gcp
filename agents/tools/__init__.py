"""Tools used by the agents.

- fetch_url       — Analysis: fetch & extract readable text from a candidate URL
- <discovery>     — Discovery: query a free public source API (F2). Respects
                    robots.txt / ToS, GDPR-aware; no LinkedIn/Crunchbase scraping.

Knowledge is NOT a tool: frameworks are read from knowledge/*.md and injected
into agent instructions (no RAG / Vertex AI Search in this demo).
"""
