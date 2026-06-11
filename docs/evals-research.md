# Investigación: evals en el proyecto (documento vivo · /loop)

> Objetivo del loop: investigar a fondo **cómo llevar a cabo evals** en este
> proyecto, sacar conclusiones y **ir contrastando** entre iteraciones.
> **Restricción del usuario:** *limitarse a investigar* — NO implementar cambios.
> Cada iteración añade una sección; las conclusiones se refinan/contrastan.

---

## Iteración 1 — Inventario del estado actual + primer contraste (custom vs ADK)

### 1.1 Qué existe hoy (inventario verificado en código)

| Pieza | Fichero | Qué hace |
|---|---|---|
| Harness 4 niveles (lógica pura) | `evals/levels.py` | `level1_step`, `level2_trajectory`, `level3_tools`, `level4_final` sobre un `RunCapture` |
| Runner + LLM-judge | `evals/run.py` | Corre el pipeline **en vivo** (Vertex+Firecrawl+YC/GitHub), captura authors/tool_calls/state, juzga cobertura de criterios |
| Dataset de regresión | `evals/datasets/regression.jsonl` | **4 tesis** (ai-devtools, fintech, healthtech, climate) con `expected_criteria` |
| Tests offline del harness | `tests/test_levels.py` | Verifican la lógica de niveles sin red (judge inyectado) |

**Los 4 niveles:**
1. **Paso** — `shortlist`, `analyses[*].{research,business,metrics,market,diagnosis}`, `report` no vacíos y sin `error_events`.
2. **Trayectoria** — orden de `authors`: discovery → research → (business‖metrics‖market) → synthesizer → reporting.
3. **Tools** — `find_candidates` llamado con `sector`; **y cada URL de `fetch_url` pertenece al dominio de una candidata en `state`** (no hardcodeada).
4. **Final** — el `report` contiene los nombres de framework (`FRAMEWORK_NAMES`) **por substring** + un **LLM-judge** (Flash/Vertex) puntúa cobertura de `expected_criteria`, umbral **0.70**.

Detalles de implementación relevantes:
- `os.environ.setdefault("TOP_N", "2")` → evals baratas; por defecto **1 tesis** (`--limit 1`), `--all` para las 4.
- Judge = `Settings.MODEL_FLASH` sobre Vertex, **1 muestra**, salida JSON `{"1": true, ...}`, binaria por criterio.
- `RunCapture` se llena recorriendo eventos del `InMemoryRunner` (author, function_call, error_message, state final).

### 1.2 Paradigmas disponibles para evaluar

- **(A) Harness bespoke** — lo que ya hay (`evals/`).
- **(B) ADK-native eval** — `AgentEvaluator` / `agents-cli eval run` + `evalset.json` + `eval_config.json` y **8 criterios** built-in: `tool_trajectory_avg_score`, `response_match_score`, `final_response_match_v2`, `rubric_based_final_response_quality_v1`, `rubric_based_tool_use_quality_v1`, `hallucinations_v1`, `safety_v1` (+ custom). Incluye `eval compare` (baseline) y la pestaña Eval de la web UI.
  - **No está configurado** en el repo: no hay `evalset.json` ni `eval_config.json` (solo `regression.jsonl`). Se optó por el camino custom.
- **(C) Vertex AI GenAI Evaluation Service** — eval gestionada en cloud (encaja con el crédito Marketing). *Pendiente de investigar (it. siguiente).*

### 1.3 Contraste — dónde gana el bespoke

1. **Trayectoria multi-agente real.** El root es `SequentialAgent + PerCandidateAnalysis` (un `BaseAgent` custom que itera sub-agentes por candidata). El modelo de ADK (tool_uses esperados **por invocación**) encaja mal con una trayectoria **dinámica** (N candidatas) — por eso aquí se valida el **orden de `authors`**, que es lo que importa.
2. **Nivel 3 = invariante de dominio.** "La URL de `fetch_url` ∈ dominios de candidatas en `state`" **demuestra que el dato fluye por `state`, no hardcodeado**. `tool_trajectory_avg_score` genérico **no puede expresar esto**. Es la parte más valiosa del harness.
3. **Funciones puras → testeables offline** (`tests/test_levels.py`). Buena ingeniería; el judge se inyecta, así que la lógica no toca la red.

### 1.4 Contraste — gaps del bespoke (lo que ADK sí da)

1. **No mide grounding/alucinación.** El nivel 4 solo hace **substring** de los nombres de framework → un informe puede *nombrar* "Marco Lean & Growth" y **fabricar** lo que dice → **PASS falso**. Para un producto cuyo pitch es "grounded en frameworks + citas", esto es el gap de mayor valor. ADK `hallucinations_v1` verifica que las afirmaciones estén ancladas en el contexto/tool output.
2. **Judge débil: 1 muestra, binario, auto-evaluado.** Flash juzgando a Flash, `num_samples=1`, sin rúbrica. ADK `final_response_match_v2` / rubric evaluators soportan **num_samples** (estabilidad) y **rúbricas estructuradas**. El judge debería ser **Pro** (o multi-muestra) para la calidad final.
3. **No-determinismo sin gestionar.** Corrida en vivo, sin fijar `temperature` → scores fluctúan; sin mitigación de flakiness. Guía ADK: `temperature=0` o métricas rubric-based.
4. **No hay baseline/`compare`.** El harness imprime PASS/FAIL y `exit(1)`; no compara contra un baseline almacenado → **no detecta drift** (p. ej. caer de 90% a 75% sigue "pasando" el 0.70).
5. **Cobertura fina:** 4 tesis, 1 turno cada una; por defecto 1 tesis / TOP_N=2.
6. **Coste/velocidad:** cada eval = pipeline **en vivo** completo (Vertex+Firecrawl+fuentes) → lento, gasta crédito, **no reproducible offline**. Difícil de meter en CI.
7. **Citación de framework frágil:** substring de **2 nombres hardcodeados** → un 3er framework o un parafraseo rompe el check; y *presencia ≠ uso correcto*.

### 1.5 Contraste — dónde ADK-native NO encaja bien aquí (el contraste corta en ambos sentidos)

1. **Discovery en vivo y no-determinista** → no puedes fijar los `tool_uses` args esperados (las URLs de candidatas cambian entre corridas). Los evalset de ADK asumen tool calls reproducibles. **Esto es justo por lo que el nivel 3 valida un invariante** en vez de una trayectoria exacta.
2. **`BaseAgent` custom (PerCandidateAnalysis)** → trayectoria por-invocación dinámica; mal encaje con el matching exacto de ADK.
3. **Gotchas:** app name debe = nombre del directorio (`agents/`); para evalsets estables habría que **controlar el sourcing** (fixtures/replay).

### 1.6 Hipótesis de recomendación (a validar en próximas iteraciones)

- **Híbrido.** Mantener niveles 1–3 custom (estructura + invariantes de flujo que ADK no expresa). **Subir el nivel 4** hacia el modelo de calidad de ADK: añadir **check de grounding/alucinación**, **judging rubric-based**, **multi-muestra** y **judge Pro** (o Vertex GenAI Eval).
- **Añadir baseline/compare** para detectar *drift*, no solo pasar umbral.
- **Para determinismo/CI:** modo **fixture/replay** del discovery (grabar fuentes una vez) → evals que no dependan de YC/GitHub en vivo. Si no, las evals se quedan en "smoke + judge", no regresión real.

### 1.7 Preguntas abiertas (agenda para próximas iteraciones)

- [ ] ¿`agents-cli` / CLI de eval de ADK es usable aquí (WDAC + `BaseAgent` custom)? ¿`AgentEvaluator.evaluate` puede correr este pipeline?
- [ ] ¿La versión instalada de ADK incluye `hallucinations_v1` y `rubric_based_*`? (vistos en `.venv`: `rubric_based_evaluator.py`, `safety_evaluator.py`, `response_evaluator.py`, `trajectory_evaluator.py`, `multi_turn_*`; falta confirmar hallucinations).
- [ ] `pipeline.py` / `prompts.py`: ¿hay control de `temperature`? ¿contratos de salida (output_schema) que ayuden al determinismo?
- [ ] Vertex AI GenAI Evaluation Service — ¿encaja con el crédito Marketing? ¿merece la pena para una demo?
- [ ] Replay/fixtures del discovery — ¿cómo grabar fuentes para evals reproducibles sin reescribir el pipeline?
