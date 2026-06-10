# Investigación: fuentes y herramientas para descubrir startups (junio 2026)

Contexto: pipeline ADK + Vertex en Cloud Run para Tales Venture (foco pre-seed/seed
España/Galicia, algo global). Presupuesto MVP ~0€/mes adicionales. Ya contratado:
Firecrawl + créditos GCP (grounding). Decisiones tomadas: búsqueda **bajo demanda**
(no monitorización continua, de momento), geografía **equilibrada**.

**Implementado a raíz de esta investigación:** `spain_source` (prensa/directorios
españoles vía Firecrawl + extracción Gemini) como cuarta fuente de `find_candidates`.

## 1. X/Twitter

### API oficial — inviable para discovery en 2026
- Feb-2026: modelo **pay-per-use por defecto** (~$0.005/post leído, tope 2M/mes).
  Abr-2026: escrituras a $0.015/post. **Tier gratuito descontinuado.**
- Tiers legacy (solo suscriptores existentes): Basic $200/mes (15k lecturas — inútil),
  Pro $5.000/mes (1M lecturas, full-archive search), Enterprise ~$42k/mes.
- Leer 100k tweets/mes en pay-per-use ≈ $500. La búsqueda full-archive sigue en Pro+.
- Fuentes: xpoz.ai pricing guide, postproxy.dev/blog/x-api-pricing-2026,
  twitterapi.io/blog/x-api-cost-breakdown-2026

### Alternativas de terceros (viables)
| Servicio | Precio | Notas |
|---|---|---|
| twitterapi.io | $0.15/1k tweets, $0.18/1k perfiles, PAYG | REST drop-in, search avanzada con histórico |
| socialdata.tools | $0.20/1k tweets | Monitoring API con webhooks por query — ideal para monitorización continua |
| Apify actors (apidojo/tweet-scraper, kaitoeasyapi) | $0.18–0.40/1k, pay-per-result | Integrable vía Apify MCP server; free tier $5/mes en créditos |
| Nitter | — | **Muerto en la práctica** (instancias públicas caídas; self-host requiere cuentas reales) |

Legal: scraping contra ToS de X (precedente *X vs Bright Data* 2024 favoreció al
scraper de datos públicos). Riesgo práctico bajo para research interno; no construir
producto comercial encima sin asesoría.

## 2. LinkedIn

- API oficial cerrada (solo partners). **Proxycurl murió** por demanda de LinkedIn
  (cerró jul-2025) — LinkedIn litiga activamente.
- Viables: **Apify actors** (posts por keyword ~$1/1k, company posts $2/1k, perfiles
  $3/1k, sin cookies), **Bright Data** ($1.50/1k registros PAYG, posicionamiento
  "compliant"). **PhantomBuster** ($69+/mes) usa tu cuenta → riesgo de baneo, mal
  encaje para agente headless.
- Es donde los fundadores españoles anuncian primero ("lanzamos", "ronda pre-seed").
  **Primera candidata si se relaja el presupuesto.**

## 3. Otras redes/comunidades

| Fuente | Acceso | Coste | Veredicto |
|---|---|---|---|
| Reddit API | OAuth, 100 QPM free (no comercial) | 0€ | OK como secundaria; poca señal española |
| Product Hunt API v2 | GraphQL gratis (6.250 ptos/15min) | 0€ | Fácil; makers redactados desde 2023; poca señal gallega |
| Hacker News (Algolia) | hn.algolia.com/api, sin key | 0€ | Show HN / lanzamientos; trivial de integrar |
| Indie Hackers / BetaList | Sin API | Firecrawl | Secundario |
| Discord/Slack | Sin acceso programático a comunidades de terceros | — | Descartado |

## 4. Fuentes España/Galicia (la mina de oro — implementadas en `spain_source`)

Casi ninguna tiene API → Firecrawl search/scrape:

- **El Referente** (elreferente.es) — el medio que mejor cubre rondas pre-seed/seed
  españolas; directorio + cobertura explícita de Galicia (ViaGalicia, etc.).
- **Startupxplore** (startupxplore.com) — plataforma líder de inversión con
  directorio público de startups españolas.
- **Ecosistema gallego**: ViaGalicia (Zona Franca Vigo + Xunta; 8ª ed. jun-2026 con
  14 startups; capital riesgo vía Vigo Activo y XesGalicia), Business Factories
  (BFFood, BFAuto, BFAero, BF Climatech), nuevas aceleradoras Xunta (biotech/salud/
  energía). Notas de prensa y listados de cohortes scrapeables.
- **Otros nacionales**: Lanzadera (cohortes en web), ENISA (memoria anual de
  beneficiarios), prensa (El Español-Invertia, Expansión, La Voz de Galicia).
- **BORME / Registro Mercantil**: PDFs diarios públicos.
  - `bormeparser` (Python, libre) — parsear constituciones de las 4 provincias
    gallegas a coste 0. Mucho ruido (filtrar por objeto social con LLM), pero
    detección antes que nadie. Encaja en monitorización continua, no bajo demanda.
  - LibreBOR (librebor.me) — API REST de pago (precios no verificados, página 403).

## 5. Agregadores (todos inviables para MVP)

| Plataforma | Precio | Nota |
|---|---|---|
| Crunchbase | API solo enterprise; free API eliminada 2025 | Targets gallegas no están ahí |
| Dealroom | ~€12,5–17k/año (API solo Enterprise) | Mejor cobertura europea, eso sí |
| PitchBook | ~$24k/año/usuario | — |
| Harmonic.ai | ~$25–30k/año (estimado) | La opción "pro" futura: diseñada para descubrimiento temprano |
| Specter / Tracxn | Enterprise, sin precios públicos | — |

## 6. Herramientas de búsqueda/listening para agentes

| Herramienta | MCP | Precio | Apunte |
|---|---|---|---|
| Apify | ✅ mcp.apify.com (6.000+ actors) | Free $5/mes; PAYG | La pieza clave si se añade X/LinkedIn |
| Bright Data | ✅ Web MCP | Free 5.000 req/mes | Buen backup gratuito |
| Exa.ai | ✅ | Free 1.000 créditos; $49/mes Core | Búsqueda semántica + Websets (listas estructuradas verificadas); los VCs la usan para deal sourcing |
| Tavily | ✅ | Free 1.000 créditos/mes | Redundante con Firecrawl + grounding |
| Perplexity Sonar | REST | $5/1k requests | Solapa con Vertex grounding |
| Firecrawl (contratado) | ✅ | /search = 2 créditos/10 resultados | Caballo de batalla para fuentes españolas |

## 7. Stack recomendado por capas (≈$20–60/mes si se activa todo)

1. **BORME** (`bormeparser`, 0€) — constituciones gallegas diarias; requiere
   monitorización continua. Ventaja real: nadie más mira ahí.
2. **Prensa + directorios ES vía Firecrawl** (ya pagado) — ✅ **implementado** (`spain_source`).
3. **LinkedIn vía Apify** (~$5–20/mes) — post-search por keywords; anuncios de fundadores.
4. **X vía twitterapi.io o socialdata.tools** (~$5–15/mes) — "build in public" español.
5. **Exa.ai Websets** (free → $49/mes) — capa semántica "startups parecidas a X".

Fuera: API oficial de X, Crunchbase/Dealroom/PitchBook/Harmonic, PhantomBuster,
Nitter, Reddit como fuente principal.

## No verificado
- Precios exactos de LibreBOR (403 a fetchers; mirar librebor.me/productos/api a mano).
- Si OpenVC tiene API (es directorio de inversores, no de startups).
- Precios de Specter/Tracxn (no públicos).
- Los precios de actors de Apify varían por actor; confirmar antes de integrar.
