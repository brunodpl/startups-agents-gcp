"""Sub-agents of the 4-stage startup-diagnosis pipeline (v2).

- discovery       — Discovery: thesis -> shortlist via a free public API (F2)
- research        — Analysis: fetch & summarise a candidate's site (uses fetch_url)
- business_model  — Analysis: value proposition, segment, monetisation
- metrics         — Analysis: key metrics & unit-economics signals
- market          — Analysis: market size & competition
- diagnosis       — SynthesizerAgent (gemini-2.5-pro): judgment grounded in the
                    in-context frameworks (knowledge/*.md), citing sources (F3)
- reporting       — ReportingAgent: ranked, structured report (F4)
"""
