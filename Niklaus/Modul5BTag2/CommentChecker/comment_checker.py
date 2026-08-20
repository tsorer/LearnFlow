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

Findet die Regel gar nichts, wird **kein Modell aufgerufen** — der haeufigste
Fall im Alltag kostet also nichts. Ein Pruefer, der bei jedem Commit Geld
kostet, wird abgeschaltet.

Was die Einstufung dagegen NICHT tut: den Aufruf sparen. Sobald irgendein Fund
da ist, laeuft das Modell — auch wenn alle Funde `sicher` sind. Es hat zwei
Aufgaben, und nur die erste haengt am Zweifel:

    verdaechtig  ist das Deutsch oder Englisch mit Fachbegriff?  -> Urteil
    sicher       schon entschieden                               -> nur uebersetzen

Bei `sicher` ueberspringt das Modell die Urteilsfrage und schreibt bloss die
englische Fassung. Das spart Tokens innerhalb des Laufs, nicht den Lauf.

Der Unterschied liegt woanders, naemlich beim Exit-Code: `sicher` blockiert
bedingungslos. Das Modell darf zusaetzlich blockieren, aber einen eindeutigen
Fund nicht wegreden.

Dieselbe Aufteilung noch einmal, eine Ebene hoeher — zwischen teurem und
billigem Modell:

    Haupt-Agent (Sonnet)   urteilt ueber die Zweifelsfaelle
    Subagent (Haiku)       schreibt die englischen Fassungen

Uebersetzen ist Routine, Beurteilen nicht. Der Subagent bekommt `staged_comments`
nicht — er sieht den Staging-Bereich gar nicht, sondern nur den Text, den ihm
der Haupt-Agent uebergibt.

Umgekehrt gilt das NICHT: der Haupt-Agent kann `language_signals` sehr wohl
aufrufen. MCP-Tools sind ueber `mcp_servers` verfuegbar, und `allowed_tools`
regelt nur die Rueckfrage. Wer ihn wirklich fernhalten wollte, braeuchte zwei
getrennte MCP-Server. Die Rollentrennung ist hier also im Prompt beschrieben und
beim Subagenten durchgesetzt, beim Haupt-Agenten dagegen nur beschrieben.

Das Modell bekommt kein Read und kein Bash — nur die beiden Tools. Es kann
also nicht im Repo herumsuchen, sondern urteilt ueber genau die Kommentare,
die aus dem Staging-Bereich kommen.

Durchgesetzt wird das von `tools=[]`, nicht von `allowed_tools`. Die beiden
Felder sehen aehnlich aus und tun Verschiedenes:

    tools          welche eingebauten Tools es UEBERHAUPT GIBT
    allowed_tools  welche davon OHNE RUECKFRAGE benutzt werden duerfen

Steht ein Tool nicht in `allowed_tools`, ist es trotzdem im Kontext des
Modells und kann angefordert werden. Erst `tools=[]` nimmt die eingebauten
Tools aus der Auswahl. Dieselbe Unterscheidung gilt fuer `skills` und
`setting_sources` — Details bei den Optionen weiter unten.
"""

import asyncio
import json
import sys
from typing import Annotated

from claude_agent_sdk import (
    AgentDefinition,
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
import staging

sys.stdout.reconfigure(encoding="utf-8")


# ── Zusammenfuehrung ───────────────────────────────────────────
# Die beiden Haelften wissen nichts voneinander: `staging` kennt Git und keine
# Kommentare, `comment_rules` kennt Sprache und kein Git. Hier treffen sie sich
# — und mehr als diese drei Zeilen darf die Naht nicht sein.

def gestagte_funde() -> list[comment_rules.Fund]:
    """Kommentare aus dem, was gerade committet werden soll."""
    funde: list[comment_rules.Fund] = []
    for pfad, inhalt in staging.gestagte_dateien(comment_rules.unterstuetzt):
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

# ── Subagent: die Routine-Rolle ────────────────────────────────
# Die Arbeitsteilung des Checkers, eine Ebene hoeher gezogen:
#
#     Python  <-> Modell     was eindeutig ist <-> was Urteil braucht
#     Sonnet  <-> Haiku      urteilen          <-> uebersetzen
#
# Beurteilen ist selten und schwierig, uebersetzen haeufig und Routine. Der
# Subagent laeuft deshalb auf dem billigen Modell.
#
# `tools` ist hier abschliessend — er bekommt NICHT `staged_comments`. Er kann
# den Staging-Bereich also gar nicht sehen, sondern nur den Text bearbeiten,
# den ihm der Haupt-Agent im Auftrag uebergibt. Minimalrechte auf der zweiten
# Ebene, mit derselben Begruendung wie auf der ersten.

UEBERSETZER = AgentDefinition(
    description=(
        "Schreibt zu deutschen Code-Kommentaren die englische Fassung und prueft "
        "sie gegen. IMMER nutzen, sobald uebersetzt werden soll — nicht selbst "
        "uebersetzen."
    ),
    prompt=(
        "Du uebersetzt Code-Kommentare ins Englische. Nicht Wort fuer Wort, "
        "sondern was gemeint ist: der Satz soll dasselbe sagen, in der Sprache, "
        "die ein Entwickler im Code erwartet.\n\n"
        "Pruefe jeden Vorschlag mit language_signals gegen. Loest er noch Marker "
        "aus, formuliere neu und pruefe erneut.\n\n"
        "Antworte nur mit den Uebersetzungen, eine pro Zeile:\n"
        "    <datei:zeile>\\t<englische Fassung>\n"
        "Keine Vorrede, keine Begruendung, keine Rueckfragen."
    ),
    tools=["mcp__sprache__language_signals"],
    # Sperrliste zusaetzlich zur Positivliste. Im ersten scharfen Lauf tauchte
    # nach einer Delegation ein `bash`-Aufruf im Stream auf — mit `tools` wie
    # oben sollte das nicht moeglich sein. Solange die Ursache nicht geklaert
    # ist, wird explizit zugesperrt: eine Sperrliste schlaegt jede Freigabe.
    # `Agent` steht bewusst mit drin — der Subagent soll nicht weiterdelegieren.
    disallowedTools=["Bash", "bash", "Read", "Write", "Edit", "Grep", "Glob", "Agent"],
    mcpServers=["sprache"],
    skills=[],
    model="haiku",
    maxTurns=10,
)

SYSTEM = """Du pruefst vor einem Commit, ob deutsche Kommentare im Code stehen.

Konvention: Kommentare und Docstrings im Code sind englisch. Deutsch bleibt
Docs/, Ops/, README, PR-Texten und Issues vorbehalten.

Nicht zu beanstanden:
- deutsche Fachbegriffe in einem sonst englischen Satz (Bereichsverantwortlicher,
  Konfidenz-Schwelle, Lernkorpus) — der Satz zaehlt, nicht das einzelne Wort
- Eigennamen, Datei- und Feldnamen
- zitierte deutsche Meldungstexte, wenn der Kommentar sie als Zitat kennzeichnet

Ablauf:

1. staged_comments aufrufen. Die Kommentare nicht aus dem Auftragstext
   rekonstruieren.
2. Eintraege mit Einstufung "sicher" sind deutsch — darueber musst du nicht
   nachdenken. Bei "verdaechtig" entscheidest du: ist der Satz deutsch, oder
   englisch mit einem deutschen Fachbegriff?
3. Alle deutschen Kommentare EINMAL gesammelt an den Subagent `uebersetzer`
   geben, mit Ort und Text. Du uebersetzt nicht selbst — auch dann nicht, wenn
   es dir leichtfaellt. Ein Auftrag fuer alle, nicht einer pro Kommentar.

Antworte knapp und genau in dieser Form:

datei:zeile
  ist:  <der deutsche Text>
  neu:  <die englische Fassung des Subagents>

Am Ende genau eine Zeile:
ERGEBNIS: sauber
oder
ERGEBNIS: <n> zu uebersetzen

Keine Vorrede, keine Zusammenfassung, keine Verbesserungsvorschlaege zum Code
selbst."""

# `allowed_tools` ist die Erlaubnis der SESSION — sie gilt auch fuer den
# Subagenten. Seine `tools`-Liste sagt nur, was er sehen darf; ob er es benutzen
# darf, steht hier.
#
# Das kostete den ersten scharfen Lauf: `language_signals` fehlte hier, weil der
# Haupt-Agent es nicht brauchen sollte. Der Subagent durfte es daraufhin nicht
# aufrufen, hat dreimal neu delegiert und am Ende ohne Gegenprobe geliefert.
#
# Und der Nebeneffekt, den ich mir davon versprochen hatte, trat gar nicht ein:
# MCP-Tools sind ueber `mcp_servers` verfuegbar, unabhaengig von `allowed_tools`.
# Der Haupt-Agent konnte `language_signals` die ganze Zeit aufrufen — es wurde
# nur nachgefragt. Fernhalten liesse er sich nur ueber `disallowed_tools`, und
# das traefe den Subagenten mit.
#
# `Agent` ist das Delegations-Tool — ohne den Eintrag waere `agents=` tote
# Konfiguration.
TOOL_NAMEN = [
    "mcp__sprache__staged_comments",
    "mcp__sprache__language_signals",
    "Agent",
]

opts = ClaudeAgentOptions(
    model="claude-sonnet-4-6",
    cwd=str(staging.WURZEL),

    # ── Verfuegbarkeit: was es fuer dieses Modell ueberhaupt gibt ──
    # Vier getrennte Quellen, aus denen sonst Tools hereinkommen. Jede muss
    # einzeln geschlossen werden; keine davon deckt eine andere mit ab.
    tools=["Agent"],        # NUR das Delegations-Tool. Kein Read, kein Bash,
                            # kein Write. Das ist der Preis des Subagents: die
                            # Liste ist nicht mehr leer, aber sie ist bewusst
                            # genau einen Eintrag lang.
    skills=[],              # keine Skills. None waere NICHT "aus", sondern
                            # "CLI-Standard" — also alle gefundenen Skills.
    setting_sources=[],     # nichts von der Platte: keine CLAUDE.md, keine
                            # .claude/agents, keine settings.json
    strict_mcp_config=True, # nur der Server unten, kein .mcp.json aus dem Projekt

    # ── Erlaubnis: was davon ohne Rueckfrage laufen darf ──
    mcp_servers={"sprache": sprache},
    agents={"uebersetzer": UEBERSETZER},
    allowed_tools=TOOL_NAMEN,

    system_prompt=SYSTEM,

    # Ein Aufruf von staged_comments, ein paar Gegenproben, die Antwort. 20 war
    # grosszuegig fuer etwas, das bei jedem Commit laeuft; 10 laesst Luft fuer
    # viele Zweifelsfaelle und deckelt trotzdem.
    max_turns=10,
    max_budget_usd=0.30,
)

# Bewusst NICHT benutzt: can_use_tool. Der Callback verlangt den Streaming-Modus
# (mit `query(prompt="…")` wirft das SDK), und Tools aus `allowed_tools` werden
# ohnehin auto-erlaubt und erreichen ihn gar nicht. Nach `tools=[]` und
# `skills=[]` bleibt nichts uebrig, was er noch ablehnen koennte.


async def frage_modell() -> str:
    letzte = ""
    async for msg in query(prompt="Pruefe den Staging-Bereich.", options=opts):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, ToolUseBlock):
                    if block.name == "Agent":
                        # Sichtbar machen, WELCHE Definition gezogen wird — ein
                        # falscher subagent_type faellt sonst nicht auf.
                        ziel = block.input.get("subagent_type")
                        print(f">>> DELEGIERT an Subagent: {ziel!r}")
                    else:
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
