"""Baut Block 2 (Technischer Aufbau) neu — drei Wege durch das System, rund 9 Minuten.

Nicht die Fortsetzung von `build_block2.py`: dort war der Block zu 100 % die
Antwort-Pipeline. Hier führt die Landkarte drei Wege ein (Wissen hinein, Frage →
Antwort, Fragen hinaus) und schliesst mit den Belegen. Übernommen wird das
Layout, nicht der Inhalt — jede Folie ist neu geschrieben, weil die alten Folien
für diese Erzählung die falsche Detaildichte hatten.

Wiederkehrendes Muster: Auf möglichst jeder Folie steht, was gut funktioniert
(`learning`, türkis), was nicht (`learning bad`, koralle) oder was überrascht
hat (`learning aha`, amber).

Ordner (relativ zu dieser Datei):
    ../Archive/Block2_Technischer-Aufbau.html   Vorlage: CSS, Navigation, Architektur-SVG
    ../Archive/2026-09-20/Block2_Technischer-Aufbau.html   Ergebnis (archiviert 20.09.)
    ../assets/                                  Bilder (bei Bedarf aus Archive kopiert)

Alle Zahlen sind belegt: ../Pipeline-Trace/ (Q1.json, Q2.json, README.md),
../Archive/Block2_Notizen.md, Docs/04_ADR-008/009, Issue #142.

Aufruf:  python build_block2_v3.py
"""

import re
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
TEMPLATE = BASE / "Archive" / "Block2_Technischer-Aufbau.html"
OUT = BASE / "Archive" / "2026-09-20" / "Block2_Technischer-Aufbau.html"

if not (BASE / "assets").exists() and (BASE / "Archive" / "assets").exists():
    shutil.copytree(BASE / "Archive" / "assets", BASE / "assets")

v1 = TEMPLATE.read_text(encoding="utf-8")
head, rest = v1.split('  <main class="deck"', 1)
tail = rest[rest.index("  </main>") + len("  </main>"):]

# Das Architektur-Diagramm ist eine Grafik, kein Text: als Baustein übernommen.
ARCH_SVG = re.search(r'<svg class="arch".*?</svg>', v1, re.S).group(0)

EXTRA_CSS = """
    /* ── v3: drei Wege ───────────────────────────────────────────────── */
    .wrail { display: flex; gap: 6px; margin-bottom: 22px; }
    .wrail span {
      padding: 7px 12px; border-radius: 99px; background: rgba(16, 30, 54, .06); color: #9aa1ac;
      font-size: 13px; font-weight: 780; letter-spacing: .02em; white-space: nowrap;
    }
    .wrail span.done { background: var(--teal-pale); color: var(--teal-dark); }
    .wrail span.on { background: var(--ink); color: var(--white); }

    .learning.bad { border-left-color: var(--coral); }
    .learning.bad strong { color: var(--coral-dark); }
    .learning.aha { border-left-color: var(--amber); }
    .learning.aha strong { color: var(--amber-dark); }

    .panel.center { display: flex; flex-direction: column; justify-content: center; }

    .ways { display: grid; gap: 14px; }
    .way { display: grid; grid-template-columns: 52px 1fr; gap: 16px; align-items: start; padding: 17px 19px; border: 1px solid var(--line); border-radius: 18px; background: var(--white); }
    .way b { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 13px; background: var(--teal-pale); color: var(--teal-dark); font-size: 20px; font-weight: 850; }
    .way h3 { margin: 0 0 4px; color: var(--ink); font-size: 20px; font-weight: 820; letter-spacing: -.02em; }
    .way p { margin: 0 0 8px; color: var(--muted); font-size: 16.5px; font-weight: 620; line-height: 1.38; }
    .way .gate { display: inline-block; padding: 6px 12px; border-radius: 99px; background: var(--paper); color: var(--ink); font-size: 14.5px; font-weight: 800; }
    .way .gate.human { background: var(--amber-pale); color: var(--amber-dark); }
    .way .gate.eval { background: var(--teal-pale); color: var(--teal-dark); }

    .pipe { display: grid; gap: 9px; }
    .pipe > div { display: grid; grid-template-columns: 34px 1fr auto; gap: 14px; align-items: center; padding: 12px 15px; border: 1px solid var(--line); border-radius: 13px; background: var(--white); }
    .pipe b { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 9px; background: var(--paper); color: var(--muted); font-size: 15px; font-weight: 850; }
    .pipe h3 { margin: 0; color: var(--ink); font-size: 18px; font-weight: 760; }
    .pipe small { display: block; margin-top: 2px; color: var(--muted); font-size: 14.5px; font-weight: 620; }
    .pipe .tag { padding: 6px 11px; border-radius: 99px; background: var(--paper); color: var(--muted); font-size: 13px; font-weight: 800; white-space: nowrap; }
    .pipe .tag.llm { background: var(--ink); color: var(--white); }
    .pipe .tag.gate { background: var(--coral-pale); color: var(--coral-dark); }
    .pipe .tag.human { background: var(--amber-pale); color: var(--amber-dark); }

    .stat { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
    .stat div { padding: 15px 17px; border-radius: 15px; background: var(--paper); }
    .stat b { display: block; color: var(--teal-dark); font-size: 33px; font-weight: 850; letter-spacing: -.045em; line-height: 1; }
    .stat span { display: block; margin-top: 6px; color: var(--muted); font-size: 15px; font-weight: 680; line-height: 1.3; }

    .chip { display: inline-block; margin: 3px 4px 3px 0; padding: 7px 11px; border-radius: 10px; background: var(--white); border: 1px solid var(--line); color: var(--ink); font-size: 17px; font-weight: 720; }
    .chip small { display: block; margin-top: 2px; font-size: 12.5px; font-weight: 650; color: var(--muted); text-decoration: none; }
    .chip.out { color: #a3a9b2; text-decoration: line-through; border-style: dashed; background: transparent; }
    .chip.ok { background: var(--teal-pale); border-color: transparent; color: var(--teal-dark); }
    .chip.ok small { color: var(--teal-dark); }

    .law { margin: 0; padding: 18px 20px; border-radius: 16px; background: var(--white); border: 1px solid var(--line); font: 600 17px/1.55 var(--mono); color: var(--muted); white-space: pre-wrap; }
    .law .ans { color: var(--ink); font-weight: 800; background: #fcf3dc; padding: 0 4px; border-radius: 5px; }

    .vs { width: 100%; border-collapse: collapse; }
    .vs th { padding: 0 10px 9px; color: var(--muted); font-size: 12.5px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; text-align: left; }
    .vs td { padding: 11px 10px; border-top: 1px solid var(--line); color: var(--text); font-size: 17px; font-weight: 680; white-space: nowrap; }
    .vs td.l { color: var(--muted); font-size: 15.5px; font-weight: 700; }
    .vs td.v { font-variant-numeric: tabular-nums; font-weight: 800; color: var(--ink); }
    .vs td.ok { color: var(--teal-dark); font-weight: 820; }
    .vs td.warn { color: var(--amber-dark); font-weight: 820; }
    .vs tr.big td { font-size: 19px; }

    .chunkcut { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .chunkcut div { padding: 16px 18px; border-radius: 16px; background: var(--paper); font: 600 15.5px/1.5 var(--mono); color: var(--text); }
    .chunkcut div b { display: block; margin-bottom: 8px; font-family: Inter, sans-serif; font-size: 13px; font-weight: 820; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
    .chunkcut div .edge { color: var(--coral-dark); font-weight: 800; }
    .chunkline { margin-top: 12px; text-align: center; color: var(--muted); font-size: 15px; font-weight: 700; }

    .qcard { padding: 18px 20px; border-radius: 16px; background: var(--white); border: 1px solid var(--line); }
    .qcard .qq { color: var(--ink); font-size: 19px; font-weight: 800; line-height: 1.35; }
    .qcard ol { margin: 12px 0 0; padding-left: 22px; color: var(--text); font-size: 16.5px; font-weight: 620; line-height: 1.6; }
    .qcard li.right { color: var(--teal-dark); font-weight: 820; }
    .qcard .prov { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--line); color: var(--muted); font-size: 14.5px; font-weight: 680; }

    .gates { display: grid; gap: 10px; margin-top: 14px; }
    .gates div { display: grid; grid-template-columns: 1fr auto; gap: 14px; align-items: center; padding: 12px 16px; border-radius: 13px; background: var(--white); border: 1px solid var(--line); }
    .gates span { color: var(--ink); font-size: 16.5px; font-weight: 720; }
    .gates b { color: var(--teal-dark); font-size: 22px; font-weight: 850; font-variant-numeric: tabular-nums; }
    .gates small { display: block; color: var(--muted); font-size: 13.5px; font-weight: 640; }

    .evalcats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 14px; }
    .evalcats div { padding: 14px 15px; border-radius: 14px; background: var(--paper); }
    .evalcats b { display: block; color: var(--ink); font-size: 30px; font-weight: 850; letter-spacing: -.04em; line-height: 1; }
    .evalcats span { display: block; margin-top: 5px; color: var(--ink); font-size: 15px; font-weight: 760; }
    .evalcats small { display: block; margin-top: 3px; color: var(--muted); font-size: 13.5px; font-weight: 640; line-height: 1.3; }

    .close { display: grid; gap: 14px; }
    .close div { display: grid; grid-template-columns: 1fr auto; gap: 18px; align-items: center; padding: 20px 22px; border-radius: 18px; background: var(--white); border: 1px solid var(--line); }
    .close h3 { margin: 0 0 4px; color: var(--ink); font-size: 20px; font-weight: 820; }
    .close p { margin: 0; color: var(--muted); font-size: 16px; font-weight: 640; }
    .close em { font-style: normal; padding: 9px 16px; border-radius: 99px; font-size: 17px; font-weight: 850; white-space: nowrap; }
    .close em.m { background: var(--ink); color: var(--white); }
    .close em.h { background: var(--amber-pale); color: var(--amber-dark); }
    .close em.e { background: var(--teal-pale); color: var(--teal-dark); }
"""
marker = "\n    @media (prefers-reduced-motion: reduce)"
assert head.count(marker) == 1
head = head.replace(marker, EXTRA_CSS + marker)

WAYS = ["Landkarte", "A · Wissen hinein", "B · Frage → Antwort", "C · Fragen hinaus", "Belege"]


def rail(current: int) -> str:
    spans = []
    for i, name in enumerate(WAYS, 1):
        cls = "on" if i == current else ("done" if i < current else "")
        spans.append(f'<span class="{cls}">{name}</span>')
    return '<div class="wrail">' + "".join(spans) + "</div>"


def slide(label: str, story: str, panel: str, way: int = 0, center: bool = True) -> str:
    pcls = "panel center" if center else "panel"
    return f"""
    <section class="slide" aria-label="{label}">
      <header class="topbar">
        <div class="brand"><span class="brand-mark" aria-hidden="true">LF</span><span>LearnFlow</span></div>
        <div class="context" data-title="Technischer Aufbau"></div>
      </header>
      <div class="content">
        <div class="story">
          {rail(way) if way else ""}
          {story}
        </div>
        <div class="{pcls}">
          {panel}
        </div>
      </div>
      <div class="page-number"></div>
    </section>
"""


S = []

# ── Landkarte ────────────────────────────────────────────────────────────
S.append(slide("Architektur",
    """<div class="eyebrow">Landkarte</div>
          <h1>Vier Container. <span class="accent">Eine Datenbank.</span></h1>
          <p class="lead">Ein modularer Monolith in Docker Compose. Fragen laufen synchron durch die API, Dokumente verarbeitet ein Worker im Hintergrund — die beiden teilen kein Netz.</p>
          <div class="learning">
            <strong>Funktioniert gut</strong>
            Postgres macht vier Jobs gleichzeitig: Tabellen, Vektoren (pgvector), deutschen Volltext (tsvector) und die Warteschlange (pgqueuer). Kein Redis, keine zweite Datenbank — ein Backup, eine Transaktion, ein Ort für die Wahrheit.
          </div>""",
    f"""<div class="panel-label"><span>Container und Netze</span><span class="status">Docker Compose</span></div>
          {ARCH_SVG}""",
    way=1, center=False))

S.append(slide("Drei Wege",
    """<div class="eyebrow">Was gebaut wurde</div>
          <h1>Drei Wege durch <span class="accent">dasselbe System</span></h1>
          <p class="lead">Die Antwort-Pipeline ist der bekannteste Weg, aber nicht der einzige. Interessant ist, dass auf jedem Weg jemand anderes über die Qualität entscheidet.</p>
          <div class="learning">
            <strong>Der rote Faden</strong>
            Maschine prüft die Antwort. Mensch prüft die Frage. Messung prüft beides.
          </div>""",
    """<div class="panel-label"><span>Wer löst aus · was passiert · wer entscheidet</span></div>
          <div class="ways">
            <div class="way"><b>A</b><div><h3>Wissen hinein</h3><p>Stefan lädt ein Dokument hoch: parsen, stückeln, einbetten, indexieren.</p><span class="gate">Prüfung: das Stückeln</span></div></div>
            <div class="way"><b>B</b><div><h3>Frage hinein, Antwort heraus</h3><p>Lara fragt: suchen, mischen, prüfen, antworten, nachprüfen.</p><span class="gate">Prüfung: vier Stufen, fail-closed</span></div></div>
            <div class="way"><b>C</b><div><h3>Fragen hinaus</h3><p>Das System erzeugt Quizfragen aus dem Korpus.</p><span class="gate human">Prüfung: ein Mensch</span></div></div>
          </div>""",
    way=1))

# ── Weg A ────────────────────────────────────────────────────────────────
S.append(slide("Weg A Überblick",
    """<div class="eyebrow">Weg A · Wissen hinein</div>
          <h1>Bevor gefragt wird, muss <span class="accent">gelesen werden</span></h1>
          <p class="lead">Der Upload antwortet sofort, gearbeitet wird im Hintergrund: Die API legt einen Job in die Warteschlange, der Worker holt ihn. Den Fortschritt sieht Stefan in der Oberfläche.</p>
          <div class="learning">
            <strong>Funktioniert gut</strong>
            Die Herkunft entsteht schon beim Parsen: Jeder Block weiss, aus welcher Seite und welchem Absatz er stammt. Nur deshalb kann der Quellenlink aus der Demo die Stelle im Originaldokument markieren — nachträglich wäre das nicht zu rekonstruieren.
          </div>""",
    """<div class="panel-label"><span>Vom PDF zum durchsuchbaren Abschnitt</span><span class="status">Worker</span></div>
          <div class="pipe">
            <div><b>1</b><div><h3>Hochladen</h3><small>max. 10 MB, liegt als Datei in der Datenbank</small></div><span class="tag">API</span></div>
            <div><b>2</b><div><h3>Parsen</h3><small>PDF · DOCX · Markdown → Blöcke mit Seite und Absatz</small></div><span class="tag">Worker</span></div>
            <div><b>3</b><div><h3>Stückeln</h3><small>Blöcke → Abschnitte von rund 512 Tokens</small></div><span class="tag">Worker</span></div>
            <div><b>4</b><div><h3>Einbetten</h3><small>jeder Abschnitt wird zu 1536 Zahlen</small></div><span class="tag llm">Modell</span></div>
            <div><b>5</b><div><h3>Indexieren</h3><small>Vektor-Index und deutscher Volltext-Index</small></div><span class="tag">Datenbank</span></div>
          </div>
          <div class="panel-foot" style="margin-top:16px"><strong>Pilotkorpus:</strong> 4 Dokumente → 1017 Abschnitte. EU AI Act 525 · SAMW-Leitfaden 210 · SKOS-Richtlinien 200 · Ordnungsbussenverordnung 82.</div>""",
    way=2))

S.append(slide("Stückeln",
    """<div class="eyebrow">Weg A · Wissen hinein</div>
          <h1>Abschnitte, die an <span class="accent">natürlichen Kanten</span> enden</h1>
          <p class="lead">Geschnitten wird zuerst an Überschriften, dann an Absätzen, Sätzen, Zeilen — feiner nur, wenn ein Stück immer noch zu lang ist. Kein Abschnitt endet mitten im Satz.</p>
          <div class="learning">
            <strong>Funktioniert gut</strong>
            Gezählt wird mit demselben Tokenizer, den das Embedding-Modell benutzt. Sonst zählt man etwas anderes, als der Anbieter später abschneidet.
          </div>""",
    """<div class="panel-label"><span>Ordnungsbussenverordnung</span><span class="status">82 Abschnitte</span></div>
          <div class="stat">
            <div><b>512</b><span>Ziel-Grösse in Tokens</span></div>
            <div><b>64</b><span>Tokens Überlappung zum Nachbarn</span></div>
            <div><b>429</b><span>Median der 82 Abschnitte</span></div>
            <div><b>38 – 511</b><span>kürzester und längster Abschnitt</span></div>
          </div>
          <p class="listhead" style="margin:18px 0 8px; color:var(--muted); font-size:14px; font-weight:800; letter-spacing:.1em; text-transform:uppercase">Schnittkanten in dieser Reihenfolge</p>
          <div>
            <span class="chip ok">Überschrift</span><span class="chip">Absatz</span><span class="chip">Satz</span><span class="chip">Zeile</span><span class="chip">Wort</span>
          </div>""",
    way=2))

S.append(slide("Chunking Grenzen",
    """<div class="eyebrow">Weg A · Wissen hinein</div>
          <h1>Das Dokument bestimmt, <span class="accent">wo geschnitten wird</span></h1>
          <p class="lead">Innerhalb einer Seite überlappen zwei Abschnitte ungefähr einen Satz. Über einen Seitenwechsel hinweg gibt es keine Überlappung — die Seite ist eine harte Kante.</p>
          <div class="learning bad">
            <strong>Funktioniert nicht</strong>
            Der Satzsplitter liest «302.» als Satzende. Deshalb steht die Ziffernnummer am Ende des einen Abschnitts und ihr Text am Anfang des nächsten. Hier ist das harmlos — eine Tabelle über den Seitenumbruch wäre zerrissen.
          </div>""",
    """<div class="panel-label"><span>OBV · Abschnitt 25 und 26</span><span class="status warn">Seite 12</span></div>
          <div class="chunkcut">
            <div><b>Abschnitt 25 · Ende</b>… Höchstgeschwindigkeit<br>auf Autobahnen<br><span class="edge">302.</span></div>
            <div><b>Abschnitt 26 · Anfang</b><span class="edge">Überschreiten der …</span><br>303. Innerorts<br>a. 1–5 km/h …</div>
          </div>
          <div class="chunkline">139 Zeichen Überlappung innerhalb der Seite · 0 Zeichen über den Seitenwechsel</div>
          <div class="panel-foot" style="margin-top:16px"><strong>Für unsere Beispielfrage ging es gut aus:</strong> Ziffer 303.1 steht vollständig in Abschnitt 26 — mit Überschrift und allen drei Tabellenzeilen.</div>""",
    way=2))

# ── Weg B ────────────────────────────────────────────────────────────────
S.append(slide("Weg B Überblick",
    """<div class="eyebrow">Weg B · Frage → Antwort</div>
          <h1>Fünf Schritte, <span class="accent">neun Arten «Weiss ich nicht»</span></h1>
          <p class="lead">Jede Stufe hat ihren eigenen Grund zu unterdrücken — von «nichts Passendes gefunden» bis «erfundener Beleg». Genau ein Weg führt zu einer Antwort. Nur zwei Schritte rufen ein Sprachmodell.</p>
          <div class="learning">
            <strong>Das Prinzip: fail-closed</strong>
            Jede Stufe darf unterdrücken, keine darf aufwerten. «Weiss ich nicht» ist ein Ergebnis, kein Fehler.
          </div>""",
    """<div class="panel-label"><span>Ein Aufruf von <code>POST /api/query</code></span><span class="status">synchron</span></div>
          <div class="pipe">
            <div><b>1</b><div><h3>Suchen</h3><small>zwei Suchen parallel: nach Bedeutung und nach Wörtern</small></div><span class="tag">Embedding</span></div>
            <div><b>2</b><div><h3>Mischen</h3><small>zwei Ranglisten → fünf Abschnitte Kontext</small></div><span class="tag">Rechnen</span></div>
            <div><b>3</b><div><h3>Vorprüfung</h3><small>Stufe 0 und 1: Ist überhaupt etwas Passendes dabei?</small></div><span class="tag gate">Prüfung</span></div>
            <div><b>4</b><div><h3>Antworten</h3><small>nur aus diesen fünf Abschnitten, mit Quellennummern</small></div><span class="tag llm">Modell</span></div>
            <div><b>5</b><div><h3>Nachprüfen</h3><small>Stufe 2 und 3: Belege gültig? Aussage gedeckt?</small></div><span class="tag gate">Prüfung</span></div>
          </div>
          <div class="panel-foot" style="margin-top:16px"><strong>Neun Gründe zu schweigen:</strong> nichts gefunden · zu schwache Fundlage · Modell verweigert · Antwort abgeschnitten · zu wenig Belege · erfundener Beleg · Vertrauen unter dem Band · Selbstprüfung negativ · kaputte Konfiguration. Fällt der Anbieter aus, gibt es einen Fehler — keine Notlösung.</div>""",
    way=3))

S.append(slide("Das Beispiel",
    """<div class="eyebrow">Weg B · Frage → Antwort</div>
          <h1>Dieselbe Frage. <span class="accent">Zwei Formulierungen.</span></h1>
          <p class="lead">Wörtlich so gestellt, Tippfehler inklusive, am 18.09. gegen den laufenden Stack verfolgt. Die Antwort steht in der Ordnungsbussenverordnung: innerorts 6–10 km/h zu schnell kostet 120 Franken.</p>
          <div class="learning">
            <strong>Funktioniert gut</strong>
            Die Suche nach Bedeutung findet beide: Q1 auf Platz 1, Q2 auf Platz 2 von 1017 Abschnitten. Dass «gebliztz» falsch geschrieben ist, stört sie nicht — sie vergleicht Bedeutungen, keine Zeichenketten.
          </div>""",
    """<div class="panel-label"><span>Beispiel</span><span class="status">echter Lauf</span></div>
          <div class="asker">
            <div class="portrait"><img src="../assets/lara-portrait-v1.png" alt="Lara, neue Mitarbeiterin"></div>
            <div class="asks">
              <div>
                <div class="ask-label"><span class="q">Q1</span> · formal</div>
                <div class="bubble">Ich fahre innerorts 6 Km/h zu schnell wie hoch ist die Busse?</div>
              </div>
              <div>
                <div class="ask-label"><span class="q">Q2</span> · umgangssprachlich</div>
                <div class="bubble">Ich wurde innerorts mit 6 <span class="typo">zuschnell</span> <span class="typo">gebliztz</span> was kostet mich das?</div>
              </div>
            </div>
          </div>
          <div class="panel-foot"><strong>Suche nach Bedeutung:</strong> richtiger Abschnitt auf Platz 1 (Q1) und Platz 2 (Q2).</div>""",
    way=3))

S.append(slide("Wortsuche",
    """<div class="eyebrow">Weg B · Frage → Antwort</div>
          <h1>Zwei Zerleger, die sich <span class="accent">nicht einig sind</span></h1>
          <p class="lead">Die Frage zerlegt Python mit einem Regex, das Dokument zerlegt Postgres mit seinem eigenen Parser. Beide schneiden dieselben Wörter anders.</p>
          <div class="learning bad">
            <strong>Funktioniert nicht</strong>
            Von der ganzen Frage trifft im richtigen Abschnitt genau ein Wort: «innerort». Das reicht für Rang 22 — zwei Plätze zu tief für die Auswahl. Bei Q2 ist es Rang 119.
          </div>""",
    """<div class="panel-label"><span>Q1 · was die Wortsuche aus der Frage macht</span></div>
          <div>
            <span class="chip out">6<small>zu kurz, fliegt raus</small></span><span class="chip out">Km/h → km<small>Dokument kennt «km/h» als ein Wort</small></span><span class="chip out">Busse → buss<small>Dokument sagt «ordnungsbuss»</small></span><span class="chip out">schnell<small>trifft «Höchstgeschwindigkeit» nicht</small></span><span class="chip ok">innerort<small>trifft</small></span>
          </div>
          <pre class="law" style="margin-top:18px">303. Überschreiten der Höchst&shy;geschwindigkeit … innerorts

a. um  1– 5 km/h    40
<span class="ans">b. um  6–10 km/h   120</span>
c. um 11–15 km/h   250</pre>""",
    way=3))

S.append(slide("Mischen",
    """<div class="eyebrow">Weg B · Frage → Antwort</div>
          <h1>Das Mischen rechnet mit <span class="accent">Rängen, nicht mit Ähnlichkeiten</span></h1>
          <p class="lead">Wer in beiden Ranglisten mittelmässig steht, gewinnt gegen den, der nur in einer Liste Erster ist. Nur die besten fünf kommen in den Kontext.</p>
          <div class="learning bad">
            <strong>Funktioniert nicht — zweimal</strong>
            Q1: Der beste Treffer rutscht auf Platz 5 von 5. Ein Rang tiefer, und das Modell hätte die Antwort nie gesehen.<br>
            Q2: «wurde» trifft in jedem Rechtstext — 161 von 166 Treffern. Zwei EU-AI-Act-Abschnitte landen im Kontext, mit Ähnlichkeit 0,16 und 0,21. Die Schwelle läge bei 0,35; sie greift hier nicht, weil gemischt wird, bevor sie zählt.
          </div>""",
    """<div class="panel-label"><span>Q1 · Rangliste nach dem Mischen</span><span class="status warn">Schnitt nach 5</span></div>
          <table class="rank">
            <tr><th>Platz</th><th>Bedeutung</th><th>Wörter</th><th>Ähnlichkeit</th></tr>
            <tr><td class="num">1</td><td class="num">5</td><td class="num">4</td><td class="num">0,4778</td></tr>
            <tr><td class="num">2</td><td class="num">8</td><td class="num">9</td><td class="num">0,4640</td></tr>
            <tr><td class="num">3</td><td class="num">18</td><td class="num">2</td><td class="num">0,4373</td></tr>
            <tr><td class="num">4</td><td class="num">19</td><td class="num">10</td><td class="num">0,4361</td></tr>
            <tr class="gt cut"><td class="num">5</td><td class="num">1</td><td class="num">–</td><td class="num">0,5236</td></tr>
            <tr class="out"><td class="num">6</td><td class="num">–</td><td class="num">1</td><td class="num">0,4281</td></tr>
          </table>
          <div class="panel-foot" style="margin-top:14px">Grün: der Abschnitt mit der Antwort. Er hat die höchste Ähnlichkeit der ganzen Liste — und den letzten Platz.</div>""",
    way=3))

S.append(slide("Die Stufen",
    """<div class="eyebrow">Weg B · Frage → Antwort</div>
          <h1>Dieselbe Antwort, <span class="accent">nicht dasselbe Vertrauen</span></h1>
          <p class="lead">Stufe 1 bewertet die Fundlage aus den fünf Abschnitten. Bei Q2 drücken die zwei fremden Abschnitte den Wert auf 0,44 — vier Hundertstel über der Unterdrückung.</p>
          <div class="learning">
            <strong>Funktioniert gut</strong>
            Fail-closed heisst hier nicht «unterdrücken», sondern «genauer hinschauen, wenn die Grundlage dünner ist». Q2 landet im mittleren Band und bekommt eine zweite Prüfung: Ein weiterer Modellaufruf liest die Antwort gegen die Abschnitte zurück. Urteil: gedeckt.
          </div>""",
    """<div class="panel-label"><span>Was die Stufen gemessen haben</span></div>
          <table class="vs">
            <tr><th>Stufe</th><th>Q1 · formal</th><th>Q2 · Alltag</th></tr>
            <tr><td class="l">Kontext</td><td>5× OBV</td><td>3× OBV + 2× fremd</td></tr>
            <tr><td class="l">Stufe 1 · Fundlage <small>(Schwelle 0,40)</small></td><td class="v">0,6021</td><td class="v">0,4403</td></tr>
            <tr><td class="l">Stufe 2 · Belege gültig</td><td class="v">100 %</td><td class="v">100 %</td></tr>
            <tr><td class="l">Band</td><td class="ok">hoch</td><td class="warn">mittel</td></tr>
            <tr><td class="l">Stufe 3 · zweite Prüfung</td><td>nicht nötig</td><td class="warn">läuft → gedeckt</td></tr>
            <tr class="big"><td class="l">Antwort</td><td class="ok">120 Franken</td><td class="ok">120 Franken</td></tr>
          </table>""",
    way=3))

S.append(slide("Bilanz Wortsuche",
    """<div class="eyebrow">Weg B · Frage → Antwort</div>
          <h1>Ein Beispiel ist <span class="accent">eine Anekdote</span></h1>
          <p class="lead">Zweimal hat die Wortsuche hier geschadet. Das heisst noch nichts — also nachgemessen: für 56 Gold-Fragen der Kontext mit beiden Suchen gegen den Kontext nur mit der Bedeutungssuche.</p>
          <div class="learning aha">
            <strong>Der überraschende Teil</strong>
            Sie wurde für exakte Fachbegriffe und deutsche Komposita eingeführt, und dafür ist sie richtig. Nur ist das in unserem Korpus selten — in 48 von 56 Fällen ändert sie gar nichts. Kein Grund, sie abzuschalten; ein Grund, zu messen statt anzunehmen.
          </div>""",
    """<div class="panel-label"><span>Wortsuche über 56 Gold-Fragen</span><span class="status">eigene Messung</span></div>
          <div class="evalcats">
            <div><b>3</b><span>hilft</span><small>Abschnitt kommt nur dank Wortsuche in den Kontext</small></div>
            <div><b>5</b><span>schadet</span><small>Abschnitt fällt wegen der Wortsuche heraus</small></div>
            <div><b>48</b><span>kein Unterschied</span><small>gleicher Kontext mit und ohne</small></div>
          </div>
          <div class="panel-foot" style="margin-top:18px"><strong>Nicht gemessen:</strong> ob eine der naheliegenden Korrekturen hilft — die Frage mit demselben Parser zerlegen wie das Dokument, «wurde» in die Stoppwortliste, ein Re-Ranker. Jede davon gehört vor der Umsetzung gegen das Gold-Dataset gemessen.</div>""",
    way=3))

# ── Weg C ────────────────────────────────────────────────────────────────
S.append(slide("Weg C Generierung",
    """<div class="eyebrow">Weg C · Fragen hinaus</div>
          <h1>Das System stellt auch <span class="accent">selbst Fragen</span></h1>
          <p class="lead">Stefan löst die Generierung aus. Zehn zufällige Abschnitte gehen in einem einzigen Aufruf ans Modell, heraus kommen fünf Multiple-Choice-Fragen mit je vier Optionen und einer Erklärung.</p>
          <div class="learning">
            <strong>Funktioniert gut</strong>
            Zehn Abschnitte für fünf Fragen — die Reserve ist Absicht. Mit genau fünf müsste das Modell auch aus einem Inhaltsverzeichnis oder einer Überschrift eine Frage pressen. Unbenutzte Abschnitte sind der Normalfall, kein Fehler.
          </div>""",
    """<div class="panel-label"><span>Eine echte generierte Frage</span><span class="status">EU AI Act</span></div>
          <div class="qcard">
            <div class="qq">Was sollte in der Folgen&shy;abschätzung eines Hochrisiko-KI-Systems berücksichtigt werden?</div>
            <ol type="A">
              <li>Die Grösse des Unternehmens</li>
              <li class="right">Die spezifischen Schadensrisiken für Grundrechte</li>
              <li>Die Anzahl der Mitarbeiter</li>
              <li>Die Marktanteile des Unternehmens</li>
            </ol>
            <div class="prov">Gespeichert mit Abschnitt, Dokument und dem Textauszug, auf dem die Frage beruht.</div>
          </div>""",
    way=4))

S.append(slide("Provenienz",
    """<div class="eyebrow">Weg C · Fragen hinaus</div>
          <h1>Eine erfundene Quelle ist <span class="accent">ein Fehler, kein Detail</span></h1>
          <p class="lead">Jede Frage muss den nummerierten Abschnitt nennen, aus dem sie stammt. Nennt sie eine Nummer, die es im Aufruf nicht gab, wird die Frage verworfen — nicht mit geratener Quelle gespeichert.</p>
          <div class="learning">
            <strong>Dieselbe Regel wie beim Antworten</strong>
            Im Antwortweg heisst sie «ungültiger Beleg» und unterdrückt die Antwort. Hier verwirft sie die Frage. Eine erfundene Referenz ist ein Modellfehler — keine Schwelle macht sie akzeptabel.
          </div>""",
    """<div class="panel-label"><span>Was das Modell zurückgeben muss</span></div>
          <pre class="code-block">{
  <span class="k">"question"</span>: "Was sollte in der Folgenabschätzung …",
  <span class="k">"options"</span>: ["…", "…", "…", "…"],
  <span class="k">"correct"</span>: "B",
  <span class="k">"explanation"</span>: "…",
  <span class="ok">"source"</span>: 7          <span class="k">← einer der 10 Abschnitte</span>
}</pre>
          <div class="panel-foot" style="margin-top:16px"><strong>Verworfen wird auch:</strong> eine Frage ohne genau vier Optionen, mit mehr als einer richtigen Antwort oder ohne Erklärung. Fünf Fragen sind das Soll — ein Lauf, der drei brauchbare liefert, ist ein schlechter Lauf, kein kürzeres Quiz.</div>""",
    way=4))

S.append(slide("Menschliches Gate",
    """<div class="eyebrow">Weg C · Fragen hinaus</div>
          <h1>Hier entscheidet <span class="accent">kein Score</span></h1>
          <p class="lead">Generierte Fragen landen als «offen» und bleiben dort. Stefan gibt frei, korrigiert den Text oder lehnt ab. Erst danach kann eine Lernende die Frage überhaupt ziehen.</p>
          <div class="learning">
            <strong>Funktioniert gut</strong>
            Auch die Sichtbarkeit ist fail-closed: Ein Filter kann die erlaubte Menge nur verkleinern, nie vergrössern. Wer als Lernende nach «offen» filtert, bekommt eine leere Liste — keine Fehlermeldung, aber auch keine unfreigegebene Frage.
          </div>""",
    """<div class="panel-label"><span>Der Weg einer generierten Frage</span></div>
          <div class="pipe">
            <div><b>1</b><div><h3>offen</h3><small>so wird jede Frage gespeichert</small></div><span class="tag">Standard</span></div>
            <div><b>2</b><div><h3>Stefan liest</h3><small>freigeben · Text korrigieren · ablehnen</small></div><span class="tag human">Mensch</span></div>
            <div><b>3</b><div><h3>freigegeben</h3><small>nur diese Fragen sind für Lernende sichtbar</small></div><span class="tag">Lernende</span></div>
            <div><b>4</b><div><h3>Quiz-Durchlauf</h3><small>fünf freigegebene Fragen, zufällig gezogen</small></div><span class="tag">Lernende</span></div>
          </div>
          <div class="panel-foot" style="margin-top:16px"><strong>Unterschied zum Antwortweg:</strong> Dort prüft die Maschine in vier Stufen, weil Lara sofort eine Antwort braucht. Hier wartet niemand — also prüft ein Mensch.</div>""",
    way=4))

# ── Belege ───────────────────────────────────────────────────────────────
S.append(slide("Eval",
    """<div class="eyebrow">Belege</div>
          <h1>Woher wir wissen, <span class="accent">dass es hält</span></h1>
          <p class="lead">Man stellt der Pipeline 80 Fragen, deren richtige Antwort man schon kennt — inklusive der Seite, auf der sie steht — und vergleicht. Diese Sammlung heisst Gold-Dataset.</p>
          <div class="learning">
            <strong>Gemessen, nicht geschätzt</strong>
            Jede Änderung an der Pipeline muss sich an denselben 80 Fragen beweisen. Drei Grenzen müssen halten, sonst geht nichts in Produktion.
          </div>""",
    """<div class="panel-label"><span>Gold-Dataset</span><span class="status">80 Fragen</span></div>
          <pre class="code-block"><span class="k">id:</span> SKOS-PRINZ-02
<span class="k">question:</span> Was bedeutet das Bedarfsdeckungsprinzip?
<span class="k">category:</span> in_corpus
<span class="k">expected_refusal:</span> false
<span class="k">expected_source:</span> Seiten 6–8 · A.3 Prinzipien</pre>
          <div class="evalcats">
            <div><b>45</b><span>steht drin</span><small>muss antworten und belegen</small></div>
            <div><b>22</b><span>steht nicht drin</span><small>muss «Weiss ich nicht» sagen</small></div>
            <div><b>13</b><span>Fangfragen</span><small>muss die falsche Annahme korrigieren</small></div>
          </div>
          <div class="gates">
            <div><span>Nichts erfinden</span><b>0 %<small>erfundene Belege</small></b></div>
            <div><span>Ablehnen, was nicht drinsteht</span><b>≥ 90 %<small>«Weiss ich nicht»</small></b></div>
            <div><span>Antworten, was drinsteht</span><b>≤ 15 %<small>fälschlich abgelehnt</small></b></div>
          </div>""",
    way=5))

S.append(slide("Gold muss Gold sein",
    """<div class="eyebrow">Belege</div>
          <h1>Der Massstab kann <span class="accent">selbst falsch sein</span></h1>
          <p class="lead">Ein Eintrag verlangt, dass die Pipeline ablehnt: Meldefristen stünden nicht im Leitfaden. Sie stehen aber drin.</p>
          <div class="learning bad">
            <strong>Funktioniert nicht</strong>
            Die Pipeline antwortete richtig — und wurde dafür als Fehler gezählt. Nach der Abnahme prüft niemand mehr gegen den Korpus, also bestraft ein falscher Eintrag korrektes Verhalten dauerhaft und unbemerkt. Das Gold-Dataset braucht dieselbe Prüfung wie der Code: gegen die Quelle, nicht gegen die Erinnerung.
          </div>""",
    """<div class="panel-label"><span>Eintrag SAMW-OOC-03</span><span class="status warn">Defekt · Issue #142</span></div>
          <pre class="code-block"><span class="k">question:</span> Innert welcher Frist müssen schwer&shy;wiegende
  unerwünschte Ereignisse der Ethik&shy;kommission
  gemeldet werden?
<span class="k">category:</span> <span class="hl">out_of_corpus</span>
<span class="k">expected_refusal:</span> <span class="hl">true</span>
<span class="k">note:</span> «Konkrete Meldefristen sind nicht im
  Leitfaden enthalten → Weiss ich nicht.»</pre>
          <div class="panel-foot" style="margin-top:16px"><strong>Im Korpus steht:</strong> der SAMW-Leitfaden nennt die Frist. Einer von drei Einträgen, die wir bei der Nachprüfung gefunden haben.</div>""",
    way=5))

S.append(slide("Schluss",
    """<div class="eyebrow">Zusammengefasst</div>
          <h1>Drei Wege, <span class="accent">drei Prüfungen</span></h1>
          <p class="lead">Wer über die Qualität entscheidet, hängt davon ab, wer wartet: Lara wartet auf die Antwort, also prüft die Maschine. Auf eine Quizfrage wartet niemand, also prüft ein Mensch.</p>
          <div class="learning aha">
            <strong>Was uns überrascht hat</strong>
            Die heiklen Stellen lagen nie dort, wo wir sie vermutet haben, sondern zwischen zwei Bauteilen: zwischen Parser und Suche, zwischen Rang und Ähnlichkeit, zwischen Gold-Dataset und Korpus.
          </div>""",
    """<div class="panel-label"><span>Wer prüft was</span></div>
          <div class="close">
            <div><div><h3>Die Antwort</h3><p>Vier Stufen, jede darf unterdrücken — keine darf aufwerten.</p></div><em class="m">Maschine</em></div>
            <div><div><h3>Die Frage</h3><p>Generiert wird automatisch, freigegeben wird von Hand.</p></div><em class="h">Mensch</em></div>
            <div><div><h3>Beides zusammen</h3><p>80 Gold-Fragen vor jedem Release, drei harte Grenzen.</p></div><em class="e">Messung</em></div>
          </div>""",
    way=5))

SLIDES = (
    '  <main class="deck" aria-label="LearnFlow Technischer Aufbau">\n'
    + "".join(S).replace('<section class="slide"', '<section class="slide active"', 1)
    + "\n"
)
OUT.write_text(head + SLIDES + "  </main>" + tail, encoding="utf-8")
print("Folien:", SLIDES.count('<section class="slide'))


# ── Q1/Q2 behalten ihr Abzeichen aus der letzten Fassung ─────────────────
Q_CSS = """
    /* ── Q1/Q2-Abzeichen ─────────────────────────────────────────────── */
    :root { --q1: #2f5bd3; --q1-pale: #e8eefc; --q2: #8b3fd9; --q2-pale: #f3eafc; }
    .qb {
      display: inline-flex; align-items: center; gap: .32em; vertical-align: .06em;
      padding: .16em .55em .16em .38em; border-radius: 99px; color: #fff;
      font-size: clamp(16px, .7em, 30px); font-weight: 850; letter-spacing: .01em; line-height: 1.15;
      text-transform: none; white-space: nowrap; font-style: normal;
    }
    .qb.q1 { background: var(--q1); }
    .qb.q2 { background: var(--q2); }
    .qb .qi {
      display: inline-grid; place-items: center; width: 1.25em; height: 1.25em; border-radius: 50%;
      background: rgba(255, 255, 255, .22); font-size: .95em; font-weight: 900;
    }
    .qb .qi svg { width: .82em; height: .82em; display: block; }
    .bubble.b1 { box-shadow: inset 7px 0 0 var(--q1), 0 14px 28px rgba(16, 30, 54, .16); }
    .bubble.b2 { box-shadow: inset 7px 0 0 var(--q2), 0 14px 28px rgba(16, 30, 54, .16); }
    .ask-label .q { color: inherit; }
    .ask-label .qb { font-size: 22px; margin-right: 4px; }
    .panel-label .qb, .vs th .qb { font-size: 17px; margin-right: 3px; }
    .learning .qb { font-size: 17px; }
"""

BUBBLE_SVG = ('<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" '
              'd="M2 2.5h12a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7l-3.5 3v-3H2a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1z"/></svg>')
BADGE = {
    "1": '<span class="qb q1" title="Frage 1 · formal"><span class="qi">§</span>Q1</span>',
    "2": f'<span class="qb q2" title="Frage 2 · Alltag"><span class="qi">{BUBBLE_SVG}</span>Q2</span>',
}


def _badge_text(html: str) -> str:
    """Q1/Q2 nur in Textknoten ersetzen — Attribute bleiben unangetastet."""
    def text_node(m: re.Match) -> str:
        return re.sub(r"\bQ([12])\b", lambda q: BADGE[q.group(1)], m.group(0))
    return re.sub(r"(?<=>)[^<>]+(?=<)", text_node, html)


html = OUT.read_text(encoding="utf-8")
assert html.count(marker) == 1
html = html.replace(marker, Q_CSS + marker)

head_part, main_part = html.split('  <main class="deck"', 1)
main_part = _badge_text(main_part)

beispiel = main_part.index('aria-label="Das Beispiel"')
for n in ("1", "2"):
    idx = main_part.index('class="bubble"', beispiel)
    main_part = main_part[:idx] + f'class="bubble b{n}"' + main_part[idx + len('class="bubble"'):]

OUT.write_text(head_part + '  <main class="deck"' + main_part, encoding="utf-8")
print("Abzeichen:", main_part.count('class="qb q1"'), "×Q1,", main_part.count('class="qb q2"'), "×Q2")
print("geschrieben:", OUT)
