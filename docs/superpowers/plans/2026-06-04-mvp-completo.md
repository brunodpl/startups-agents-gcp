# MVP completo — Discovery & Diagnóstico de Startups · Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completar el pipeline de 4 fases (Discovery → Analysis → Diagnosis → Presentation) y desplegarlo en Cloud Run con una URL que, dada una tesis, devuelva una shortlist diagnosticada con citas, listo para hacer pruebas.

**Architecture:** ADK `SequentialAgent` que encadena las 4 fases; Analysis corre 4 sub-agentes por candidata; Diagnosis (gemini-2.5-pro) razona con los frameworks de `knowledge/*.md` inyectados en contexto (NO RAG) y cita fuentes; el estado de la sesión (`output_key`) pasa datos entre fases. Despliegue en Cloud Run, scale-to-zero, región EU.

**Tech Stack:** Python 3.13 · uv · Google ADK (`google-adk` 1.32) · Vertex AI (Gemini 2.5 Flash/Pro vía `aiplatform.googleapis.com`) · Firecrawl (`fetch_url`) · YC OSS API (Discovery) · pydantic (esquemas) · pytest.

**Modelo de trabajo:** 👤 = lo escribes tú y yo corrijo · 🤖 = lo scaffoldeo yo. Cada fase termina con: resumen + sintaxis nueva + mini-reto.

**Skills de apoyo:** @superpowers:test-driven-development · @google-agents-cli-adk-code · @consuming-gcp-credits · @superpowers:executing-plans

**Restricciones (no negociables):**
- Conocimiento EN CONTEXTO (no RAG / no Discovery Engine). Solo crédito **Marketing** (Vertex + Cloud Run).
- LLM siempre por Vertex (`GOOGLE_GENAI_USE_VERTEXAI=True`). Nunca `google.generativeai` / `GOOGLE_API_KEY`.
- Deps del contenedor en **`agents/requirements.txt`** (no el pyproject).
- En Windows, ejecutar todo como módulo: `uv run python -m ...` (WDAC bloquea los `.exe` de `.venv`).
- Scale-to-zero, EU (`europe-west1`), GDPR-aware; Discovery solo fuentes públicas y ToS.
- Secretos en `.env` (gitignored) y `--update-env-vars` al desplegar.

---

## Estructura de archivos (qué se crea/toca)

| Archivo | Responsabilidad | Estado |
|---|---|---|
| `agents/schemas.py` | Modelos pydantic: `Thesis`, `Candidate`, `Shortlist`, `CandidateAnalysis`, `Diagnosis`, `Report` | crear |
| `agents/tools/yc_source.py` | Tool: consulta YC OSS API y normaliza candidatas | crear |
| `agents/sub_agents/discovery.py` | `discovery_agent` (Flash): tesis → shortlist puntuada | crear |
| `agents/knowledge.py` | `load_frameworks()`: lee `knowledge/*.md` → string para el `instruction` | crear |
| `agents/sub_agents/business_model.py` · `metrics.py` · `market.py` | Analistas (Flash) por dimensión | crear |
| `agents/sub_agents/diagnosis.py` | `synthesizer_agent` (Pro): veredicto con citas | crear |
| `agents/sub_agents/reporting.py` | `reporting_agent` (Flash): informe rankeado | crear |
| `agents/pipeline.py` | Arma el `SequentialAgent` + la iteración por candidata de Analysis | crear |
| `agents/agent.py` | `root_agent` = pipeline completo | modificar |
| `agents/prompts.py` | Instrucciones de cada agente nuevo | modificar |
| `agents/config.py` | `TOP_N`, claves de fuentes, etc. | modificar |
| `agents/requirements.txt` | + `httpx` (y `pydantic` si hace falta) | modificar |
| `evals/run.py` · `evals/levels.py` · `evals/datasets/regression.jsonl` | Harness de 4 niveles + dataset | crear |
| `tests/test_*.py` | Unit tests de helpers deterministas + smoke de wiring | crear |

> **Decisión de diseño clave (F3):** la iteración "4 analistas × N candidatas" se resuelve con un agente personalizado en `pipeline.py` (ver Tarea 3.4). Riesgo medio → hay un *fallback* más simple documentado.

---

## FASE F2 — Discovery (tesis → shortlist cruda)

### Tarea 2.1 — Esquemas base (`schemas.py`) 🤖
**Files:** Create `agents/schemas.py` · Test `tests/test_schemas.py`

- [ ] **Paso 1 — Test que falla:** validar que `Thesis` y `Candidate` aceptan los campos esperados.
```python
# tests/test_schemas.py
from agents.schemas import Thesis, Candidate

def test_thesis_minimal():
    t = Thesis(sector="AI dev tools", stage="early", geography="global", signals=["tracción"])
    assert t.sector == "AI dev tools"

def test_candidate_from_yc():
    c = Candidate(name="X", website="https://x.com", one_liner="y", source="yc")
    assert c.score is None  # score se rellena en Discovery
```
- [ ] **Paso 2 — Correr y ver fallar:** `uv run python -m pytest tests/test_schemas.py -q` → FAIL (ImportError).
- [ ] **Paso 3 — Implementar** `agents/schemas.py` con pydantic: `Thesis(sector, stage, geography, signals: list[str])`, `Candidate(name, website, one_liner, industries=[], regions=[], stage=None, source, score: float|None=None, rationale=None)`, `Shortlist(thesis, candidates: list[Candidate])`. (Analysis/Diagnosis/Report se añaden en F3/F4.)
- [ ] **Paso 4 — Pasar:** `uv run python -m pytest tests/test_schemas.py -q` → PASS.
- [ ] **Paso 5 — Commit:** `feat(F2): pydantic schemas (Thesis, Candidate, Shortlist)`

### Tarea 2.2 — Tool de la fuente YC OSS (`yc_source.py`) 👤 (tú la escribes, yo corrijo)
**Files:** Create `agents/tools/yc_source.py` · Test `tests/test_yc_source.py`

- [ ] **Paso 1 — Test con fixture (determinista):** dado un JSON de ejemplo de YC, `normalize_company(raw)` devuelve un dict con `name, website, one_liner, industries, regions, stage`.
- [ ] **Paso 2 — Ver fallar.**
- [ ] **Paso 3 — Implementar** `def search_startups(sector: str, region: str | None = None, limit: int = 20) -> list[dict]`:
  - Descarga con `httpx` el endpoint filtrado de YC OSS (p. ej. `https://yc-oss.github.io/api/tags/<slug>.json`); si no hay slug, cae a `companies/all.json`.
  - Normaliza cada empresa a `{name, website, one_liner, industries, regions, stage, batch}`.
  - Filtra por `region` si se pasa; recorta a `limit`. Manejo de errores explícito (try/except → lista vacía + log).
  - Docstring claro (es prompt para el LLM): "Busca startups candidatas en YC por sector/región…".
- [ ] **Paso 4 — Pasar test** (fixture local, sin red) + 1 prueba manual real: `uv run python -c "from agents.tools.yc_source import search_startups; print(len(search_startups('artificial-intelligence', limit=5)))"`.
- [ ] **Paso 5 — Commit:** `feat(F2): yc_source tool (YC OSS API)`
- [ ] **Paso 6 — Añadir `httpx` a `agents/requirements.txt`** (deps del contenedor) y a `pyproject` (`uv add httpx`). Commit.

### Tarea 2.3 — DiscoveryAgent (`discovery.py` + prompt) 👤
**Files:** Create `agents/sub_agents/discovery.py` · Modify `agents/prompts.py`

- [ ] **Paso 1 — Prompt** `DISCOVERY_INSTRUCTION` en `prompts.py`: recibe una tesis (texto), llama a `search_startups` con sector/región, y **puntúa** cada candidata 0-1 contra la tesis explicando el porqué; devuelve las **top N** (ver `TOP_N`). Sin inventar (solo lo que devuelva la tool).
- [ ] **Paso 2 — Agente** `discovery_agent = Agent(model=Settings.MODEL_FLASH, name="discovery_agent", instruction=DISCOVERY_INSTRUCTION, tools=[search_startups], output_key="shortlist")`.
- [ ] **Paso 3 — `config.py`:** añadir `TOP_N = int(os.getenv("TOP_N", "3"))` y `DISCOVERY_SECTOR_DEFAULT` (placeholder).
- [ ] **Paso 4 — root temporal:** en `agent.py`, `root_agent = discovery_agent` (para probar F2 aislada).
- [ ] **Paso 5 — Smoke + prueba real** (Runner) con una tesis de ejemplo → imprime shortlist. `uv run python -m pytest -q` debe seguir verde.
- [ ] **Paso 6 — Commit:** `feat(F2): DiscoveryAgent (thesis -> scored shortlist)`

### Tarea 2.4 — Deploy de verificación F2 🤖
- [ ] Redesplegar (`agents/requirements.txt` ya con httpx+firecrawl) y comprobar `/run` 200 con una tesis. Commit del estado.

**Cierre F2:** resumen · sintaxis nueva (pydantic, `output_key`, `httpx`) · mini-reto.

---

## FASE F3 — Analysis + Diagnosis (con frameworks y citas)

### Tarea 3.0 — Rewire del ResearchAgent existente para el pipeline 👤
**Files:** Modify `agents/sub_agents/research.py`, `agents/prompts.py`

> ⚠️ El `research_agent` actual espera la URL como **mensaje del usuario** y NO tiene `output_key`. Dentro de Analysis debe (a) leer la web de la candidata desde `state["current_candidate"]` y (b) escribir su salida en `output_key="research"` para que business/metrics/market puedan leer `{research}`.

- [ ] **Paso 1** — Añadir `output_key="research"` al `research_agent`.
- [ ] **Paso 2** — Actualizar `RESEARCH_INSTRUCTION`: en vez de pedir la URL al usuario, leer la `website` de `{current_candidate}` (inyectada desde state) y llamar a `fetch_url` con ella.
- [ ] **Paso 3** — Smoke verde (`uv run python -m pytest -q`). Commit: `refactor(F3): wire research_agent into pipeline (state in/out)`.

### Tarea 3.1 — Loader de conocimiento (`knowledge.py`) 👤
**Files:** Create `agents/knowledge.py` · Test `tests/test_knowledge.py`

- [ ] **Paso 1 — Test:** crear 2 `.md` temporales y verificar que `load_frameworks(dir)` concatena ambos con sus títulos.
- [ ] **Paso 2 — Ver fallar.**
- [ ] **Paso 3 — Implementar** `load_frameworks() -> str` con `Path(__file__).parent.parent / "knowledge"` + `.glob("*.md")` ordenado, concatenando `# Framework: <stem>` + contenido. Manejo de carpeta vacía.
- [ ] **Paso 4 — Pasar test.**
- [ ] **Paso 5 — Commit:** `feat(F3): knowledge loader (in-context frameworks)`

### Tarea 3.2 — Analistas Business/Metrics/Market (3 agentes) 👤
**Files:** Create `agents/sub_agents/business_model.py`, `metrics.py`, `market.py` · Modify `prompts.py`

- [ ] **Paso 1 — Prompts** (3): cada uno recibe el resumen del ResearchAgent (de state `{research}`) y la candidata; devuelve su dimensión. `BUSINESS_MODEL`, `METRICS`, `MARKET`.
- [ ] **Paso 2 — Agentes** (Flash), cada uno con su `output_key` (`business`, `metrics`, `market`). Sin tools (leen de state).
- [ ] **Paso 3 — Smoke** (import + wiring). `uv run python -m pytest -q` verde.
- [ ] **Paso 4 — Commit:** `feat(F3): analysis sub-agents (business/metrics/market)`

### Tarea 3.3 — SynthesizerAgent / Diagnosis (`diagnosis.py`) 👤
**Files:** Create `agents/sub_agents/diagnosis.py` · Modify `prompts.py`

- [ ] **Paso 1 — Prompt** `DIAGNOSIS_INSTRUCTION`: recibe research+business+metrics+market de state; produce veredicto estructurado (fortalezas, riesgos, palancas, fit con tesis, experimentos Lean priorizados); **OBLIGATORIO citar** el framework de cada conclusión. Los frameworks se inyectan con `load_frameworks()` (concatenados al instruction al construir el agente).
- [ ] **Paso 2 — Agente** `synthesizer_agent = Agent(model=Settings.MODEL_PRO, ..., instruction=DIAGNOSIS_INSTRUCTION + "\n\n" + load_frameworks(), output_key="diagnosis")`.
- [ ] **Paso 3 — Smoke** verde.
- [ ] **Paso 4 — Commit:** `feat(F3): SynthesizerAgent (Pro, grounded + citations)`

### Tarea 3.4 — Pipeline + iteración por candidata (`pipeline.py`) 🤖 (la parte más delicada)
**Files:** Create `agents/pipeline.py` · Modify `agents/agent.py`

- [ ] **Paso 1 — Diseño:** `Analysis = ParallelAgent([research, business_model, metrics, market])`. Para iterar las N candidatas de la shortlist, crear un `BaseAgent` personalizado `PerCandidateAnalysis` que, por cada candidata en `state["shortlist"]`, fija `state["current_candidate"]`, ejecuta el `ParallelAgent` y acumula en `state["analyses"]`.
  - ⚠️ **El state se serializa a JSON:** guarda `current_candidate` como `dict` (`candidate.model_dump()`), **parsea la `shortlist`** que dejó Discovery (puede venir como objeto/JSON, no como lista de `Candidate`), y acumula `analyses` como **lista de dicts**.
- [ ] **Paso 2 — Pipeline:** `root = SequentialAgent([discovery_agent, PerCandidateAnalysis(...), synthesizer_agent])` (reporting se añade en F4).
- [ ] **Paso 3 — `agent.py`:** `root_agent = build_pipeline()`.
- [ ] **Paso 4 — Prueba real (Runner)** con tesis de ejemplo → veredicto del top 1-3 con citas. Verificar trayectoria (Discovery → Analysis ×N → Diagnosis).
- [ ] **Paso 5 — Commit:** `feat(F3): 4-stage pipeline with per-candidate analysis`
- [ ] **FALLBACK si la iteración da problemas (deadline):** procesar las N candidatas en un solo paso por dimensión (cada analista recibe la lista y devuelve análisis por candidata). Documentar el recorte con `log()`.

**Cierre F3:** resumen · sintaxis nueva (`ParallelAgent`, `SequentialAgent`, `BaseAgent` custom, state `output_key`/lectura `{clave}`) · mini-reto.

---

## FASE F4 — Presentation + 2ª fuente

### Tarea 4.1 — ReportingAgent (`reporting.py`) 👤
**Files:** Create `agents/sub_agents/reporting.py` · Modify `prompts.py` · `schemas.py` (Report)

- [ ] **Paso 1 — `Report` schema** (pydantic): ranking de candidatas con `{name, score, fortalezas, riesgos, palancas, experimentos, citas}`.
- [ ] **Paso 2 — Prompt** `REPORTING_INSTRUCTION`: toma los diagnósticos y produce **JSON estructurado + resumen legible rankeado** (top 3).
- [ ] **Paso 3 — Agente** (Flash), `output_key="report"`; añadirlo al final del `SequentialAgent`.
- [ ] **Paso 4 — Prueba real** end-to-end (tesis → informe rankeado). Commit: `feat(F4): ReportingAgent (ranked report)`

### Tarea 4.2 — 2ª fuente de Discovery 👤 (opcional si aprieta el deadline)
**Files:** Create `agents/tools/ph_source.py` (Product Hunt o GitHub) · Modify `discovery.py`

- [ ] Tool de 2ª fuente (con key en `.env` si aplica), normalizada al mismo esquema; Discovery consulta ambas y **deduplica** por dominio. Test de dedup. Commit: `feat(F4): second discovery source + dedupe`.

**Cierre F4:** resumen · sintaxis nueva · mini-reto.

---

## FASE F5 — Evals + docs

### Tarea 5.1 — Dataset de regresión 🤖
**Files:** Create `evals/datasets/regression.jsonl`

- [ ] 3-5 startups conocidas con criterios esperados (qué debería detectar el diagnóstico). Commit.

### Tarea 5.2 — Harness de 4 niveles (`evals/run.py`, `levels.py`) 🤖 (tú revisas)
**Files:** Create `evals/levels.py`, modify `evals/run.py`

- [ ] **Nivel 1 (paso):** por agente, input fijo → assert sobre la salida (campos presentes / no error).
- [ ] **Nivel 2 (trayectoria):** la corrida pasa por Discovery→Analysis→Diagnosis→Reporting en orden.
- [ ] **Nivel 3 (tools):** se llamó `search_startups`/`fetch_url` con argumentos válidos (la URL de `fetch_url` debe venir de la candidata en state, no hardcodeada → valida el flujo de F3).
- [ ] **Nivel 4 (final):** el informe cita frameworks reales (presentes en `knowledge/`) y cubre los criterios esperados del dataset (LLM-as-judge sencillo).
- [ ] `python -m evals.run` imprime informe por nivel + fallos. Commit: `feat(F5): 4-level eval harness + regression dataset`.

### Tarea 5.3 — Docs + guion 🤖
- [ ] Actualizar README (estado F2-F5 ✅), `docs/architecture.md`, y sincronizar Notion. Guion de demo 2 min. Commit.

**Cierre F5:** resumen · sintaxis nueva · mini-reto.

---

## Deploy final + smoke

### Tarea D.1 — Despliegue MVP a Cloud Run 🤖
- [ ] Confirmar `agents/requirements.txt` con TODAS las deps (`google-adk`, `firecrawl-py`, `python-dotenv`, `httpx`, `pydantic`).
- [ ] `uv run python -m google.adk.cli deploy cloud_run --project=your-gcp-project --region=europe-west1 --service_name=startup-diagnostics --with_ui agents -- --allow-unauthenticated --update-env-vars=FIRECRAWL_API_KEY=...` (+ key de 2ª fuente si aplica).
- [ ] **Smoke en vivo:** crear sesión + `/run` con la tesis de ejemplo → 200 + informe con citas. Verificar latencia/logs.
- [ ] Pegar la URL en README + Notion. Commit final: `chore: deploy MVP to Cloud Run`.

---

## Orden y dependencias
F2 → F3 → F4 → F5 → Deploy. Cada fase es desplegable/desmostrable por sí sola. Riesgo principal: Tarea 3.4 (iteración por candidata) — tiene fallback. Coste: Vertex (Flash barato, Pro solo en Diagnosis) + Firecrawl (créditos) + Cloud Run (scale-to-zero) — todo dentro del crédito Marketing salvo Firecrawl.
