"""Block 2 — gekürzte Fassung (v4), zusammengestellt aus V2 und V3.

Quellen (beide archiviert, werden nur gelesen):
    V2 = ../Archive/Block2_Technischer-Aufbau_v2.html            (19.09., 19 Folien; die letzte ist abgeschnitten)
    V3 = ../Archive/2026-09-20/Block2_Technischer-Aufbau.html    (20.09., 17 Folien)
Ergebnis:
    ../Block2_Technischer-Aufbau.html

Kopf (CSS) und Fuss (Navigation) stammen aus V3. Jede Folie wird unverändert aus
ihrer Quelle übernommen; Korrekturen stehen als (alt, neu)-Paare bei der Folie und
müssen genau einmal treffen, sonst bricht der Build ab.

    python build/build_block2_v4.py
"""

import base64
import os
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SOURCES = {
    "V2": BASE / "Archive" / "Block2_Technischer-Aufbau_v2.html",
    "V3": BASE / "Archive" / "2026-09-20" / "Block2_Technischer-Aufbau.html",
}
OUT = BASE / "Block2_Technischer-Aufbau.html"

# Die drei Bereiche der Leiste oben auf jeder Folie (ersetzt Landkarte / Weg A–C / Belege).
SECTIONS = ["Architektur", "RAG-Pipeline", "Evaluation"]

# CSS, das V3 nicht mitbringt: .big-lead/.take aus V2 und das Flussdiagramm.
EXTRA_CSS = """
    /* v4: aus V2 übernommen */
    .big-lead { max-width: 600px; margin: 26px 0 0; color: #566173; font-size: 22px; line-height: 1.45; letter-spacing: -.014em; }
    .take {
      max-width: 620px; margin-top: 26px; padding: 16px 0 16px 22px; border-left: 4px solid var(--amber);
      color: var(--ink); font-size: 20px; font-weight: 700; line-height: 1.4;
    }
    .take.good { border-left-color: var(--teal); }
    .take.bad { border-left-color: var(--coral); }
    /* v4: Balken der Ähnlichkeit (V2 F11), aus V2 übernommen */
    .doc { display: inline-block; padding: 3px 10px; border-radius: 8px; font-size: 15px; font-weight: 800; white-space: nowrap; }
    .doc.obv { background: var(--teal-pale); color: var(--teal-dark); }
    .doc.fremd { background: var(--coral-pale); color: var(--coral-dark); }
    .listhead { margin: 0 0 10px; color: var(--muted); font-size: 14px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
    .listhead .qb { font-size: 20px; margin-right: 4px; }
    .bars { display: grid; gap: 10px; }
    .bar { display: grid; grid-template-columns: 190px 1fr 60px; gap: 14px; align-items: center; }
    .bar .track { position: relative; height: 22px; border-radius: 6px; background: var(--paper); }
    .bar .fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 6px; background: rgba(15, 168, 160, .55); }
    .bar .fill.low { background: rgba(207, 102, 92, .55); }
    .bar .thr { position: absolute; top: -5px; bottom: -5px; width: 3px; background: var(--ink); border-radius: 2px; left: 58.33%; }
    .bar .v { font-size: 17px; font-weight: 800; color: var(--ink); text-align: right; font-variant-numeric: tabular-nums; }
    .bars-note { margin-top: 12px; color: var(--muted); font-size: 14px; font-weight: 650; }
    /* v4: Eval als Ablauf (V2 F18): Schrittkästen aus V2 übernommen */
    .phases { display: grid; gap: 12px; }
    .phase { display: grid; grid-template-columns: 60px 1fr auto; gap: 18px; align-items: center; padding: 16px 20px; border: 1px solid var(--line); border-radius: 18px; background: var(--white); }
    .phase b { display: grid; place-items: center; width: 50px; height: 50px; border-radius: 14px; background: var(--teal-pale); color: var(--teal-dark); font-size: 21px; font-weight: 850; }
    .phase h3 { margin: 0 0 3px; color: var(--ink); font-size: 21px; font-weight: 800; letter-spacing: -.02em; }
    .phase p { margin: 0; color: var(--muted); font-size: 16.5px; font-weight: 620; line-height: 1.35; }
    .phase .tag { padding: 6px 12px; border-radius: 99px; font-size: 13.5px; font-weight: 800; white-space: nowrap; background: var(--paper); color: var(--muted); }
    .phase .tag.gate { background: var(--coral-pale); color: var(--coral-dark); }
    /* v4: eine Karte pro Fragetyp — Erklärung oben, geforderter Wert unten (Zuordnung nach ADR-009) */
    .qtypes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 18px; }
    .qtypes > div { display: flex; flex-direction: column; padding: 14px 16px; border-radius: 16px; background: var(--paper); }
    .qtypes b { color: var(--teal-dark); font-size: 30px; font-weight: 850; letter-spacing: -.04em; line-height: 1; }
    .qtypes span { margin-top: 5px; color: var(--ink); font-size: 16px; font-weight: 780; }
    .qtypes small { margin-top: 2px; color: var(--muted); font-size: 14px; font-weight: 620; line-height: 1.3; }
    .qtypes .req { margin-top: auto; padding-top: 10px; }
    .qtypes .req div { margin-top: 8px; padding: 8px 12px; border-radius: 12px; background: var(--white); border: 2px solid var(--ink); }
    .qtypes .req strong { display: block; color: var(--ink); font-size: 24px; font-weight: 850; letter-spacing: -.03em; }
    .qtypes .req em { display: block; color: var(--muted); font-size: 13.5px; font-weight: 650; font-style: normal; }
    /* v4: Flussdiagramm der fünf Phasen (baut auf .arch auf) */
    .flowd .ah { fill: var(--muted); }
    .flowd .ph { fill: var(--ink); font: 800 15px Inter, sans-serif; }
    .flowd .num { fill: var(--teal-pale); }
    .flowd .num.gate { fill: var(--coral-pale); }
    .flowd .num.llm { fill: var(--ink); }
    .flowd .nt { fill: var(--teal-dark); font: 850 15px Inter, sans-serif; text-anchor: middle; }
    .flowd .nt.gate { fill: var(--coral-dark); }
    .flowd .nt.llm { fill: var(--white); }
    .flowd .box.gate { stroke: var(--coral); stroke-width: 2; }
    .flowd .box.llm { fill: var(--ink); stroke: var(--ink); }
    .flowd .t.inv { fill: var(--white); }
    .flowd .s.inv { fill: rgba(255, 254, 251, .72); }
    .flowd .box.stop { fill: var(--coral-pale); stroke: var(--coral); stroke-dasharray: 6 5; }
    .flowd .t.stop { fill: var(--coral-dark); }
    .flowd .lbl.neg { fill: var(--coral-dark); font-weight: 750; }
    .flowd .lbl.yes { fill: var(--teal-dark); font-weight: 750; }
    /* v4: Self-Check (V2 F16) — durchlaufener Pfad vs. nicht durchlaufene Pfade */
    .flowd .ahp { fill: var(--ink); }
    .flowd .edge.path { stroke: var(--ink); stroke-width: 2.6; }
    .flowd .edge.alt { stroke-dasharray: 6 5; opacity: .55; }
    .flowd .lbl.alt { opacity: .8; }
    .flowd .capt { fill: var(--teal-dark); font: 800 13px Inter, sans-serif; letter-spacing: .1em; text-anchor: middle; }
    .flowd .anst { fill: var(--ink); font: 750 17px Inter, sans-serif; text-anchor: middle; }
    .flowd .cref { fill: var(--teal-dark); font-family: var(--mono); font-weight: 800; }
"""

# V2 F16: der Self-Check für Q2 als Flussdiagramm (Stil wie F3).
# Werte aus Pipeline-Trace/Q2.json: Vertrauen 0,7202, Band mittel, Self-Check GEDECKT.
# Der Pfad von Q2 ist durchgezogen (edge path), nicht durchlaufene Pfade gestrichelt (edge alt).
SELFCHECK_SVG = """\
          <svg class="arch flowd" viewBox="0 0 700 428" role="img" aria-label="Flussdiagramm Self-Check für Q2: Vertrauen 0,72 liegt im mittleren Band, also prüft das Modell seine Antwort gegen die fünf Abschnitte. Urteil gedeckt, die Antwort wird ausgeliefert. Nicht durchlaufen und gestrichelt: hohes Vertrauen direkt zur Antwort, tiefes Vertrauen oder nicht gedeckt zu «Weiss ich nicht».">
            <defs>
              <marker id="fb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path class="ah" d="M0 0 L10 5 L0 10 z"/>
              </marker>
              <marker id="fbp" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path class="ahp" d="M0 0 L10 5 L0 10 z"/>
              </marker>
            </defs>
            <!-- Eingang -->
            <rect class="box" x="160" y="4" width="240" height="38" rx="19"/>
            <text class="t" x="280" y="30">Q2 · Vertrauen 0,72</text>
            <path class="edge path" d="M280 42 V70" marker-end="url(#fbp)"/>
            <!-- Band-Prüfung: drei Ausgänge -->
            <rect class="box gate" x="90" y="72" width="380" height="56" rx="14"/>
            <text class="t" x="280" y="96">Welches Band?</text>
            <text class="s" x="280" y="117">tief &lt; 0,45 ≤ mittel &lt; 0,75 ≤ hoch</text>
            <!-- nicht durchlaufen: hoch → direkt zur Antwort -->
            <path class="edge alt" d="M90 100 H40 V363 H88" marker-end="url(#fb)"/>
            <text class="lbl alt" x="48" y="92">hoch</text>
            <!-- nicht durchlaufen: tief → «Weiss ich nicht» -->
            <path class="edge alt" d="M470 100 H650 V266" marker-end="url(#fb)"/>
            <text class="lbl alt" x="478" y="92">tief</text>
            <!-- Pfad von Q2: mittel → Self-Check (2. Modellaufruf) -->
            <path class="edge path" d="M280 128 V162" marker-end="url(#fbp)"/>
            <text class="lbl yes" x="290" y="150">mittel</text>
            <rect class="box llm" x="90" y="164" width="380" height="92" rx="14"/>
            <text class="t inv" x="280" y="192">Self-Check · 2. Modellaufruf</text>
            <text class="s inv" x="280" y="218">Steht jede Aussage in den fünf Abschnitten?</text>
            <text class="s inv" x="280" y="239">Ohne Vorwissen.</text>
            <!-- nicht durchlaufen: nicht gedeckt → «Weiss ich nicht» -->
            <path class="edge alt" d="M470 210 H560 V266" marker-end="url(#fb)"/>
            <text class="lbl alt" x="478" y="202">nicht gedeckt</text>
            <rect class="box stop" x="520" y="268" width="180" height="64" rx="14"/>
            <text class="t stop" x="610" y="306">«Weiss ich nicht»</text>
            <!-- Pfad von Q2: gedeckt → Antwort ausgeliefert -->
            <path class="edge path" d="M280 256 V300" marker-end="url(#fbp)"/>
            <text class="lbl yes" x="290" y="283">gedeckt</text>
            <rect class="box db" x="90" y="302" width="380" height="122" rx="16"/>
            <text class="capt" x="280" y="328">ANTWORT AUSGELIEFERT</text>
            <text class="anst" x="280" y="356">Das Überschreiten der</text>
            <text class="anst" x="280" y="380">Höchstgeschwindigkeit innerorts</text>
            <text class="anst" x="280" y="404">um 6–10 km/h kostet 120 Franken <tspan class="cref">[3]</tspan>.</text>
          </svg>
"""

# V2 F4: die fünf Phasen als Flussdiagramm statt als Liste. Texte aus der V2-Folie.
FLOW_SVG = """\
          <svg class="arch flowd" viewBox="0 0 700 544" role="img" aria-label="Flussdiagramm: Frage, zwei Suchen, Mischen, Vorprüfung, Antworten, Nachprüfung. Bei hohem Vertrauen Antwort mit Belegen, bei mittlerem ein Self-Check als zweiter Modellaufruf, bei zu tiefem Vertrauen oder zu wenig Passendem «Weiss ich nicht».">
            <defs>
              <marker id="fa" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path class="ah" d="M0 0 L10 5 L0 10 z"/>
              </marker>
            </defs>
            <!-- Phasenleiste links -->
            <circle class="num" cx="18" cy="95" r="15"/><text class="nt" x="18" y="100">1</text><text class="ph" x="42" y="100">Suchen</text>
            <circle class="num" cx="18" cy="169" r="15"/><text class="nt" x="18" y="174">2</text><text class="ph" x="42" y="174">Mischen</text>
            <circle class="num gate" cx="18" cy="243" r="15"/><text class="nt gate" x="18" y="248">3</text><text class="ph" x="42" y="248">Vorprüfung</text>
            <circle class="num llm" cx="18" cy="317" r="15"/><text class="nt llm" x="18" y="322">4</text><text class="ph" x="42" y="322">Antworten</text>
            <circle class="num gate" cx="18" cy="391" r="15"/><text class="nt gate" x="18" y="396">5</text><text class="ph" x="42" y="396">Nachprüfung</text>
            <!-- Eingang -->
            <rect class="box" x="245" y="2" width="130" height="36" rx="18"/>
            <text class="t" x="310" y="27">Frage</text>
            <!-- 1 Suchen: zwei parallele Suchen -->
            <path class="edge" d="M310 38 V52 H226 V68" marker-end="url(#fa)"/>
            <path class="edge" d="M310 52 H394 V68" marker-end="url(#fa)"/>
            <rect class="box db" x="150" y="70" width="152" height="50" rx="14"/>
            <text class="t" x="226" y="92">Bedeutung</text>
            <text class="s" x="226" y="111">Vektoren</text>
            <rect class="box db" x="318" y="70" width="152" height="50" rx="14"/>
            <text class="t" x="394" y="92">Wörter</text>
            <text class="s" x="394" y="111">Volltext</text>
            <!-- 2 Mischen -->
            <path class="edge" d="M226 120 V132 H310 V142" marker-end="url(#fa)"/>
            <path class="edge" d="M394 120 V132 H310"/>
            <rect class="box" x="150" y="144" width="320" height="50" rx="14"/>
            <text class="t" x="310" y="166">Zwei Listen werden eine</text>
            <text class="s" x="310" y="185">nur 5 Abschnitte gehen weiter</text>
            <!-- 3 Vorprüfung -->
            <path class="edge" d="M310 194 V216" marker-end="url(#fa)"/>
            <rect class="box gate" x="150" y="218" width="320" height="50" rx="14"/>
            <text class="t" x="310" y="240">Genug Passendes gefunden?</text>
            <text class="s" x="310" y="259">sonst stoppt die Pipeline hier</text>
            <!-- 4 Antworten: 1. Modellaufruf -->
            <path class="edge" d="M310 268 V290" marker-end="url(#fa)"/>
            <text class="lbl yes" x="320" y="284">ja</text>
            <rect class="box llm" x="150" y="292" width="320" height="50" rx="14"/>
            <text class="t inv" x="310" y="314">Sprachmodell antwortet</text>
            <text class="s inv" x="310" y="333">nur aus den 5 Abschnitten</text>
            <!-- 5 Nachprüfung: drei Ausgänge -->
            <path class="edge" d="M310 342 V364" marker-end="url(#fa)"/>
            <rect class="box gate" x="150" y="366" width="320" height="50" rx="14"/>
            <text class="t" x="310" y="388">Wie viel Vertrauen?</text>
            <text class="s" x="310" y="407">Belege und Fundlage zusammen</text>
            <!-- hoch → ausliefern -->
            <path class="edge" d="M310 416 V498" marker-end="url(#fa)"/>
            <text class="lbl yes" x="320" y="462">hoch</text>
            <!-- mittel → Self-Check (2. Modellaufruf) -->
            <path class="edge" d="M440 416 V465 H498" marker-end="url(#fa)"/>
            <text class="lbl" x="448" y="446">mittel</text>
            <rect class="box llm" x="500" y="440" width="200" height="50" rx="14"/>
            <text class="t inv" x="600" y="462">Self-Check</text>
            <text class="s inv" x="600" y="481">2. Modellaufruf</text>
            <path class="edge" d="M600 490 V520 H417" marker-end="url(#fa)"/>
            <text class="lbl yes" x="470" y="512">gedeckt</text>
            <!-- Ausgang -->
            <rect class="box db" x="205" y="500" width="210" height="40" rx="20"/>
            <text class="t" x="310" y="526">Antwort mit Belegen</text>
            <!-- «Weiss ich nicht»: aus Vorprüfung, Nachprüfung und Self-Check -->
            <rect class="box stop" x="500" y="270" width="200" height="70" rx="14"/>
            <text class="t stop" x="600" y="300">«Weiss ich nicht»</text>
            <text class="s" x="600" y="322">statt zu raten</text>
            <path class="edge" d="M470 243 H600 V268" marker-end="url(#fa)"/>
            <text class="lbl neg" x="478" y="235">nein</text>
            <path class="edge" d="M470 391 H560 V342" marker-end="url(#fa)"/>
            <text class="lbl neg" x="478" y="383">tief</text>
            <path class="edge" d="M650 440 V342" marker-end="url(#fa)"/>
            <text class="lbl neg" x="642" y="420" text-anchor="end">nicht gedeckt</text>
          </svg>
"""
# V2 F18, Panel neu geordnet. Schritttexte aus V2; Zuordnung Fragetyp → Grenze nach
# ADR-009 (Abschnitt Metriken): 0 % gilt für in_corpus und für die 11 von 13
# adversarial-Fragen mit expected_refusal: false (gold-eval-dataset.yaml, 22.09. gezählt).
# Glossar: «Prüfung» statt des früheren «Gates».
EVAL_PANEL = """\
          <div class="phases">
            <div class="phase"><b>1</b><div><h3>Fragen mit bekannter Antwort</h3><p>Bei jeder Frage ist festgehalten, ob die Antwort im Korpus steht – und auf welcher Seite.</p></div><span class="tag">80 Fragen</span></div>
            <div class="phase"><b>2</b><div><h3>Pipeline antworten lassen</h3><p>Alle 80 Fragen laufen durch die echte Pipeline.</p></div><span class="tag">automatisch</span></div>
            <div class="phase"><b>3</b><div><h3>Vergleichen</h3><p>Drei Grenzen müssen halten, sonst geht nichts in Produktion.</p></div><span class="tag gate">Prüfung</span></div>
          </div>
          <div class="qtypes">
            <div><b>45</b><span>Antwort steht drin</span><small>muss antworten und belegen</small>
              <div class="req"><div><strong>≤ 15 %</strong><em>fälschlich abgelehnt</em></div><div><strong>0 %</strong><em>erfundene Belege</em></div></div></div>
            <div><b>22</b><span>steht nicht drin</span><small>muss «Weiss ich nicht» sagen</small>
              <div class="req"><div><strong>≥ 90 %</strong><em>«Weiss ich nicht»</em></div></div></div>
            <div><b>13</b><span>Fangfragen</span><small>falsche Annahme korrigieren</small>
              <div class="req"><div><strong>0 %</strong><em>erfundene Belege</em></div></div></div>
          </div>
"""
PHASES_RE = re.compile(r'[ \t]*<div class="phases">.*?\n          </div>\n', re.S)

# (Quelle, Foliennummer 1-basiert, Bereich 1–3, Korrekturen)
# Korrektur = (alter Text, neuer Text) oder (Regex, neuer Text); beides muss genau 1× treffen.
# Leiste und Eyebrow erzeugt der Build aus dem Bereich; die Eyebrow zeigt den
# Bereichsnamen.
SLIDES = [
    ("V3", 1, 1, [
        # Genau wie im Diagramm: Web App, zwei Backend-Services (API, Worker), eine Datenbank.
        ("<h1>Vier Container. <span class=\"accent\">Eine Datenbank.</span></h1>",
         "<h1>Ein Frontend. Zwei Services. <span class=\"accent\">Eine Datenbank.</span></h1>"),
        # Diagramm senkrecht zentrieren statt oben mit leerem Streifen darunter.
        ('<div class="panel">', '<div class="panel center">'),
        # Modellzeile war breiter als der Kasten → zwei Zeilen, Kasten 96 → 110 hoch.
        ('<rect class="box ext" x="460" y="220" width="250" height="96" rx="14"/>',
         '<rect class="box ext" x="460" y="220" width="250" height="110" rx="14"/>'),
        ('<text class="s" x="585" y="294">gpt-4o-mini · text-embedding-3-small</text>',
         '<text class="s" x="585" y="294">gpt-4o-mini</text>\n'
         '            <text class="s" x="585" y="314">text-embedding-3-small</text>'),
        ('<line class="edge" x1="585" y1="378" x2="585" y2="318" marker-end="url(#ah)"/>',
         '<line class="edge" x1="585" y1="378" x2="585" y2="332" marker-end="url(#ah)"/>'),
        # Der POC läuft über OpenAI Direct (ADR-004: MVP-Default); Azure OpenAI EU kommt erst,
        # bevor echte interne Dokumente verarbeitet werden.
        ('<text class="note" x="585" y="206">extern · Pilot: Azure OpenAI EU</text>',
         '<text class="note" x="585" y="206">extern · POC: OpenAI Direct</text>'),
    ]),
    ("V2", 2, 2, [
        # Korpus-Aufzählung unten weg; der Fundort der Antwort bleibt.
        ("<strong>Korpus:</strong> SKOS-Richtlinien · EU AI Act · SAMW-Leitfaden · "
         "Ordnungsbussenverordnung (OBV) – 1017 Chunks.<br>\n            ", ""),
        # Das gekürzte Deck zeigt nicht mehr jeden Schritt, sondern Vorprüfung und Self-Check.
        ("Wir verfolgen beide Fragen durch jeden Schritt der Pipeline.",
         "Wir verfolgen sie durch die Pipeline."),
        # Q2 heisst überall «Alltag» (Badge-Tooltips, F4).
        ("</span></span> · umgangssprachlich</div>", "</span></span> · Alltag</div>"),
    ]),
    ("V2", 4, 2, [
        (PHASES_RE, FLOW_SVG),
    ]),
    ("V2", 11, 2, [
        # Glossar (README, Begriffs-Review 20.09.): 0,35 ist eine «Schwelle»; «Grenze» nur für die Eval-Ziele.
        ("liegen unter der Grenze", "liegen unter der Schwelle"),
        ('<span class="status">Grenze 0,35</span>', '<span class="status">Schwelle 0,35</span>'),
        # ★ erklären: markiert den Abschnitt mit der Antwort — bei Q2 Rang 3, darauf zeigt das [3] auf F5.
        ("Schwarze Linie = Grenze 0,35.", "★ = Abschnitt mit der Antwort. Schwarze Linie = Schwelle 0,35."),
    ]),
    # Self-Check; 0,45/0,75 am 21.09. gegen die config-Tabelle geprüft.
    # Gekürzt: kürzerer Lead, ohne Take, ohne Prompt-Regeln; dafür die ausgelieferte
    # Antwort von Q2 (wörtlich aus Pipeline-Trace/Q2.json, Band mittel, Self-Check GEDECKT).
    ("V2", 16, 2, [
        ("Bei mittlerem Vertrauen bekommt das Modell die eigene Antwort noch einmal vorgelegt – "
         "zusammen mit den fünf Abschnitten – und muss urteilen, ob jede Aussage darin steht.",
         "Bei mittlerem Vertrauen prüft das Modell die eigene Antwort gegen die fünf Abschnitte."),
        (re.compile(r'[ \t]*<div class="take good">Fail-closed.*?</div>\n'), ""),
        # Die Formel wandert nach rechts ins Flussdiagramm.
        (re.compile(r'[ \t]*<div class="formula">.*?</div>\n'), ""),
        # Rechts nur noch Q2 als Flussdiagramm: Band-Prüfung → Self-Check (die drei
        # Prompt-Regeln in einem Satz) → ausgelieferte Antwort. Q1 fällt weg.
        (re.compile(r'[ \t]*<div class="blk">.*?</div>\n', re.S), SELFCHECK_SVG),
        (re.compile(r'[ \t]*<div class="bigpair".*?\n          </div>\n', re.S), ""),
    ]),
    # Evaluation: Eval als Ablauf in drei Schritten (V2 statt V3 F15, die dasselbe als Liste zeigt).
    # Umgebaut: Schritte 1–3 untereinander, danach eine Karte pro Fragetyp mit Erklärung
    # und gefordertem Wert (statt Kategorien nach 1 und Grenzen nach 3).
    ("V2", 18, 3, [
        (re.compile(r'[ \t]*<div class="phases">.*?<div class="gates">.*?\n          </div>\n', re.S), EVAL_PANEL),
        # Beispieleintrag an gold-eval-dataset.yaml (SKOS-PRINZ-02) angeglichen: pages: [6, 8] ist
        # eine Liste einzelner PDF-Seiten, kein Bereich; dazu die Referenzantwort (gekürzt), damit
        # der Eintrag zeigt, was «richtige Antwort, die man schon kennt» heisst.
        ('<span class="k">expected_refusal:</span> <span class="ok">false</span>\n'
         '<span class="k">expected_source:</span>  Seiten 6–8 · A.3 Prinzipien der Sozialhilfe</div>',
         '<span class="k">expected_refusal:</span> <span class="ok">false</span>\n'
         '<span class="k">reference_answer:</span> <span class="k"># gekürzt</span>\n'
         '  Deckt einen aktuellen Bedarf – nicht die\n'
         '  Vergangenheit, keine Übernahme von Schulden.\n'
         '<span class="k">expected_source:</span>  Seiten 6 und 8 · A.3 Prinzipien der Sozialhilfe</div>'),
    ]),
]


def split_slides(name: str, html: str) -> tuple[str, list[str], str]:
    """Teilt in Kopf, Folien (<section class="slide ...">, verschachtelte
    <section> innerhalb einer Folie inklusive) und Fuss.

    Eine Folie ohne schliessendes </section> endet an </main> — so ist die
    letzte Folie von V2 («Gold muss Gold sein») abgeschnitten archiviert."""
    main_end = html.rfind("\n", 0, html.find("</main>")) + 1
    slides, pos, head_end = [], 0, None
    while (start := html.find('<section class="slide', pos, main_end)) != -1:
        line_start = html.rfind("\n", 0, start) + 1
        if head_end is None:
            head_end = line_start
        depth, i, end = 0, start, None
        while True:
            nxt_open = html.find("<section", i, main_end)
            nxt_close = html.find("</section>", i, main_end)
            if nxt_close == -1:
                print(f"  Warnung: {name} F{len(slides) + 1} ist nicht geschlossen — endet an </main>")
                end = main_end
                break
            if nxt_open != -1 and nxt_open < nxt_close:
                depth, i = depth + 1, nxt_open + len("<section")
            else:
                depth, i = depth - 1, nxt_close + len("</section>")
                if depth == 0:
                    end = html.find("\n", i) + 1
                    break
        slides.append(html[line_start:end])
        pos = end
    return html[:head_end], slides, html[pos:]


parsed = {k: split_slides(k, p.read_text(encoding="utf-8")) for k, p in SOURCES.items()}
for k, (_, s, _) in parsed.items():
    print(f"{k}: {len(s)} Folien")

# wrail = Wege-Leiste aus V3, prail = Phasen-Leiste aus V2; beide ersetzt die Bereichsleiste.
RAIL_RE = re.compile(r'[ \t]*<div class="[wp]rail">.*?</div>\n')
EYEBROW_RE = re.compile(r'([ \t]*)<div class="eyebrow">.*?</div>\n')


def rail(section: int) -> str:
    spans = "".join(
        f'<span class="{"on" if i == section else "done" if i < section else ""}">{name}</span>'
        for i, name in enumerate(SECTIONS, start=1)
    )
    return f'<div class="wrail">{spans}</div>'


out_slides = []
for src, n, section, fixes in SLIDES:
    slide = parsed[src][1][n - 1]
    for old, new in fixes:
        if isinstance(old, re.Pattern):
            slide, hits = old.subn(lambda _: new, slide)
            label = old.pattern
        else:
            hits = slide.count(old)
            slide = slide.replace(old, new)
            label = old
        if hits != 1:
            raise SystemExit(f"{src} F{n}: Korrektur trifft {hits}× statt 1×: {label[:60]}")
    # Leiste + Eyebrow neu: alte Leiste (nur V3) raus, beides vor dem Titel neu setzen.
    slide = RAIL_RE.sub("", slide)
    m = EYEBROW_RE.search(slide)
    if not m:
        raise SystemExit(f"{src} F{n}: keine Eyebrow gefunden")
    indent = m.group(1)
    slide = slide[:m.start()] + (
        f"{indent}{rail(section)}\n"
        f'{indent}<div class="eyebrow">{SECTIONS[section - 1]}</div>\n'
    ) + slide[m.end():]
    slide = slide.replace('<section class="slide active"', '<section class="slide"', 1)
    out_slides.append(slide)
out_slides[0] = out_slides[0].replace('<section class="slide"', '<section class="slide active"', 1)

head, _, tail = parsed["V3"]
if head.count("  </style>") != 1:
    raise SystemExit("V3: </style> nicht eindeutig")
head = head.replace("  </style>", EXTRA_CSS + "  </style>")
deck = head + "".join(out_slides) + tail


# Bilder einbetten: ein relativer Pfad bricht, sobald die Datei allein
# weitergegeben oder in einer Vorschau geöffnet wird.
def embed(m: re.Match) -> str:
    img = BASE / m.group(1)
    return f'src="data:image/png;base64,{base64.b64encode(img.read_bytes()).decode()}"'


# Optional eine leichte Kopie ohne eingebettete Bilder (für Vorschau-Tools mit Grössenlimit).
# PREVIEW_SLIDE=n startet diese Kopie auf Folie n.
if preview := os.environ.get("PREVIEW_OUT"):
    start = int(os.environ.get("PREVIEW_SLIDE", "1")) - 1
    Path(preview).write_text(deck.replace("showSlide(0);\n  </script>", f"showSlide({start});\n  </script>"),
                             encoding="utf-8")

deck = re.sub(r'src="(assets/[^"]+\.png)"', embed, deck)
OUT.write_text(deck, encoding="utf-8")
print(f"Folien: {len(out_slides)} -> {OUT.name}")
