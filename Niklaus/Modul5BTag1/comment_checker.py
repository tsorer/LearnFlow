"""Prueft vor dem Commit, ob deutsche Kommentare im Code stehen.

    python comment_checker.py            # prueft den Staging-Bereich
    python comment_checker.py --alle     # prueft auch die Zweifelsfaelle ohne Modell

Exit-Code 1, wenn etwas zu uebersetzen ist — damit taugt das Skript als
Pre-Commit-Hook.

Aufbau wie third_agent.py: die Logik steht in `comment_rules.py` und ist ohne
SDK testbar, die Wrapper hier enthalten nur Schema, Datenbeschaffung und
Fehlerbehandlung.

Die Arbeitsteilung ist der eigentliche Punkt dieses Agents:

    Python entscheidet, was eindeutig ist    -> kostet nichts, immer gleich
    Das Modell entscheidet die Zweifelsfaelle -> kostet, aber nur dort

Ist der Staging-Bereich sauber oder enthaelt er nur eindeutige Faelle ohne
Zweifel, wird **kein Modell aufgerufen**. Ein Pruefer, der bei jedem Commit
Geld kostet, wird abgeschaltet.

Das Modell bekommt kein Read und kein Bash — nur die beiden Tools. Es kann
also nicht im Repo herumsuchen, sondern urteilt ueber genau die Kommentare,
die aus dem Staging-Bereich kommen.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Annotated

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

import comment_rules

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).parent.parent.parent  # Niklaus/Modul5BTag1 -> LearnFlow


# ── Datenbeschaffung ───────────────────────────────────────────

def lauf(*befehl: str) -> str:
    fertig = subprocess.run(
        befehl, cwd=REPO, capture_output=True, text=True, encoding="utf-8", timeout=60
    )
    if fertig.returncode != 0:
        raise RuntimeError(f"{' '.join(befehl)}: {fertig.stderr.strip()}")
    return fertig.stdout


def gestagte_funde() -> list[comment_rules.Fund]:
    """Kommentare aus dem, was gerade committet werden soll.

    Gelesen wird der gestagte Blob (`git show :pfad`), nicht die Datei auf der
    Platte: wer eine Aenderung teilweise staged, committet auch nur diesen Teil.
    """
    roh = lauf("git", "diff", "--cached", "--name-only", "--diff-filter=ACM").strip()
    funde: list[comment_rules.Fund] = []
    for pfad in filter(None, roh.splitlines()):
        if not comment_rules.unterstuetzt(pfad):
            continue
        try:
            inhalt = lauf("git", "show", f":{pfad}")
        except RuntimeError:
            continue
        funde.extend(comment_rules.pruefe_datei(pfad, inhalt))
    return funde


# ── Die zwei Tools ─────────────────────────────────────────────

@tool(
    "staged_comments",
    "Liefert alle Kommentare und Docstrings aus dem Staging-Bereich, bei denen "
    "deutsche Marker gefunden wurden — mit datei:zeile, Text, Signalen und "
    "Einstufung (sicher/verdaechtig). IMMER zuerst aufrufen; die Kommentare "
    "nicht aus dem Auftragstext rekonstruieren.",
    {},
)
async def staged_comments(args):
    try:
        funde = gestagte_funde()
    except RuntimeError as exc:
        return {"content": [{"type": "text", "text": f"Staging nicht lesbar: {exc}"}], "is_error": True}

    nutzlast = [
        {
            "ort": f"{f.datei}:{f.zeile}",
            "art": f.art,
            "text": f.text,
            "signale": list(f.signale),
            "einstufung": f.einstufung,
        }
        for f in funde
    ]
    return {"content": [{"type": "text", "text": json.dumps(nutzlast, ensure_ascii=False, indent=1)}]}


@tool(
    "language_signals",
    "Gibt die deterministischen Deutsch-Marker eines einzelnen Textes zurueck "
    "(Umlaute, Stoppwoerter, transliterierte Formen) samt Einstufung. Fuer "
    "Zweifelsfaelle und fuer die Gegenprobe einer vorgeschlagenen englischen "
    "Fassung — die soll keine Marker mehr enthalten.",
    {"text": Annotated[str, "Der zu pruefende Kommentartext"]},
)
async def language_signals(args):
    text = args.get("text", "")
    if not text:
        return {"content": [{"type": "text", "text": "Leerer Text."}], "is_error": True}
    sig = comment_rules.signale(text)
    nutzlast = {"signale": list(sig), "einstufung": comment_rules.einstufen(sig)}
    return {"content": [{"type": "text", "text": json.dumps(nutzlast, ensure_ascii=False)}]}


sprache = create_sdk_mcp_server(
    name="sprache", version="1.0.0", tools=[staged_comments, language_signals]
)

SYSTEM = """Du pruefst vor einem Commit, ob deutsche Kommentare im Code stehen.

Konvention: Kommentare und Docstrings im Code sind englisch. Deutsch bleibt
Docs/, Ops/, README, PR-Texten und Issues vorbehalten.

Nicht zu beanstanden:
- deutsche Fachbegriffe in einem sonst englischen Satz (Bereichsverantwortlicher,
  Konfidenz-Schwelle, Lernkorpus) — der Satz zaehlt, nicht das einzelne Wort
- Eigennamen, Datei- und Feldnamen
- zitierte deutsche Meldungstexte, wenn der Kommentar sie als Zitat kennzeichnet

Ablauf: staged_comments aufrufen. Eintraege mit Einstufung "sicher" sind
deutsch, darueber musst du nicht nachdenken. Bei "verdaechtig" entscheidest du:
ist der Satz deutsch oder englisch mit einem Fachbegriff? Fuer jeden deutschen
Kommentar schlaegst du eine englische Fassung vor, die denselben Inhalt sagt —
nicht Wort fuer Wort, sondern was gemeint ist. Pruefe deinen Vorschlag mit
language_signals gegen: er darf keine Marker mehr ausloesen.

Antworte knapp und genau in dieser Form:

datei:zeile
  ist:  <der deutsche Text>
  neu:  <dein englischer Vorschlag>

Am Ende genau eine Zeile:
ERGEBNIS: sauber
oder
ERGEBNIS: <n> zu uebersetzen

Keine Vorrede, keine Zusammenfassung, keine Verbesserungsvorschlaege zum Code
selbst."""

opts = ClaudeAgentOptions(
    model="claude-sonnet-4-6",
    mcp_servers={"sprache": sprache},
    allowed_tools=["mcp__sprache__staged_comments", "mcp__sprache__language_signals"],
    system_prompt=SYSTEM,
    max_turns=20,
    max_budget_usd=0.30,
)


async def frage_modell() -> str:
    letzte = ""
    async for msg in query(prompt="Pruefe den Staging-Bereich.", options=opts):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, ToolUseBlock):
                    print(f">>> TOOL-CALL: {block.name}")
                elif isinstance(block, TextBlock):
                    print(block.text)
                    letzte = block.text
        elif isinstance(msg, ResultMessage):
            print(f"\n--- Turns: {msg.num_turns} · Kosten: ${msg.total_cost_usd:.4f} ---")
    return letzte


def main() -> int:
    try:
        funde = gestagte_funde()
    except RuntimeError as exc:
        print(f"Staging nicht lesbar: {exc}")
        return 2

    sicher = [f for f in funde if f.einstufung == "sicher"]
    zweifel = [f for f in funde if f.einstufung == "verdaechtig"]
    print(f"Gestagte Funde: {len(sicher)} sicher, {len(zweifel)} verdaechtig")

    if not funde:
        print("Sauber — kein Modell aufgerufen, keine Kosten.")
        return 0

    for f in sicher:
        print(f"  sicher      {f.datei}:{f.zeile}  {f.text[:70]}")
    for f in zweifel:
        print(f"  verdaechtig {f.datei}:{f.zeile}  {f.text[:70]}")

    if "--alle" in sys.argv:
        # Ohne Modell: nur die deterministische Haelfte, fuer schnelle Laeufe
        # und fuer die CI, wo niemand auf ein Urteil warten will.
        return 1 if sicher else 0

    print("\n── Modell urteilt ueber die Zweifelsfaelle und schlaegt Englisch vor ──\n")
    letzte = asyncio.run(frage_modell())

    # Blockieren tut die deterministische Haelfte. Das Modell darf zusaetzlich
    # blockieren (wenn es einen Zweifelsfall als deutsch einstuft), aber ein
    # eindeutiger Fund bleibt ein Fund, egal was es sagt.
    modell_meldet = "ERGEBNIS: sauber" not in letzte
    return 1 if (sicher or modell_meldet) else 0


if __name__ == "__main__":
    raise SystemExit(main())
