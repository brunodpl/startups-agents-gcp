"""DiscoveryAgent (F2): thesis -> shortlist of QUALIFIED candidate startups.

Calls the ``find_candidates`` source tool and applies a binary gate to each
candidate (es_candidato / no_es_candidato: sector AND geography AND signals must
fit the thesis). Writes the qualified shortlist (as JSON text) to
``state["shortlist"]`` via ``output_key`` so the rest of the pipeline can
consume it.
"""

from google.adk.agents import Agent

from ..config import Settings
from ..prompts import DISCOVERY_INSTRUCTION
from ..tools.sources import find_candidates

# MAX_CANDIDATES is injected with an f-string (not str.format) so the JSON braces
# inside DISCOVERY_INSTRUCTION are left untouched.
discovery_agent = Agent(
    model=Settings.MODEL_FLASH,
    name="discovery_agent",
    description="Qualifies an investment thesis into a shortlist of fit startups.",
    instruction=(
        DISCOVERY_INSTRUCTION
        + f"\nDevuelve TODAS las candidatas que cualifiquen (es_candidato), hasta "
        f"un MÁXIMO de {Settings.MAX_CANDIDATES} (si cualifican más, quédate con "
        "las mejores por el desempate; si cualifican menos, devuelve solo esas; "
        "si ninguna cualifica, devuelve la lista vacía)."
    ),
    tools=[find_candidates],
    output_key="shortlist",
)
