"""M1+M4 (Tag 1, Modul 6): P->G->E-Orchestrator aus Tag 2, aber der Evaluator ist
jetzt ECHTES pytest statt eines LLM ("Meinung raus, Beweis rein").

Task unveraendert aus Modul 5B: ist_upload_gueltig() nach LearnFlow ADR-003.
"""
import asyncio, sys, os, re, subprocess, shutil
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock
sys.stdout.reconfigure(encoding="utf-8")

# Abo statt API-Key: ANTHROPIC_API_KEY würde sonst gewinnen
os.environ.pop("ANTHROPIC_API_KEY", None)
if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
    sys.exit("Abo-Token fehlt: claude setup-token")

def role_opts(system, tools=None, budget=0.20):
    return ClaudeAgentOptions(
        model="claude-sonnet-4-6", system_prompt=system,
        allowed_tools=tools or [], max_turns=5, max_budget_usd=budget,
    )

planner_o   = role_opts("Du bist Planner. Zerlege die Aufgabe in eine knappe Spec: Inputs, Outputs, Edge Cases. Kein Code.")
generator_o = role_opts("Du bist Generator. Setze die Spec exakt in Python um. NUR Code.", budget=0.30)

def pytest_evaluator(test_file: str) -> str:
    """M4: echter Evaluator. Exit-Code 0 = PASS, sonst FAIL mit Test-Output als Feedback."""
    shutil.rmtree("__pycache__", ignore_errors=True)  # WICHTIG! sonst testet pytest die alte mycode.py
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-q",
         "--no-header", "-p", "no:cacheprovider"],
        capture_output=True, text=True, timeout=60, env=env)
    if result.returncode == 0:
        return "PASS"
    return f"FAIL:\n{result.stdout[-800:]}"

async def run(opts, prompt):
    out = []
    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    out.append(b.text)
    return "\n".join(out)

def extrahiere_code(text: str) -> str:
    """Entfernt ```python ... ```-Fences, falls der Generator trotz 'NUR Code' welche liefert."""
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()

async def main():
    task = (
        "Eine Funktion ist_upload_gueltig(dateiname: str, groesse_bytes: int) -> tuple[bool, str] "
        "nach LearnFlow ADR-003: maximal 10 MB (10 * 1024 * 1024 Bytes), erlaubte Formate anhand "
        "der Dateiendung: .pdf, .docx, .md (Gross-/Kleinschreibung egal). Bei Ablehnung enthält der "
        "zweite Rückgabewert einen kurzen deutschen Grund, bei Erfolg einen leeren String."
    )
    try:
        print("=== PLANNER ===")
        plan = await run(planner_o, f"Aufgabe: {task}")
        print(plan[:400])
        for rnd in range(1, 4):
            print(f"\n=== GENERATOR (Runde {rnd}) ===")
            code = await run(generator_o, f"Spec:\n{plan}")
            print(code[:400])

            with open("mycode.py", "w", encoding="utf-8") as f:
                f.write(extrahiere_code(code))

            print(f"\n=== EVALUATOR (Runde {rnd}, pytest) ===")
            verdict = pytest_evaluator("test_mycode.py")
            print(verdict)
            if verdict.strip().upper().startswith("PASS"):
                print(f"\n*** PASS in Runde {rnd} ***")
                return
            plan += f"\n\nEvaluator-Feedback (echter pytest-Output): {verdict}"
        print("\n*** kein PASS nach 3 Runden -> Mensch entscheidet ***")
    except Exception as e:  # max_turns/max_budget wirft
        print(f"FAIL: abgebrochen ({e})")

asyncio.run(main())
