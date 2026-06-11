# Arquitectura — Diagnóstico 360º de Startups (v2)

Documento de apoyo técnico. Acompaña al [README](../README.md) (pitch + guion).
Aquí va el *cómo* y el *por qué*.

## 1. Visión

Pipeline **multi-agente** que, dada una **tesis de inversión**, descubre startups
en fuentes públicas, las analiza y entrega una **shortlist diagnosticada** con
experimentos Lean priorizados, citando los frameworks de evaluación. Sobre
**Google ADK** + **Vertex AI** (Gemini 3), desplegado en **Cloud Run**.

## 2. El pipeline (4 etapas)

```
1. Discovery   (sourcing)   tesis -> shortlist cualificada (gate binario)
2. Analysis    (en paralelo) por candidata: research · business · metrics · market
3. Diagnosis   (synthesizer, gemini-3.1-pro-preview) juicio grounded en frameworks + citas
4. Presentation(reporting)  informe rankeado (JSON + legible) -> URL Cloud Run
```

| Etapa | Agente(s) | Modelo | Entrada | Salida | Tools |
|---|---|---|---|---|---|
| Discovery | discovery_agent | Flash | tesis | shortlist cualificada (`state["shortlist"]`) | `find_candidates` (grounded · spain · YC · GitHub) |
| Analysis | research / business_model / metrics / market | Flash | candidata | señales por dimensión | `fetch_url` (research) |
| Diagnosis | synthesizer | **Pro** | análisis + frameworks | juicio estructurado + citas | — |
| Presentation | reporting | Flash | diagnósticos (`state["analyses"]`) | informe rankeado | — |

**Orquestación** (`agents/pipeline.py`): el root es un `SequentialAgent`
= `[discovery_agent, PerCandidateAnalysis, reporting_agent]`.

- `PerCandidateAnalysis` es un **`BaseAgent` custom**: parsea `state["shortlist"]`
  (JSON que dejó Discovery, posiblemente con fences ```), e itera las
  cualificadas (hasta `MAX_CANDIDATES`). Por
  cada candidata fija `state["current_candidate"]` (+ `state["thesis"]`), corre el
  sub-pipeline de análisis y la síntesis, y **acumula** un diagnóstico por
  candidata en `state["analyses"]` (lista de dicts, JSON-serializable).
- **Persistencia del estado por candidata:** además de mutar el dict vivo (lo
  que ven los sub-agentes), el loop emite un **evento con `state_delta`** por
  cada escritura (selección de candidata, veredicto del guard, y un
  **checkpoint de `analyses` tras cada candidata**). Las sesiones persistidas
  (Agent Engine, `SESSION_SERVICE_URI`) se reconstruyen SOLO desde deltas, así
  que sin esto el estado intermedio sería invisible para replay/evals; y si la
  corrida muere a mitad, las candidatas ya completadas quedan en la sesión.
- El sub-pipeline de análisis es `SequentialAgent([research, ParallelAgent([
  business, metrics, market])])`: **research primero** (escribe `state["research"]`)
  y luego los 3 analistas **en paralelo**, porque leen `{research}`. (El plan
  original los ponía a los 4 en un solo `ParallelAgent`; se corrigió por esta
  dependencia de datos. La síntesis corre **por candidata**, no una sola vez.)

El paso de datos es vía el **`state` de la sesión ADK** (`output_key` para
escribir; `{clave}` en el `instruction` del siguiente para leer). ⚠️ ADK sólo
sustituye `{identificador}` válidos contra `state`; los ejemplos JSON con claves
entrecomilladas (`{"name": ...}`) se dejan intactos.

**Por qué Flash + Pro:** Flash (barato/rápido) para sourcing y extracción; Pro
solo para la síntesis del diagnóstico, donde la calidad del razonamiento importa.

## 3. Discovery (sourcing real, sin reconstruir Harmonic)

- Input: tesis `{sector, stage, geografía, señales}` (texto del usuario).
- `find_candidates` consulta **4 fuentes** — `grounded_source` (Gemini + Google
  Search vía Vertex), `spain_source` (prensa/directorios españoles vía
  Firecrawl), `yc_source` (YC OSS) y `gh_source` (GitHub) — **en paralelo**
  (`ThreadPoolExecutor`: cada fuente es I/O bloqueante independiente y ya traga
  sus propios fallos), normaliza al mismo esquema, **interleava** y **deduplica
  por dominio** (gana grounded, luego spain). El LLM aplica un **gate binario**
  (sector AND geografía AND señales) y se queda con las que cualifican (hasta
  `MAX_CANDIDATES`).
- **Cumplimiento:** respeta `robots.txt` y ToS; nada de scrapear LinkedIn/Crunchbase;
  GDPR-aware con datos de founders (minimizar/evitar PII).
- Demo: YC en F2, GitHub añadida en F4 (con dedupe).

## 4. Conocimiento EN CONTEXTO (decisión cerrada — no RAG)

- Frameworks en `knowledge/*.md` (rúbrica de evaluación, Lean & growth).
- Helper `agents/knowledge.py` (F3): `Path("knowledge").glob("*.md")` → leer →
  concatenar → **inyectar en el `instruction`** de Diagnosis (y Analysis si aplica).
- **Sin** vector DB, embeddings, Vertex AI Search ni Skills. Migrar a Vertex AI
  Search SOLO si el corpus crece (fase futura, fuera de esta demo).
- **Auditabilidad por prompting:** cada conclusión cita su framework de origen.

## 5. Routing de créditos GCP

| Servicio | API | Crédito | En esta demo |
|---|---|---|---|
| Gemini / agentes | `aiplatform.googleapis.com` | Marketing (433,58 €, caduca 2026-06-25) | ✅ |
| Cloud Run | `run.googleapis.com` | Marketing | ✅ |
| Cloud Storage | `storage.googleapis.com` | Marketing | (si hace falta) |
| Discovery Engine | `discoveryengine.googleapis.com` | GenAI App Builder | ❌ no (no RAG) |

Garantías en código:
- `GOOGLE_GENAI_USE_VERTEXAI=True` vía `os.environ.setdefault` en `agents/agent.py`
  (antes de importar `google.adk`), para que funcione en Cloud Run sin `.env`.
- Nunca `google.generativeai` / `GOOGLE_API_KEY` (free tier).

## 6. Despliegue

- **Target: Cloud Run** (no Agent Runtime, no Cloud Functions/App Engine).
- `adk deploy cloud_run ... --with_ui agents -- --allow-unauthenticated`.
- **Scale-to-zero**; región `europe-west1` (EU/GDPR); `--with_ui` = URL clicable.

### ⚠️ Dependencias del contenedor
`adk deploy cloud_run` instala desde **`agents/requirements.txt`** (en la carpeta
del agente), **NO** desde `pyproject.toml`. Todo paquete que el agente importe en
runtime debe listarse ahí, o el contenedor arranca pero `/run` devuelve **500
`ModuleNotFoundError`** (el agente se carga en la primera petición, no al boot).

### Nota de entorno (Windows / WDAC)
Windows Application Control bloquea los `.exe` de `.venv\Scripts` (`adk.exe`,
`pytest.exe`). Workaround universal: `uv run python -m <módulo>`. No afecta al
contenedor Cloud Run (Linux).

## 7. Harness de evals (F5)

Una sola corrida del pipeline (`RunCapture`: authors + tool_calls + state) se
evalúa en 4 niveles (`evals/levels.py`, funciones puras → testeables offline):

1. **Paso individual** — cada etapa produjo salida no vacía (`shortlist`,
   `analyses[*].{research,business,metrics,market,diagnosis}`, `report`), sin errores.
2. **Trayectoria** — orden discovery → research → analistas → synthesizer → reporting.
3. **Llamada a herramientas** — `find_candidates` se llamó con `sector`; y cada
   URL de `fetch_url` **pertenece al dominio de una candidata en `state`** (no
   hardcodeada) → valida que research lee la web desde el estado (flujo F3).
4. **Salida final** — el informe cita frameworks reales de `knowledge/` y un
   **LLM-judge** (Flash sobre Vertex) puntúa la cobertura de criterios esperados
   (umbral 70 %).

Dataset de regresión (`evals/datasets/regression.jsonl`: 4 tesis con criterios
esperados); `python -m evals.run [--all]` → informe por nivel + fallos.

## 8. Logging / observabilidad

Logging estructurado: qué agente actuó, qué tools llamó, latencia
(`google-cloud-logging` + `--trace_to_cloud` en el deploy, desde F3).

## 9. Decisiones de diseño (v2)

| Decisión | Elección | Motivo |
|---|---|---|
| Conocimiento | frameworks en contexto (no RAG) | corpus pequeño/estático; menos infra; cero coste de Discovery Engine |
| Input | tesis de inversión | el servicio de Tales Venture parte de una tesis, no de 1 startup |
| Discovery | API públicas gratis | sourcing real sin reconstruir Harmonic; legal/GDPR-aware |
| Orquestación | Sequential (etapas) + Parallel (Analysis) | dependencias claras + paralelizar por candidata |
| Modelos | Flash (sourcing/análisis) + Pro (diagnóstico) | coste/calidad |
| Deploy | Cloud Run + scale-to-zero | crédito Marketing, sin coste en reposo |
| Región | `europe-west1` | EU / GDPR |
| Python / pkgs | 3.13 / uv | ya instalado; lock reproducible |
| Ejecución | **síncrona**: todo el pipeline dentro de una petición HTTP (`--timeout=900`) | demo: simple, una URL clicable; mitigado con checkpoints de `analyses` por candidata |

## 10. Triggers de v3 (si esto deja de ser una demo)

Igual que el conocimiento tiene su salida documentada (corpus crece → Vertex AI
Search), estos son los límites aceptados de la demo y su salida:

| Límite aceptado hoy | Trigger | Salida |
|---|---|---|
| Ejecución síncrona en una petición (cap real: `MAX_CANDIDATES` × `--timeout`) | corridas > ~8 candidatas o clientes que no esperan minutos | modelo async/job: Cloud Run Jobs o Cloud Tasks + polling de sesión (el smoke test ya hace fire-and-poll) |
| Candidatas en serie (claves de estado compartidas: `current_candidate`, `research`, …) | la latencia por corrida importa | namespacing de claves por candidata (`research:{i}`) → desbloquea paralelizar el loop |
| `--allow-unauthenticated`, sin rate-limit | cualquier uso más allá del evento | IAM/IAP delante del servicio + atribución de coste por corrida |
| Ranking del informe lo emite el LLM (no determinista) | clientes comparan corridas entre sí | rúbrica de scoring en código (el LLM puntúa criterios; el código ordena) |
