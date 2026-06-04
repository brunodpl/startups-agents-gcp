# Arquitectura — Diagnóstico 360º de Startups (v2)

Documento de apoyo técnico. Acompaña al [README](../README.md) (pitch + guion).
Aquí va el *cómo* y el *por qué*.

## 1. Visión

Pipeline **multi-agente** que, dada una **tesis de inversión**, descubre startups
en fuentes públicas, las analiza y entrega una **shortlist diagnosticada** con
experimentos Lean priorizados, citando los frameworks de evaluación. Sobre
**Google ADK** + **Vertex AI** (Gemini 2.5), desplegado en **Cloud Run**.

## 2. El pipeline (4 etapas)

```
1. Discovery   (sourcing)   tesis -> shortlist cruda (top N)
2. Analysis    (en paralelo) por candidata: research · business · metrics · market
3. Diagnosis   (synthesizer, gemini-2.5-pro) juicio grounded en frameworks + citas
4. Presentation(reporting)  informe rankeado (JSON + legible) -> URL Cloud Run
```

| Etapa | Agente(s) | Modelo | Entrada | Salida | Tools |
|---|---|---|---|---|---|
| Discovery | discovery_agent | Flash | tesis | shortlist cruda | fuente API pública (F2) |
| Analysis | research / business_model / metrics / market | Flash | candidata | señales por dimensión | `fetch_url` (research) |
| Diagnosis | synthesizer | **Pro** | análisis + frameworks | juicio estructurado + citas | — |
| Presentation | reporting | Flash | diagnósticos | informe rankeado | — |

**Orquestación:** `SequentialAgent` para las 4 etapas; dentro de Analysis, un
`ParallelAgent` (o fan-out) por candidata y por dimensión. El paso de datos entre
agentes es vía el **`state` de la sesión ADK** (`output_key` para escribir, y
`{clave}` en el `instruction` del siguiente para leer).

**Por qué Flash + Pro:** Flash (barato/rápido) para sourcing y extracción; Pro
solo para la síntesis del diagnóstico, donde la calidad del razonamiento importa.

## 3. Discovery (sourcing real, sin reconstruir Harmonic)

- Input: tesis `{sector, stage, geografía, señales}`.
- Consulta 1-2 **fuentes públicas con API gratis**, normaliza el esquema,
  deduplica y **puntúa** cada candidata contra la tesis → shortlist.
- **Cumplimiento:** respeta `robots.txt` y ToS; nada de scrapear LinkedIn/Crunchbase;
  GDPR-aware con datos de founders (minimizar/evitar PII).
- Demo: 1 fuente en F2, 2ª fuente en F4.

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

1. **Paso individual** — aísla cada agente: ¿salida correcta dado un input fijo?
2. **Trayectoria** — la secuencia completa de decisiones de principio a fin.
3. **Llamada a herramientas** — tool correcta + argumentos correctos.
4. **Salida final** — diagnóstico correcto y **citas de frameworks reales**.

Dataset de regresión (3-5 startups conocidas con criterios esperados) en
`evals/datasets/`; `python -m evals.run` → informe por nivel + fallos.

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
