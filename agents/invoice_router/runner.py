"""Local test runner for the invoice_router agent draft.

Run with:
    python -m agents.invoice_router.runner

Swap the TEST_CASES entries to try different scenarios.
"""
import asyncio

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import root_agent
from .config import Settings

USER_ID = "local-tester"

TEST_CASES = [
    {
        "label": "WhatsApp con factura PDF",
        "prompt": (
            "Canal: whatsapp. "
            "Remitente: +34600111222. "
            "Texto: 'Te mando la factura de abril adjunta'. "
            "Fichero: factura_abril.pdf"
        ),
    },
    {
        "label": "Email sin adjunto claro",
        "prompt": (
            "Canal: email. "
            "Remitente: proveedor@ejemplo.es. "
            "Texto: 'Buenos dias, te envio el documento mensual'. "
            "Fichero: "
        ),
    },
    {
        "label": "WhatsApp mensaje de texto sin factura",
        "prompt": (
            "Canal: whatsapp. "
            "Remitente: +34611999888. "
            "Texto: 'Hola, quedamos el lunes?'. "
            "Fichero: "
        ),
    },
]


async def run_case(runner: Runner, session_id: str, label: str, prompt: str) -> None:
    content = types.Content(role="user", parts=[types.Part(text=prompt)])
    print(f"\n{'='*60}")
    print(f"CASO: {label}")
    print(f"PROMPT: {prompt}")
    print("-" * 60)

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response():
            print("RESPUESTA:", event.content.parts[0].text)


async def main() -> None:
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name=Settings.APP_NAME,
        session_service=session_service,
    )

    for i, case in enumerate(TEST_CASES):
        session_id = f"draft-session-{i}"
        await session_service.create_session(
            app_name=Settings.APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
        )
        await run_case(runner, session_id, case["label"], case["prompt"])


if __name__ == "__main__":
    asyncio.run(main())
