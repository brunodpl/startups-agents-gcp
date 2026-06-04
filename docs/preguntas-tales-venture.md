# Preguntas de descubrimiento para Tales Venture

Este sistema agéntico es **para Tales Venture**: las decisiones de abajo son
**requisitos de producto que define el cliente**, no asunciones nuestras. Para
cada bloque indicamos **dónde enchufa la respuesta en el sistema** y el **default
que usa la demo** mientras tanto, de modo que haya una URL que funcione ya.

> Cuanto más "suyas" sean las respuestas (sobre todo los frameworks del bloque 3),
> más "suyo" es el diagnóstico que produce el agente.

---

## 1. Tesis de inversión — el *input* del sistema
- ¿Qué **sectores/verticales** buscáis? ¿Y anti-sectores (qué descartáis siempre)?
- ¿Qué **stage(s)**? (pre-seed, seed, Serie A…)
- ¿Qué **geografía**? (España, UE, global…)
- ¿Qué **señales de "fit"** con vuestra tesis? (perfil de founder, tracción mínima,
  tipo de tecnología, modelo de negocio…)
- ¿**Ticket / tamaño de cheque**? (condiciona el stage)

→ *Enchufa en:* el objeto `tesis {sector, stage, geografía, señales}` que recibe **Discovery**.

## 2. Sourcing y fuentes — *Discovery*
- ¿Qué **fuentes usáis hoy** para encontrar startups? (dealflow propio, Crunchbase,
  Dealroom, PitchBook, redes, eventos…)
- ¿Qué **fuentes públicas / con API** podemos integrar? ¿Tenéis cuentas o API keys?
- ¿Qué **señales priorizáis** al descubrir? (tracción, equipo, momentum, tech)
- ¿**Restricciones legales/GDPR** sobre datos de founders?

→ *Enchufa en:* las fuentes que consulta Discovery + los **pesos de scoring** contra la tesis.

## 3. Frameworks de evaluación — vuestra metodología = el "conocimiento" ⭐
- ¿Cuál es vuestra **metodología de diagnóstico 360º**? ¿Podéis compartir vuestros
  **frameworks / rúbricas / playbooks**?
- ¿Qué **dimensiones** evaluáis y cómo las **ponderáis**? (equipo, mercado, producto,
  tracción, modelo, moat…)
- ¿Criterios de **red flag** / descarte automático?

→ *Enchufa en:* los `.md` de `knowledge/` que se **inyectan en contexto** en el
Diagnosis y que el agente **cita**. **Es el bloque más importante**: aquí es donde
el sistema deja de ser genérico y pasa a pensar como Tales Venture.

## 4. Análisis por candidata — *Analysis*
- ¿Qué **dimensiones** queréis por startup? (modelo de negocio, métricas/unit
  economics, mercado/competencia, equipo…)
- ¿Qué datos son **imprescindibles** vs *nice-to-have*?
- ¿Qué **fuentes por candidata**? (su web, prensa, repos, app stores…)

→ *Enchufa en:* los sub-agentes de Analysis y sus tools.

## 5. Diagnóstico y entregable — *Diagnosis + Presentation*
- ¿Qué debe **contener el informe**? (fortalezas, riesgos, palancas de crecimiento,
  fit con la tesis, experimentos Lean priorizados, recomendación go/no-go…)
- ¿En qué **formato**? (informe legible, JSON, PDF, dashboard, Notion…)
- ¿**Ranking/score** numérico? ¿En qué escala?
- ¿Qué **nivel de citación/justificación** esperáis?

→ *Enchufa en:* el prompt del **Synthesizer** + el **ReportingAgent** + el esquema de salida.

## 6. Operativa y escala
- ¿Cuántas candidatas por tesis y con qué **frecuencia**?
- ¿**Quién lo usa**? (analistas, partners) ¿Hay **humano en el loop**?
- ¿**Integraciones**? (CRM, Notion, Slack, email)

→ *Enchufa en:* scope, forma de entrega e integraciones.

## 7. Datos, compliance y seguridad
- **GDPR**: ¿qué datos de founders podéis/queréis almacenar?
- ¿Dónde **vive el dato**? (región, retención)
- ¿**Confidencialidad** del dealflow?

→ *Enchufa en:* región (`europe-west1`), políticas de retención y control de acceso.

---

## Defaults de la demo (placeholders, todos configurables)

Para tener una URL que funcione **antes** de que Tales Venture responda:

| Decisión | Default de la demo | A sustituir por |
|---|---|---|
| Tesis | _(pendiente — p. ej. "AI/dev-tools B2B SaaS, early-stage, global")_ | la tesis real de TV |
| Fuente Discovery | YC OSS API (gratis, sin key) | sus fuentes/keys |
| Frameworks (`knowledge/`) | 2 `.md` genéricos (rúbrica VC + Lean/growth) | sus frameworks |
| Output | shortlist top 3 con citas | su formato/score |

> Todo está parametrizado: cambiar la tesis es pasar otro input; cambiar los
> frameworks es soltar otros `.md` en `knowledge/`. La demo no "hardcodea" la
> opinión de Tales Venture; la inyecta.
