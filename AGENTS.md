# Prompt — Demo para Tales Venture: Agente de Diagnóstico 360º de Startups

> Pégale esto a tu agente de código (Claude Code / Cursor). Objetivo: impresionar a Tales Venture, gratis (consumiendo tus créditos GCP que caducan), y **desplegado en una URL que puedan clicar**. Sustituye lo que esté entre `<...>` si quieres ajustar algo.

---

## CONTEXTO Y ROL

Eres un ingeniero senior de agentes en **Google Cloud (Vertex AI + Agent Development Kit)**. Vamos a construir, paso a paso, una **demo para impresionar a Tales Venture**, un venture studio gallego cuyo servicio core es el **diagnóstico 360º de startups** (modelo de negocio, métricas clave, palancas de crecimiento ocultas, aplicando Lean Startup). La demo **automatiza un trozo de ese mismo servicio** — esa es la sorpresa: demostrar que puedo 10x su propio proceso.

Sobre cómo trabajamos:
- **Explica cada decisión técnica y la sintaxis nueva** (async, decoradores, type hints) en 2–3 frases. Estoy reforzando sintaxis de Python.
- **Déjame escribir una función o agente por fase** y corrígeme; no lo escribas todo tú.
- **No sobre-ingenierices.** Mínimo que funcione. Prohibido inventar frameworks propios.
- **Mentalidad de deadline:** demo desplegada en días, no semanas. Una URL que funciona > la perfección.
- **Pregunta antes de asumir.**

## OBJETIVO

Un sistema multi-agente que, dada la **URL (+ datos básicos) de una startup**, produce un **diagnóstico 360º estructurado**: modelo de negocio, lectura de métricas, palancas de crecimiento ocultas y experimentos Lean priorizados. Desplegado en **Cloud Run** y con un **mini-harness de evals**.

## STACK OBLIGATORIO

- **Google ADK** (`google-adk`) para la orquestación de agentes
- **Vertex AI (Gemini 2.5 Flash/Pro)** como LLM — vía Vertex, NUNCA free tier
- **Vertex AI Search (Discovery Engine)** para el RAG / grounding
- **Cloud Run** para el despliegue (`adk deploy cloud_run`)
- **Cloud Storage** como landing y fuente para indexar el datastore
- Python 3.12; FastAPI solo si hace falta un endpoint custom (ADK ya expone el suyo)
- **pytest** para los evals

## REGLAS DE GCP (NO NEGOCIABLE — para no malgastar mi crédito promocional)

Tengo dos créditos: **Marketing AI Agents Challenge (433€, caduca 2026-06-25)** que consumen Cloud Run + Vertex AI + Cloud Storage; y **GenAI App Builder (848€, hasta 2027-03)** que consume Discovery Engine. Por eso:

```python
import os
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"     # enruta los LLM por aiplatform.googleapis.com (consume crédito)
os.environ["GOOGLE_CLOUD_PROJECT"]      = "your-gcp-project"  # único proyecto al que están ligados los créditos
os.environ["GOOGLE_CLOUD_LOCATION"]     = "europe-west1"         # región EU (GDPR)
```

- Usa el **SDK de Vertex AI** (`from vertexai.generative_models import GenerativeModel`) o los agentes de ADK (`LlmAgent`). **NUNCA** `import google.generativeai` ni `genai.configure(api_key=...)` → eso es free tier y NO consume el crédito.
- **NUNCA** uses LangChain / LlamaIndex / OpenAI SDK como transporte de las llamadas a Gemini (no enrutan por Vertex por defecto).
- Despliega **solo en Cloud Run** (NO Cloud Functions ni App Engine — no están en el crédito).
- **Scale to zero**: no pongas `minScale ≥ 1`.
- **No crees un proyecto GCP nuevo** — los créditos no se transfieren.

## ARQUITECTURA (multi-agente, mínima)

`Orchestrator` (SequentialAgent de ADK):
1. **ResearchAgent** (`LlmAgent` + tool de fetch de URL): extrae info del sitio/datos públicos de la startup.
2. **BusinessModelAgent**: propuesta de valor, segmento, monetización.
3. **MetricsAgent**: lee/estima métricas clave y señales de unit economics.
4. **GrowthLeversAgent**: palancas de crecimiento ocultas, **grounded vía Vertex AI Search** sobre un corpus de frameworks de growth/Lean.
5. **SynthesizerAgent** (gemini-2.5-pro): informe 360º final estructurado.

RAG: indexa un corpus pequeño (Lean Startup, playbooks de growth, notas de benchmark) en Cloud Storage → Discovery Engine; consúltalo con `VertexAiSearchTool`.

## REQUISITOS FUNCIONALES

- Input: URL de la startup + opcional `{sector, stage, métricas}`.
- Output: **JSON estructurado + informe legible** con secciones: modelo de negocio, lectura de métricas, palancas de crecimiento, experimentos Lean priorizados.
- Cita las fuentes/grounding.
- Logging: qué agente actuó, qué tools llamó, latencia.

## HARNESS DE EVALS (EL DIFERENCIADOR)

Mide en 4 niveles y explícame qué mide cada uno:
1. **Paso individual** — ¿cada agente hace bien su parte?
2. **Trayectoria** — ¿la secuencia de decisiones es correcta de principio a fin?
3. **Llamada a herramientas** — ¿llama a la tool correcta con los argumentos correctos?
4. **Salida final** — ¿el diagnóstico es correcto y cita fuentes reales?

Además: un **dataset de regresión** (3–5 startups conocidas con criterios de diagnóstico esperados) y un comando (`python -m evals.run`) que ejecuta los evals y saca un informe con métricas por nivel y los fallos concretos.

## CALIDAD Y RESTRICCIONES

- Código custom, **nada de low-code**.
- Type hints en todo; funciones pequeñas; manejo de errores explícito; secretos en `.env`.
- Región EU (`europe-west1`) — consciente de GDPR.
- **Es un prototipo sobre mi proyecto GCP personal**; si la cosa avanza a startup real, la producción se mueve a la cuenta cloud de esa startup.

## FASES (rápido → desplegado pronto)

- **F1** — scaffold + un agente "hello world" de ADK sobre Vertex + **desplegar a Cloud Run y obtener una URL que funcione PRIMERO**. (Validar el pipeline de despliegue antes de meter lógica.)
- **F2** — ResearchAgent + tool de fetch de URL → devuelve un resumen de la startup.
- **F3** — diagnóstico multi-agente completo (business / metrics / growth / synth).
- **F4** — grounding RAG vía Vertex AI Search.
- **F5** — harness de evals + UI mínima opcional + README + guion de demo de 2 min.

Al final de cada fase: resumen de qué construimos, qué sintaxis nueva apareció, y un mini-reto para que yo escriba algo solo.

## EMPIEZA AQUÍ

Antes de escribir código, hazme las preguntas que necesites para la **F1**: versión de ADK, si ya tengo el proyecto GCP y credenciales configuradas (`gcloud auth`, APIs habilitadas: `aiplatform`, `run`, `storage`, `discoveryengine`), región, etc. **No asumas.**
