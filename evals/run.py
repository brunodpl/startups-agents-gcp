"""Entry point for the eval harness: ``python -m evals.run`` (F5).

Runs the pipeline once per dataset thesis and scores it at 4 levels:
  1. Step       — every stage produced output, no errors.
  2. Trajectory — discovery -> research -> analysts -> synthesizer -> reporting.
  3. Tool calls — find_candidates called; fetch_url URL came from state.
  4. Final      — report cites real frameworks + covers expected criteria
                  (LLM-as-judge over Vertex).

The pipeline runs live (Vertex + Firecrawl + YC/GitHub), so by default only the
first thesis is evaluated. Use ``--all`` for the whole dataset.

  uv run python -m evals.run            # first thesis
  uv run python -m evals.run --all      # all theses (slow / more credit)
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Cheap eval runs unless overridden.
os.environ.setdefault("TOP_N", "2")

from google.genai import types  # noqa: E402

from agents.agent import root_agent  # noqa: E402
from agents.config import Settings  # noqa: E402
from agents.pipeline import _strip_and_parse  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402

from .levels import (  # noqa: E402
    RunCapture,
    level1_step,
    level2_trajectory,
    level3_tools,
    level4_final,
)

DATASET = Path(__file__).parent / "datasets" / "regression.jsonl"
APP = "startup_diagnostics_eval"


async def capture_run(thesis: str) -> RunCapture:
    """Run the full pipeline once and capture authors/tool-calls/state."""
    runner = InMemoryRunner(agent=root_agent, app_name=APP)
    session = await runner.session_service.create_session(app_name=APP, user_id="eval")
    content = types.Content(role="user", parts=[types.Part(text=thesis)])

    cap = RunCapture(thesis=thesis)
    async for event in runner.run_async(
        user_id="eval", session_id=session.id, new_message=content
    ):
        author = getattr(event, "author", None)
        if author and (not cap.authors or cap.authors[-1] != author):
            cap.authors.append(author)
        if getattr(event, "error_message", None):
            cap.error_events.append(event.error_message)
        for part in getattr(getattr(event, "content", None), "parts", None) or []:
            fc = getattr(part, "function_call", None)
            if fc:
                cap.tool_calls.append(
                    {"name": fc.name, "args": dict(fc.args or {})}
                )

    s = await runner.session_service.get_session(
        app_name=APP, user_id="eval", session_id=session.id
    )
    cap.state = dict(s.state)
    return cap


def make_judge():
    """An LLM-as-judge that scores criterion coverage over Vertex (Flash)."""
    from google import genai

    client = genai.Client(
        vertexai=True,
        project=Settings.GOOGLE_CLOUD_PROJECT,
        location=Settings.GOOGLE_CLOUD_LOCATION,
    )

    def judge(report: str, criteria: list[str]) -> dict[str, bool]:
        numbered = "\n".join(f"{i}. {c}" for i, c in enumerate(criteria, 1))
        prompt = (
            "Eres un evaluador estricto. Dado un INFORME y una lista de "
            "CRITERIOS, indica para cada criterio si el informe lo cubre.\n"
            'Devuelve SOLO un objeto JSON {"1": true, "2": false, ...} con una '
            "entrada por criterio, usando su número.\n\n"
            f"INFORME:\n{report}\n\nCRITERIOS:\n{numbered}\n"
        )
        try:
            resp = client.models.generate_content(
                model=Settings.MODEL_FLASH, contents=prompt
            )
            data = _strip_and_parse(resp.text or "{}")
        except Exception as e:  # judge failure shouldn't crash the harness
            print(f"  [judge error] {e}")
            data = {}
        if not isinstance(data, dict):
            data = {}
        return {c: bool(data.get(str(i))) for i, c in enumerate(criteria, 1)}

    return judge


def main() -> None:
    parser = argparse.ArgumentParser(description="4-level eval harness")
    parser.add_argument(
        "--all", action="store_true", help="run every thesis (slow)"
    )
    parser.add_argument(
        "--limit", type=int, default=1, help="how many theses to run (default 1)"
    )
    args = parser.parse_args()

    rows = [
        json.loads(line)
        for line in DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not args.all:
        rows = rows[: max(args.limit, 1)]

    judge = make_judge()
    all_passed = True

    for entry in rows:
        print("\n" + "=" * 72)
        print(f"THESIS [{entry['id']}]: {entry['thesis'][:80]}...")
        print("=" * 72)
        cap = asyncio.run(capture_run(entry["thesis"]))
        results = [
            level1_step(cap),
            level2_trajectory(cap),
            level3_tools(cap),
            level4_final(cap, entry["expected_criteria"], judge),
        ]
        for r in results:
            mark = "PASS" if r.passed else "FAIL"
            print(f"[{mark}] level {r.name}")
            for line in r.details:
                print(f"       {line}")
            all_passed = all_passed and r.passed

    print("\n" + "=" * 72)
    print("OVERALL:", "PASS" if all_passed else "FAIL")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
