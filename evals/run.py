"""Entry point for the eval harness: ``python -m evals.run``.

Measures the agent at 4 levels (implemented in F5):
  1. Step       — does each sub-agent do its part correctly?
  2. Trajectory — is the end-to-end sequence of decisions correct?
  3. Tool calls — right tool, right arguments?
  4. Final out  — is the diagnosis correct and does it cite real sources?

Plus a regression dataset of 3-5 known startups with expected criteria.
"""


def main() -> None:
    raise SystemExit(
        "Eval harness not implemented yet — lands in F5. See README.md roadmap."
    )


if __name__ == "__main__":
    main()
