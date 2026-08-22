"""Praxis-Test 2 (Tag 2): Mini Planner->Generator->Evaluator.

Kleiner Task aus LearnFlow (nicht das ganze Feature): eine reine Python-Funktion,
die die Upload-Validierungsregeln aus ADR-003 / src/frontend/src/components/Upload.tsx
nachbildet (MAX_UPLOAD_BYTES = 10 MB, erlaubte Formate PDF/DOCX/MD).
Reines Uebungsartefakt -- wird nirgends in src/ eingebaut.

Zweimal ausfuehren und vergleichen: PASS-Runde, Code, Kosten identisch? (Spoiler: nein)
"""
import asyncio, sys, os
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
evaluator_o = role_opts("Du bist Evaluator. Prüfe den Code gegen die Spec. Erste Zeile NUR 'PASS' oder 'FAIL: <Grund>'.")

async def run(opts, prompt):
    out = []
    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    out.append(b.text)
    return "\n".join(out)

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
            print(f"\n=== EVALUATOR (Runde {rnd}) ===")
            verdict = await run(evaluator_o, f"Spec:\n{plan}\n\nCode:\n{code}")
            print(verdict[:300])
            if verdict.strip().upper().startswith("PASS"):
                print(f"\n*** PASS in Runde {rnd} ***")
                return
            plan += f"\n\nEvaluator-Feedback: {verdict}"
        print("\n*** kein PASS nach 3 Runden -> Mensch entscheidet ***")
    except Exception as e:  # max_turns/max_budget wirft
        print(f"FAIL: abgebrochen ({e})")

asyncio.run(main())
