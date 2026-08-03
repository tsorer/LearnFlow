"""M4 — Der echte Evaluator: pytest statt LLM-Meinung.

Generator -> pytest -> Feedback -> Generator ... bis PASS oder Runden-Limit.

Der Generator schreibt check_encoding_m4.py von Grund auf neu — aus der
Ursprungsanforderung (AUFGABE) plus test_m4.py als verbindlichem Vertrag. Es wird
nichts aus check_encoding.py kopiert oder gepatcht: jede Runde ist eine komplette
Neufassung, die gegen die Test-Suite antritt.

Lauf (im adai-Env, NICHT aus Claude Code heraus):
    conda activate adai
    python orchestrator_m4.py

Nur die aktuelle Datei bewerten, ohne API-Kosten:
    python orchestrator_m4.py --check
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
TARGET = HERE / "check_encoding_m4.py"    # wird jede Runde komplett neu geschrieben
TEST_FILE = "test_m4.py"

MODEL = "claude-sonnet-4-6"  # wie in test_pge.py; fuer mehr Qualitaet: "claude-opus-5"
MAX_ROUNDS = 3


# ---------------------------------------------------------------------------
# Die Ursprungsanforderung — wortgleich der Prompt, aus dem check_encoding.py
# urspruenglich entstand. Der Generator sieht NUR das und die Test-Suite.
# ---------------------------------------------------------------------------

AUFGABE = """Prüft das Encoding der noch nicht committeten Dateien. Nutze IMMER,
wenn Code committed werden soll.

Du prüfst Datei-Encodings. Führe dafür python check_encoding.py aus. Das Skript
liegt im Arbeitsverzeichnis, ermittelt die noch nicht committeten Dateien selbst
und konvertiert sie bei Bedarf nach UTF-8 ohne BOM. Berichte danach: wie viele
Dateien geprüft wurden, welche geändert wurden und ob der Exit-Code 0 war."""

RAHMEN = f"""Schreibe genau dieses Skript — die Datei heisst {TARGET.name}."""


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

GENERATOR_SYSTEM = """Du bist Generator. Du schreibst eine Python-Datei von Grund
auf neu, bis eine gegebene pytest-Suite gruen ist.

Regeln:
- Antworte mit dem VOLLSTAENDIGEN Inhalt der Datei, nichts sonst. Kein Fliesstext,
  keine Erklaerung, keine Markdown-Fences.
"""


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


def build_prompt(spec: str, attempt: str | None, verdict: str | None) -> str:
    parts = [f"AUFGABE:\n{AUFGABE}", RAHMEN, f"TEST-SUITE ({TEST_FILE}):\n\n{spec}"]
    if attempt is not None:
        parts.append(f"DEIN LETZTER VERSUCH:\n\n{attempt}")
        parts.append(f"pytest sagt dazu:\n{verdict}")
    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------


async def main() -> int:
    TARGET.unlink(missing_ok=True)   # leeres Blatt — nichts wird uebernommen
    print(f"Ziel: {TARGET.name} (wird neu geschrieben)")
    print(f"Vertrag: {TEST_FILE}")

    spec = (HERE / TEST_FILE).read_text(encoding="utf-8")
    attempt: str | None = None
    verdict: str | None = None

    for rnd in range(1, MAX_ROUNDS + 1):
        print(f"\n=== GENERATOR (Runde {rnd}) ===")
        code = extract_code(await run(role_opts(GENERATOR_SYSTEM),
                                      build_prompt(spec, attempt, verdict)))

        try:
            ast.parse(code)
        except SyntaxError as e:
            print(f"  Generator lieferte ungueltiges Python: {e}")
            attempt, verdict = code, f"FAIL:\nSyntaxError: {e}"
            continue

        TARGET.write_text(code, encoding="utf-8", newline="\n")
        attempt = code
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
    if "--check" in sys.argv:
        # Kostenfrei: bewertet die Datei, die gerade da liegt.
        print(pytest_evaluator(TEST_FILE))
        sys.exit(0)
    sys.exit(asyncio.run(main()))
