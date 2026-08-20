"""Trockenlauf der PGE-Konfiguration — ohne Modell, ohne Key, ohne Kosten.

    python smoke_pge.py

Prueft, was am Aufbau schiefgehen kann, bevor ein bezahlter Lauf startet:
Minimalrechte, Registrierung der drei Subagenten, Deckel auf beiden Ebenen.

Der wichtigste Fall ist Nummer 2: `agents=` gesetzt, aber "Agent" nicht in
`tools`. Das faellt zur Laufzeit NICHT auf — die Delegation findet dann
einfach nicht statt, ohne Fehlermeldung.
"""

import sys

import test_pge
from test_pge import opts

ROLLEN = ("planner", "generator", "evaluator")

fehler: list[str] = []


def pruefe(name: str, bedingung: bool, hinweis: str = "") -> None:
    if not bedingung:
        fehler.append(f"{name}{': ' + hinweis if hinweis else ''}")
    print(f"{'ok    ' if bedingung else 'FEHLER'} {name}")


# ── 1. Minimalrechte des Orchestrators ─────────────────────────
# `[]` und `None` sehen gleich harmlos aus, bedeuten aber das Gegenteil:
# bei skills/setting_sources heisst None "CLI-Standard", also alles.
pruefe("tools nur ['Agent']", opts.tools == ["Agent"], f"{opts.tools}")
pruefe("skills leer (nicht None)", opts.skills == [], f"{opts.skills!r}")
pruefe("setting_sources leer (nicht None)", opts.setting_sources == [], f"{opts.setting_sources!r}")
pruefe("strict_mcp_config", opts.strict_mcp_config is True)
pruefe("allowed_tools nur ['Agent']", opts.allowed_tools == ["Agent"], f"{opts.allowed_tools}")


# ── 2. Delegation ist ueberhaupt moeglich ──────────────────────
pruefe("agents registriert", bool(opts.agents))
pruefe("alle drei Rollen da", set(opts.agents or {}) == set(ROLLEN), f"{list(opts.agents or {})}")
pruefe(
    "Agent-Tool verfuegbar (sonst tote Konfiguration)",
    "Agent" in (opts.tools or []),
)


# ── 3. Die Subagenten ──────────────────────────────────────────
for rolle in ROLLEN:
    sub = (opts.agents or {}).get(rolle)
    if sub is None:
        continue
    pruefe(f"{rolle}: kein Tool noetig", sub.tools == [], f"{sub.tools}")
    pruefe(f"{rolle}: skills leer", sub.skills == [], f"{sub.skills!r}")
    gesperrt = sub.disallowedTools or []
    pruefe(
        f"{rolle}: Bash und Agent gesperrt",
        all(n in gesperrt for n in ("Bash", "bash", "Agent")),
        f"{gesperrt}",
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
    pruefe(f"System-Prompt nennt {rolle}", rolle in test_pge.SYSTEM)
pruefe("System-Prompt verlangt ERGEBNIS-Zeile", "ERGEBNIS:" in test_pge.SYSTEM)


print()
if fehler:
    print(f"{len(fehler)} Abweichung(en):")
    for f in fehler:
        print(f"  {f}")
    sys.exit(1)
print("PGE-Konfiguration wie erwartet — kein Modell aufgerufen, keine Kosten.")
