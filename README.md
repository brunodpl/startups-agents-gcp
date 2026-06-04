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

## ARQUITECTURA (multi-agente, mínima)

`Orchestrator` (SequentialAgent de ADK):
1. **ResearchAgent** (`LlmAgent` + tool de fetch de URL): extrae info del sitio/datos públicos de la startup.
2. **BusinessModelAgent**: propuesta de valor, segmento, monetización.
3. **MetricsAgent**: lee/estima métricas clave y señales de unit economics.
4. **GrowthLeversAgent**: palancas de crecimiento ocultas, **grounded vía Vertex AI Search** sobre un corpus de frameworks de growth/Lean.
5. **SynthesizerAgent** (gemini-2.5-pro): informe 360º final estructurado.

RAG: indexa un corpus pequeño (Lean Startup, playbooks de growth, notas de benchmark) en Cloud Storage → Discovery Engine; consúltalo con `VertexAiSearchTool`.

## FASES (rápido → desplegado pronto)

- **F1** — scaffold + un agente "hello world" de ADK sobre Vertex + **desplegar a Cloud Run y obtener una URL que funcione PRIMERO**. (Validar el pipeline de despliegue antes de meter lógica.)
- **F2** — ResearchAgent + tool de fetch de URL → devuelve un resumen de la startup.
- **F3** — diagnóstico multi-agente completo (business / metrics / growth / synth).
- **F4** — grounding RAG vía Vertex AI Search.
- **F5** — harness de evals + UI mínima opcional + README + guion de demo de 2 min.
