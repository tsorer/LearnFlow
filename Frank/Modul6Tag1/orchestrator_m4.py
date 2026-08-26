"""M4 — Der echte Evaluator: pytest statt LLM-Meinung.

Generator -> pytest -> Feedback -> Generator ... bis PASS oder Runden-Limit.

Aufgabe im Loop: check_encoding_m4.py (Kopie von check_encoding.py, v1) hat drei
Bugs, die test_m4.py aufdeckt. Der Generator bekommt den ECHTEN pytest-Output als
Feedback und muss nachbessern.

Lauf (im adai-Env, NICHT aus Claude Code heraus):
    conda activate adai
    python orchestrator_m4.py

Nur den Evaluator pruefen, ohne API-Kosten:
    python orchestrator_m4.py --evaluator-only
"""

import ast
import asyncio
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
SOURCE = HERE / "check_encoding.py"       # v1, mit den Bugs — Ausgangslage
TARGET = HERE / "check_encoding_m4.py"    # was der Generator ueberschreibt
TEST_FILE = "test_m4.py"

MODEL = "claude-sonnet-4-6"  # wie in test_pge.py; fuer mehr Qualitaet: "claude-opus-5"
MAX_ROUNDS = 3


# ---------------------------------------------------------------------------
# Der Evaluator — Vorlage aus dem Lab, unveraendert
# ---------------------------------------------------------------------------


def pytest_evaluator(test_file: str) -> str:
    """Exit-Code 0 = PASS, sonst FAIL mit Test-Output als Feedback."""
    shutil.rmtree("__pycache__", ignore_errors=True)   # WICHTIG!
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-q",
         "--no-header", "-p", "no:cacheprovider"],
        capture_output=True, text=True, timeout=60, env=env)
    if result.returncode == 0:
        return "PASS"
    return f"FAIL:\n{result.stdout[-800:]}"


# ---------------------------------------------------------------------------
# Der Generator
# ---------------------------------------------------------------------------

GENERATOR_SYSTEM = """Du bist Generator. Du reparierst eine bestehende Python-Datei,
bis eine gegebene pytest-Suite gruen ist.

Regeln:
- Antworte mit dem VOLLSTAENDIGEN Inhalt der Datei, nichts sonst. Kein Fliesstext,
  keine Erklaerung, keine Markdown-Fences.
- Aendere so wenig wie moeglich: nur was noetig ist, damit die Tests bestehen.
- Bestehende Funktionssignaturen und das Verhalten von main() bleiben erhalten.
- Erfinde keine Testerwartungen — der pytest-Output ist die Wahrheit."""


def role_opts(system: str, budget: float = 0.50) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=MODEL, system_prompt=system,
        allowed_tools=[], max_turns=5, max_budget_usd=budget,
    )


async def run(opts: ClaudeAgentOptions, prompt: str) -> str:
    out = []
    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    out.append(b.text)
    return "\n".join(out)


def extract_code(answer: str) -> str:
    """Markdown-Fences abstreifen — sonst landet ```python in der .py-Datei.

    Genau das ist bei mycode.py aus M1 passiert.
    """
    fenced = re.search(r"```(?:python)?\n(.*?)```", answer, re.DOTALL)
    return (fenced.group(1) if fenced else answer).strip() + "\n"


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------


async def main() -> int:
    shutil.copy(SOURCE, TARGET)  # immer reproduzierbar bei der kaputten v1 starten
    print(f"Ausgangslage: {SOURCE.name} -> {TARGET.name}")

    spec = (HERE / TEST_FILE).read_text(encoding="utf-8")
    verdict = pytest_evaluator(TEST_FILE)

    print(f"\n=== EVALUATOR (Runde 0, ungepatcht) ===\n{verdict[:600]}")
    if verdict == "PASS":
        print("\n*** Nichts zu tun — die Tests sind schon gruen. ***")
        return 0

    for rnd in range(1, MAX_ROUNDS + 1):
        print(f"\n=== GENERATOR (Runde {rnd}) ===")
        prompt = (
            f"Diese pytest-Suite muss gruen werden:\n\n{spec}\n\n"
            f"Aktueller Inhalt von {TARGET.name}:\n\n"
            f"{TARGET.read_text(encoding='utf-8')}\n\n"
            f"pytest sagt:\n{verdict}"
        )
        code = extract_code(await run(role_opts(GENERATOR_SYSTEM), prompt))

        try:
            ast.parse(code)
        except SyntaxError as e:
            print(f"  Generator lieferte ungueltiges Python: {e}")
            verdict = f"FAIL:\nSyntaxError in der Antwort: {e}"
            continue

        TARGET.write_text(code, encoding="utf-8", newline="\n")
        print(f"  {len(code.splitlines())} Zeilen geschrieben")

        print(f"\n=== EVALUATOR (Runde {rnd}) ===")
        verdict = pytest_evaluator(TEST_FILE)
        print(verdict[:600])

        if verdict == "PASS":
            print(f"\n*** PASS in Runde {rnd} ***")
            return 0

    print(f"\n*** kein PASS nach {MAX_ROUNDS} Runden -> Mensch entscheidet ***")
    return 1


if __name__ == "__main__":
    if "--evaluator-only" in sys.argv:
        # Kostenfrei: nur zeigen, was der Evaluator zur Ausgangslage sagt.
        shutil.copy(SOURCE, TARGET)
        print(pytest_evaluator(TEST_FILE))
        sys.exit(0)
    sys.exit(asyncio.run(main()))
