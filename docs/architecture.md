# Arquitectura — Diagnóstico 360º de Startups

Documento de apoyo técnico. Acompaña al [README](../README.md) (pitch + guion de
demo). Aquí va el *cómo* y el *por qué*.

## 1. Visión

Sistema **multi-agente** que, dada la URL de una startup, produce un diagnóstico
360º (modelo de negocio, métricas, palancas de crecimiento, experimentos Lean).
Construido con **Google ADK** (orquestación) sobre **Vertex AI** (Gemini 2.5),
desplegado en **Cloud Run**, con **RAG** vía Vertex AI Search y un **harness de
evals** de 4 niveles.

## 2. El pipeline de agentes

```
Orchestrator (SequentialAgent)
  1. ResearchAgent      (LlmAgent + tool fetch_url)   → resumen de la startup
  2. BusinessModelAgent (LlmAgent)                    → propuesta valor, segmento, monetización
  3. MetricsAgent       (LlmAgent)                    → métricas clave, señales de unit economics
  4. GrowthLeversAgent  (LlmAgent + VertexAiSearchTool) → palancas ocultas (grounded)
  5. SynthesizerAgent   (LlmAgent, gemini-2.5-pro)    → informe 360º final
```

| Agente | Modelo | Entrada | Salida | Tools |
|---|---|---|---|---|
| Research | Flash | URL (+ datos opcionales) | resumen estructurado | `fetch_url` (F2) |
| BusinessModel | Flash | resumen | propuesta de valor, segmento, monetización | — |
| Metrics | Flash | resumen + modelo | métricas estimadas + unit economics | — |
| GrowthLevers | Flash | todo lo anterior | palancas de crecimiento + citas | `vertex_search` (F4) |
| Synthesizer | **Pro** | todo el estado | informe 360º (JSON + texto) | — |

**Por qué `SequentialAgent`:** el diagnóstico es un pipeline lineal con
dependencias claras (no puedes leer métricas sin entender antes el modelo de
negocio). Cada sub-agente escribe su resultado en el `state` de la sesión ADK y
el siguiente lo lee. Mínima complejidad, máxima trazabilidad.

**Por qué Flash + Pro:** Flash es barato y rápido para extracción/clasificación
(la mayor parte del trabajo). Pro se reserva para la síntesis final, donde la
calidad del razonamiento marca la diferencia del informe que ve el cliente.

## 3. RAG / grounding (F4)

- **Corpus** (`rag/corpus/`): Lean Startup, playbooks de growth, notas de
  benchmark. Pequeño y curado.
- **Ingesta** (`rag/ingest.py`): sube el corpus a **Cloud Storage**
  (`storage.googleapis.com`) y crea/indexa un datastore de **Vertex AI Search /
  Discovery Engine** (`discoveryengine.googleapis.com`).
- **Consulta**: `GrowthLeversAgent` usa `VertexAiSearchTool` para fundamentar las
  palancas en frameworks reales y **citar fuentes**.

## 4. Routing de créditos GCP (crítico)

Dos créditos promocionales en el proyecto `your-gcp-project`:

| Servicio | API | Crédito |
|---|---|---|
| Gemini / agentes | `aiplatform.googleapis.com` | Marketing (433,58 €, caduca 2026-06-25) |
| Cloud Run | `run.googleapis.com` | Marketing |
| Cloud Storage | `storage.googleapis.com` | Marketing |
| Discovery Engine | `discoveryengine.googleapis.com` | GenAI App Builder (848,21 €) |

Garantías en código:
- `GOOGLE_GENAI_USE_VERTEXAI=True` se fija **antes** de importar `google.adk`
  (en `agents/agent.py`), con `os.environ.setdefault`, para que funcione también
  en Cloud Run sin `.env`.
- Nunca `google.generativeai` / `GOOGLE_API_KEY` (free tier, no consume crédito).
- Para llamadas directas a Gemini (fuera de ADK), usar el SDK de Vertex
  (`vertexai`) o `google.genai.Client(vertexai=True, ...)`, no el paquete de
  free-tier.

## 5. Despliegue

- **Target: Cloud Run** (no Agent Runtime, no Cloud Functions, no App Engine —
  solo Cloud Run está en el crédito Marketing).
- Comando: `adk deploy cloud_run ... --with_ui agents -- --allow-unauthenticated`.
- **Scale-to-zero** (sin `min-instances`): no hay coste en reposo.
- **Región `europe-west1`** (EU) por GDPR.
- `--with_ui` despliega la interfaz de chat de ADK → URL clicable para la demo.
- El endpoint es **público** (`--allow-unauthenticated`): aceptable para una demo
  sobre proyecto personal; en producción se restringiría.

### Nota de entorno (Windows / WDAC)

En la máquina de desarrollo, **Windows Application Control bloquea los `.exe` de
`.venv\Scripts`** (`adk.exe`, `pytest.exe`, …). Workaround universal: invocar
como módulo de Python — `uv run python -m google.adk.cli ...`,
`uv run python -m pytest`. Esto **no** afecta al contenedor de Cloud Run (Linux).

## 6. Harness de evals (F5)

Cuatro niveles de evaluación, cada uno responde a una pregunta distinta:

1. **Paso individual** — aísla cada sub-agente y comprueba que su salida es
   correcta dado un input fijo. (¿Falla el agente X o el pipeline?)
2. **Trayectoria** — evalúa la secuencia completa de decisiones de principio a
   fin. (¿El orden y el paso de estado son correctos?)
3. **Llamada a herramientas** — verifica que se llama a la tool correcta con los
   argumentos correctos (p. ej. `fetch_url(url=...)`, `vertex_search(query=...)`).
4. **Salida final** — juzga el diagnóstico completo: corrección y que **cite
   fuentes reales** (no alucinadas).

- **Dataset de regresión**: 3-5 startups conocidas con criterios de diagnóstico
  esperados (`evals/datasets/`).
- **Comando**: `python -m evals.run` → informe con métricas por nivel y los
  fallos concretos.
- Se apoya en la evaluación nativa de ADK (`google-adk[eval]`, `pytest`) más
  lógica custom para los 4 niveles.

## 7. Observabilidad / logging

Requisito funcional: registrar **qué agente actuó, qué tools llamó y la
latencia**. Se habilitará con `--trace_to_cloud` (Cloud Trace) en el deploy y
`google-cloud-logging` en el código, a partir de F3.

## 8. Decisiones de diseño (resumen)

| Decisión | Elección | Motivo |
|---|---|---|
| Orquestación | `SequentialAgent` | pipeline lineal con dependencias claras |
| Modelos | Flash (pasos) + Pro (síntesis) | coste/calidad |
| Deploy | Cloud Run + scale-to-zero | crédito Marketing, sin coste en reposo |
| Región | `europe-west1` | EU / GDPR |
| RAG | Vertex AI Search | crédito GenAI App Builder, grounding con citas |
| Python | 3.13 | ya instalado; constraint `>=3.11,<3.14` |
| Gestor de paquetes | uv | rápido, lockfile reproducible |
