"""Local test runner for the csv_transformer agent.

Run with:
    python -m agents.csv_transformer.runner
"""

import asyncio
import base64

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import root_agent
from .config import Settings

USER_ID = "local-tester"


def _make_csv_attachment(csv_text: str) -> types.Part:
    csv_bytes = csv_text.encode("utf-8")
    b64_data = base64.b64encode(csv_bytes).decode("ascii")
    return types.Part(
        inline_data=types.Blob(
            mime_type="text/csv",
            data=b64_data,
        )
    )


TEST_CASES = [
    {
        "label": "Renombrar + reordenar + eliminar columna",
        "csv": "fecha,nombre,importe,notas\n2024-01-01,Juan,100,urgente\n2024-02-15,Ana,250,normal",
        "instruction": "Renombra 'fecha' a 'date', pon 'importe' primero, y quita 'notas'.",
    },
    {
        "label": "Solo reordenar",
        "csv": "nombre,edad,ciudad\nJuan,30,Madrid\nAna,25,Barcelona",
        "instruction": "Pon 'ciudad' al principio.",
    },
    {
        "label": "Solo renombrar",
        "csv": "a,b,c\n1,2,3\n4,5,6",
        "instruction": "Renombra 'a' a 'primera', 'b' a 'segunda', 'c' a 'tercera'.",
    },
]


async def run_case(runner: Runner, session_id: str, label: str, csv_text: str, instruction: str) -> None:
    csv_part = _make_csv_attachment(csv_text)
    instruction_part = types.Part(text=instruction)

    content = types.Content(
        role="user",
        parts=[csv_part, instruction_part],
    )

    print(f"\n{'='*60}")
    print(f"Caso: {label}")
    print(f"CSV:\n{csv_text}")
    print(f"Instrucciones: {instruction}")
    print("-" * 60)

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response():
            text = ""
            for part in event.content.parts:
                text += getattr(part, "text", "")
            print("RESPUESTA DEL AGENTE:")
            print(text)


async def main() -> None:
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name=Settings.APP_NAME,
        session_service=session_service,
    )

    for i, case in enumerate(TEST_CASES):
        session_id = f"csv-session-{i}"
        await session_service.create_session(
            app_name=Settings.APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
        )
        await run_case(
            runner,
            session_id,
            case["label"],
            case["csv"],
            case["instruction"],
        )


if __name__ == "__main__":
    asyncio.run(main())
