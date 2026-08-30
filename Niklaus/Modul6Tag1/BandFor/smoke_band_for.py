"""Trockenlauf der band_for-Konfiguration — ohne Modell, ohne Key, ohne Kosten.

    python smoke_band_for.py

Prueft, was am Aufbau schiefgehen kann, bevor ein bezahlter Lauf startet:
Minimalrechte, Registrierung der drei Subagenten, Deckel auf beiden Ebenen.

Der wichtigste Fall ist Nummer 2: `agents=` gesetzt, aber "Agent" nicht in
`tools`. Das faellt zur Laufzeit NICHT auf — die Delegation findet dann
einfach nicht statt, ohne Fehlermeldung.
"""

import asyncio
import sys

from claude_agent_sdk import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)

import test_band_for
from test_band_for import opts

ROLLEN = ("planner", "generator", "evaluator")

fehler: list[str] = []


def pruefe(name: str, bedingung: bool, hinweis: str = "") -> None:
    if not bedingung:
        fehler.append(f"{name}{': ' + hinweis if hinweis else ''}")
    print(f"{'ok    ' if bedingung else 'FEHLER'} {name}")


# ── 1. Minimalrechte des Orchestrators ─────────────────────────
# `[]` und `None` sehen gleich harmlos aus, bedeuten aber das Gegenteil:
# bei skills/setting_sources heisst None "CLI-Standard", also alles.
# Sessionweite Basismenge: Agent (Delegation) + Read/Write (fuer die Subagenten).
pruefe("tools = Agent + Read/Write", opts.tools == ["Agent", "Read", "Write"], f"{opts.tools}")
pruefe("skills leer (nicht None)", opts.skills == [], f"{opts.skills!r}")
pruefe("setting_sources leer (nicht None)", opts.setting_sources == [], f"{opts.setting_sources!r}")
pruefe("strict_mcp_config", opts.strict_mcp_config is True)
# Leer, nicht ["Agent"]: nichts wird ueber eine Allow-Regel auto-genehmigt.
pruefe("allowed_tools leer", opts.allowed_tools == [], f"{opts.allowed_tools}")
# Zwei Ebenen: PreToolUse-Hook (sieht jeden Aufruf) + can_use_tool (Permission).
pruefe("PreToolUse-Hook registriert", "PreToolUse" in (opts.hooks or {}), f"{list(opts.hooks or {})}")
pruefe("can_use_tool gesetzt", opts.can_use_tool is not None)
# Subagent-Text wird geforwardet, damit das Evaluator-Urteil in der Konsole landet.
pruefe("forward_subagent_text an", opts.forward_subagent_text is True)


# ── 2. Delegation ist ueberhaupt moeglich ──────────────────────
pruefe("agents registriert", bool(opts.agents))
pruefe("alle drei Rollen da", set(opts.agents or {}) == set(ROLLEN), f"{list(opts.agents or {})}")
pruefe(
    "Agent-Tool verfuegbar (sonst tote Konfiguration)",
    "Agent" in (opts.tools or []),
)


# ── 3. Die Subagenten ──────────────────────────────────────────
# Jede Rolle bekommt genau die Datei-Tools, die sie braucht — nicht mehr.
ERWARTETE_TOOLS = {
    "planner": ["Write"],
    "generator": ["Read", "Write"],
    "evaluator": ["Read", "Write"],
}
for rolle in ROLLEN:
    sub = (opts.agents or {}).get(rolle)
    if sub is None:
        continue
    pruefe(f"{rolle}: Tools wie erwartet", sub.tools == ERWARTETE_TOOLS[rolle], f"{sub.tools}")
    pruefe(f"{rolle}: skills leer", sub.skills == [], f"{sub.skills!r}")
    gesperrt = sub.disallowedTools or []
    pruefe(
        f"{rolle}: Bash und Agent gesperrt",
        all(n in gesperrt for n in ("Bash", "bash", "Agent")),
        f"{gesperrt}",
    )
    # Eine Sperrliste schlaegt jede Freigabe: stuenden Read/Write hier drin,
    # koennte der Subagent sie trotz `tools=` nicht nutzen.
    pruefe(
        f"{rolle}: gewaehrte Tools nicht gesperrt",
        not (set(sub.tools) & set(gesperrt)),
        f"{sorted(set(sub.tools) & set(gesperrt))}",
    )
    pruefe(f"{rolle}: Turn-Deckel", bool(sub.maxTurns) and sub.maxTurns <= 6, f"{sub.maxTurns}")
    pruefe(f"{rolle}: Modell gesetzt", bool(sub.model), f"{sub.model!r}")
    # Die Beschreibung steuert die AUSWAHL durch den Orchestrator. Ist sie leer
    # oder nichtssagend, waehlt er den Subagenten nie oder den falschen.
    pruefe(f"{rolle}: description brauchbar", len(sub.description) > 40)


# ── 4. Deckel ──────────────────────────────────────────────────
pruefe("max_turns gesetzt", bool(opts.max_turns) and opts.max_turns <= 12, f"{opts.max_turns}")
pruefe("max_budget_usd gesetzt", bool(opts.max_budget_usd), f"{opts.max_budget_usd}")


# ── 5. Der Orchestrator delegiert wirklich ─────────────────────
# Kein Beweis, aber ein Riegel gegen das stille Umschreiben des Prompts:
# stehen die Rollennamen nicht drin, kann er sie nicht ansprechen.
for rolle in ROLLEN:
    pruefe(f"System-Prompt nennt {rolle}", rolle in test_band_for.SYSTEM)
pruefe("System-Prompt verlangt ERGEBNIS-Zeile", "ERGEBNIS:" in test_band_for.SYSTEM)


# ── 6. Die zwei Sicherheits-Ebenen, direkt geprueft (ohne Modell) ──
# WICHTIG: es wird NIE etwas ausgefuehrt — beide Funktionen lesen den Text nur
# und geben allow/deny zurueck. Kein subprocess, keine Shell, es wird keine
# Datei angefasst. Die Fremd-Pfade dienen nur der Pfadpruefung.
ERLAUBT = str(test_band_for.CWD / "spec.md")            # eines der drei Artefakte
FREMD = str(test_band_for.CWD.parent / "ausbruch.md")   # eine Ebene darueber


# (2) PreToolUse-Hook: loggt jeden Aufruf (a) und sperrt Verletzungen (b).
def _hook_decision(tool: str, tool_input: dict) -> object:
    inp = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
        "tool_use_id": "smoke",
    }
    out = asyncio.run(test_band_for.log_and_guard(inp, "smoke", {"signal": None}))
    return out.get("hookSpecificOutput", {}).get("permissionDecision")


pruefe(
    "hook laesst Delegation an eine unserer Rollen durch (planner)",
    _hook_decision("Agent", {"subagent_type": "planner"}) != "deny",
)
pruefe(
    "hook sperrt Delegation an fremden Typ (claude)",
    _hook_decision("Agent", {"subagent_type": "claude"}) == "deny",
)
pruefe(
    "hook erlaubt Write auf ein Artefakt (spec.md)",
    _hook_decision("Write", {"file_path": ERLAUBT, "content": "x"}) != "deny",
)
pruefe(
    "hook erlaubt Read relativ (code.py)",
    _hook_decision("Read", {"file_path": "code.py"}) != "deny",
)
pruefe(
    "hook sperrt Write ausserhalb (Traversal)",
    _hook_decision("Write", {"file_path": FREMD, "content": "x"}) == "deny",
)
pruefe(
    "hook sperrt Read fremder Datei im CWD (geheim.txt)",
    _hook_decision("Read", {"file_path": "geheim.txt"}) == "deny",
)
pruefe(
    "hook sperrt fremdes Werkzeug (Bash)",
    _hook_decision("Bash", {"command": "echo hi"}) == "deny",
)
pruefe(
    "hook protokolliert jeden Aufruf (Audit)",
    len(test_band_for.audit_log) >= 6,
    f"{len(test_band_for.audit_log)}",
)
# Der Hook feuert auch INNERHALB eines Subagenten und ordnet den Aufruf per
# agent_id zu. Simuliert, weil die Subagenten im Trockenlauf nichts aufrufen.
asyncio.run(
    test_band_for.log_and_guard(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": ERLAUBT, "content": "x"},
            "tool_use_id": "smoke",
            "agent_id": "planner",
        },
        "smoke",
        {"signal": None},
    )
)
pruefe(
    "hook attribuiert Subagent-Aufruf (agent_id)",
    test_band_for.audit_log[-1][2] == "planner",
    f"{test_band_for.audit_log[-1]}",
)


# (1) can_use_tool: die Permission-Ebene, als zweiter Riegel.
def _perm(tool: str, eingabe: dict) -> object:
    ctx = ToolPermissionContext(tool_use_id="smoke")
    return asyncio.run(test_band_for.gate(tool, eingabe, ctx))


pruefe(
    "gate erlaubt Write auf ein Artefakt",
    isinstance(_perm("Write", {"file_path": ERLAUBT, "content": "x"}), PermissionResultAllow),
)
pruefe(
    "gate sperrt Write ausserhalb",
    isinstance(_perm("Write", {"file_path": FREMD, "content": "x"}), PermissionResultDeny),
)


print()
if fehler:
    print(f"{len(fehler)} Abweichung(en):")
    for f in fehler:
        print(f"  {f}")
    sys.exit(1)
print("band_for-Konfiguration wie erwartet — kein Modell aufgerufen, keine Kosten.")
