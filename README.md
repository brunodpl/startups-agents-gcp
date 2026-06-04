Agente de Diagnóstico 360º

## DECISIONES DE ARQUITECTURA YA CERRADAS (no reabrir)

1. **Conocimiento = frameworks EN CONTEXTO. NO RAG, NO Skills.** El corpus de frameworks de evaluación es pequeño y estático → se leen de archivos `.md` y se inyectan en el `instruction` del agente. **Prohibido** montar vector DB, Vertex AI Search, embeddings o Skills de Anthropic. (Eso queda como fase futura SOLO si el corpus crece.)
2. **Auditabilidad por prompting:** el agente debe **citar de qué framework sale cada conclusión** (ej. "según el criterio X del framework Y…").
3. **Discovery es un agente de sourcing REAL**, pero por **integración con fuentes públicas que ya existen** — NUNCA reconstruir una base de datos tipo Harmonic.
4. **Stack:** Google ADK + Vertex AI (Gemini 2.5) + Cloud Run.

## ARQUITECTURA — PIPELINE DE 4 FASES

1. **Discovery** (agente de sourcing): input = tesis `{sector, stage, geografía, señales}`. Consulta **en paralelo fuentes públicas vía API**, normaliza, deduplica y **puntúa candidatas contra la tesis** → shortlist. Respeta `robots.txt` y ToS; **nada de scrapear LinkedIn/Crunchbase**; GDPR-aware con datos de founders. (Demo: 1–2 fuentes GRATIS.)
2. **Analysis** (grupo de agentes en paralelo): por cada candidata del top → modelo de negocio, métricas y unit-economics signals, mercado/competencia. Incluye un `ResearchAgent` con tool de fetch de URL.
3. **Diagnosis** (`SynthesizerAgent`, gemini-2.5-pro): juicio estructurado → fortalezas, riesgos, palancas de crecimiento, fit con la tesis y experimentos Lean priorizados. **Grounded en los frameworks EN CONTEXTO, citando fuentes.**
4. **Presentation** (`ReportingAgent`): informe **rankeado y estructurado** (JSON + legible) entregado al equipo del venture, expuesto vía la URL de Cloud Run.

## CONOCIMIENTO (cómo cargar los frameworks)

- Carpeta `knowledge/` con archivos `.md` (frameworks de evaluación, criterios, playbooks de growth).
- Un helper que **lee todos los `.md` → concatena → inyecta en el `instruction`** de Diagnosis (y de Analysis si aplica). Ej.: `Path("knowledge").glob("*.md")` → leer → unir.
- Nada más. Si crece en el futuro: migrar a Vertex AI Search (fase posterior, fuera de esta demo).

## HARNESS DE EVALS (EL DIFERENCIADOR)

Mide en 4 niveles y explícame qué mide cada uno:
1. **Paso individual** — ¿cada agente hace bien su parte?
2. **Trayectoria** — ¿la secuencia de decisiones es correcta de principio a fin?
3. **Llamada a herramientas** — ¿llama a la tool correcta con los argumentos correctos?
4. **Salida final** — ¿el diagnóstico es correcto y cita fuentes reales?

## FASES DE TRABAJO

- **F0 (AHORA, antes de codear):** preguntas de setup (ver "EMPIEZA AQUÍ").
- **F1:** scaffold + agente ADK "hello world" sobre Vertex + **desplegar a Cloud Run y obtener una URL que funcione PRIMERO** (validar el pipeline de deploy antes de meter lógica).
- **F2:** Discovery agent con 1 fuente API → devuelve shortlist cruda.
- **F3:** Analysis + Diagnosis (frameworks en contexto + citación).
- **F4:** Presentation (informe rankeado) + segunda fuente en Discovery.
- **F5:** eval harness + README + guion de demo de 2 min.
