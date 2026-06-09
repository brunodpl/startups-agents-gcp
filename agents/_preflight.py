"""Deploy preflight: fail loudly if a runtime dependency is missing (P0.1).

``adk deploy cloud_run`` installs from ``agents/requirements.txt`` (NOT
pyproject), and the agent package imports its tools lazily on the first /run.
So a dependency missing from requirements.txt ships a container that reports
"Ready" yet 500s on the first request — exactly what happened with ``firecrawl``
on 2026-06-04. Run this BEFORE deploy so the failure is loud and local:

    python -m agents._preflight     # exit 0 = ok, non-zero = a dep is missing
"""

from __future__ import annotations

import importlib

# Runtime modules the agent imports that previously bit us lazily. Keep in sync
# with agents/requirements.txt.
REQUIRED_MODULES = [
    "firecrawl",
    "google.genai",
    "google.cloud.logging",
    "httpx",
    "pydantic",
    "dotenv",
]


def check_imports() -> None:
    """Import every runtime dependency and build the agent tree, or raise.

    Propagates the original ImportError/ModuleNotFoundError so the caller can
    surface the exact missing module.
    """
    for module in REQUIRED_MODULES:
        importlib.import_module(module)
    # Force the whole tree (tools, prompts, knowledge, sub-agents) to import —
    # this is what fails lazily inside adk_web_server on /run.
    from .agent import root_agent  # noqa: F401


def main() -> int:
    try:
        check_imports()
    except Exception as exc:  # report ANY import failure
        print(f"PREFLIGHT FAIL: {type(exc).__name__}: {exc}")
        return 1
    print("PREFLIGHT OK: all runtime deps import and the agent tree builds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
