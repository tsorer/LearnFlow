"""Baut Block 5 (Fazit & Ausblick) auf derselben Vorlage wie Block 2.

Ordner (relativ zu dieser Datei):
    ../Archive/Block2_Technischer-Aufbau.html   Vorlage: CSS, Navigation und vier Folien
    ../Archive/Block5_Fazit-Ausblick.html   Ergebnis
    ../assets/                                  Bilder (wird bei Bedarf aus Archive kopiert)

Aufruf:  python build_block5.py
"""

import re
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
TEMPLATE = BASE / "Archive" / "Block2_Technischer-Aufbau.html"
DIR = BASE / "Archive"          # alte Stände bleiben im Archiv
OUT = DIR / "Block5_Fazit-Ausblick.html"

# Bilder müssen neben dem Ergebnis liegen, sonst lädt das Lara-Portrait nicht.
if not (DIR / "assets").exists() and (BASE / "Archive" / "assets").exists():
    shutil.copytree(BASE / "Archive" / "assets", DIR / "assets")

v1 = TEMPLATE.read_text(encoding="utf-8")
head, rest = v1.split('  <main class="deck"', 1)
tail = rest[rest.index("  </main>") + len("  </main>"):]

EXTRA_CSS = """
    /* ── Ergänzungen für Block 5 ─────────────────────────────────────── */
    .levers { display: grid; gap: 12px; }
    .lever {
      display: grid; grid-template-columns: 58px 1fr; gap: 16px; align-items: center;
      padding: 16px 18px; border: 1px solid var(--line); border-radius: 16px; background: var(--white);
      box-shadow: 0 7px 18px rgba(16, 30, 54, .05);
    }
    .lever b {
      display: grid; place-items: center; width: 50px; height: 50px; border-radius: 14px;
      background: var(--teal-pale); color: var(--teal-dark); font-size: 19px; font-weight: 840;
    }
    .lever h3 { margin: 0 0 4px; color: var(--ink); font-size: 19px; font-weight: 790; letter-spacing: -.02em; }
    .lever p { margin: 0; color: var(--muted); font-size: 16px; font-weight: 620; line-height: 1.35; }
    .lever.top { border-color: rgba(15, 168, 160, .45); }
    .lever.top b { background: var(--teal); color: var(--white); }
    .rank td.model { white-space: normal; }
    .rank td.model small { display: block; color: var(--muted); font-size: 13px; font-weight: 600; }
    .rank tr.ref td { background: var(--paper); }
    .rank td.hi { color: var(--coral-dark); font-weight: 800; }

    /* Wortsuche-Folie: Befunde und Q-Abzeichen wie in Block 2 */
    :root { --q1: #2f5bd3; --q2: #8b3fd9; }
    .qb {
      display: inline-flex; align-items: center; gap: .32em; vertical-align: .06em;
      padding: .16em .55em .16em .38em; border-radius: 99px; color: #fff;
      font-size: 18px; font-weight: 850; line-height: 1.15; white-space: nowrap;
    }
    .qb.q1 { background: var(--q1); }
    .qb.q2 { background: var(--q2); }
    .qb .qi { display: inline-grid; place-items: center; width: 1.25em; height: 1.25em; border-radius: 50%; background: rgba(255,255,255,.22); font-weight: 900; }
    .qb .qi svg { width: .82em; height: .82em; display: block; }
    .insights { display: grid; gap: 14px; }
    .insight { display: grid; grid-template-columns: 130px 1fr; gap: 20px; align-items: center; padding: 20px 22px; border-radius: 18px; background: var(--white); border: 1px solid var(--line); }
    .insight strong { color: var(--amber-dark); font-size: 40px; font-weight: 850; letter-spacing: -.05em; line-height: 1; }
    .insight.bad strong { color: var(--coral-dark); }
    .insight h3 { margin: 0 0 6px; color: var(--ink); font-size: 20px; font-weight: 800; }
    .insight p { margin: 0; color: var(--muted); font-size: 16.5px; font-weight: 620; line-height: 1.4; }

    /* Bilanz-Folie Wortsuche */
    .tri { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 18px; }
    .tri div { padding: 18px 18px 16px; border-radius: 18px; background: var(--paper); }
    .tri b { display: block; font-size: 58px; font-weight: 850; letter-spacing: -.05em; line-height: 1; color: var(--ink); }
    .tri span { display: block; margin-top: 8px; font-size: 16px; font-weight: 750; color: var(--text); }
    .tri .up { background: var(--teal-pale); }
    .tri .up b { color: var(--teal-dark); }
    .tri .down { background: var(--coral-pale); }
    .tri .down b { color: var(--coral-dark); }
    .case { padding: 16px 18px; border-radius: 16px; background: var(--white); border: 1px solid var(--line); border-left: 5px solid var(--teal); }
    .case + .case { margin-top: 12px; }
    .case.down { border-left-color: var(--coral); }
    .case .tag { display: inline-block; margin-bottom: 6px; padding: 3px 10px; border-radius: 99px; font-size: 13px; font-weight: 850; letter-spacing: .06em; text-transform: uppercase; background: var(--teal-pale); color: var(--teal-dark); }
    .case.down .tag { background: var(--coral-pale); color: var(--coral-dark); }
    .case .qq { color: var(--ink); font-size: 18px; font-weight: 750; line-height: 1.35; }
    .case .rr { margin-top: 6px; color: var(--muted); font-size: 16px; font-weight: 650; line-height: 1.4; }
    .case .rr b { color: var(--ink); }
    .mininote { margin-top: 12px; color: var(--muted); font-size: 14px; font-weight: 620; }
    .content.single { grid-template-columns: 1fr; }
    .content.single .story { max-width: 1100px; }
    h1.big { max-width: 1100px; font-size: 76px; }
    .lead.big { max-width: 900px; font-size: 26px; }
"""
marker = "\n    @media (prefers-reduced-motion: reduce)"
assert head.count(marker) == 1
head = head.replace(marker, EXTRA_CSS + marker)
head = head.replace("<title>LearnFlow – Technischer Aufbau</title>", "<title>LearnFlow – Fazit und Ausblick</title>")

TOP = """      <header class="topbar">
        <div class="brand"><span class="brand-mark" aria-hidden="true">LF</span><span>LearnFlow</span></div>
        <div class="context" data-title="Fazit &amp; Ausblick"></div>
      </header>"""

SLIDES = f"""  <main class="deck" aria-label="LearnFlow Fazit und Ausblick">

    <!-- ═══ 1 · Was wir gelernt haben ═════════════════════════════════ -->
    <section class="slide active" aria-label="Was wir gelernt haben">
{TOP}
      <div class="content">
        <div class="story">
          <div class="eyebrow">Fazit</div>
          <h1>Zielwerte sind <span class="accent">Hypothesen</span>, bis man sie kalibriert</h1>
          <p class="lead">Die 15 % für fälschlich unterdrückte Antworten waren ein Startwert. Bestätigt wurde er nie – gemessen haben wir 22,2 %.</p>
          <div class="learning">
            <strong>Learning</strong>
            Ein «verfehlt» gegen eine unbestätigte Hypothese misst die Hypothese, nicht die Pipeline.
          </div>
        </div>
        <div class="panel">
          <div class="panel-label"><span>Zielwert und Messung</span><span class="status">Referenzmodell gpt-4o-mini</span></div>
          <div class="comparison">
            <section class="filtered">
              <h2>Zielwert · ADR-009</h2>
              <div class="metric">Startwert<br><strong>≤ 15 %</strong></div>
              <div class="outcome">«nach dem ersten Kalibrierungslauf zu bestätigen» – dieser Lauf hat nie stattgefunden</div>
            </section>
            <section class="good">
              <h2>Gemessen · 80 Fragen</h2>
              <div class="metric">fälschlich unterdrückt<br><strong>22,2 %</strong></div>
              <div class="outcome">von 31,1 % gesenkt, in vier Optimierungsrunden</div>
            </section>
          </div>
          <p class="sub-label" style="margin-top:26px">Bewusst offen</p>
          <div class="criteria" style="margin-top:0">
            <div class="criterion">T-57<br>Schwellen kalibrieren statt raten</div>
            <div class="criterion">T-65<br>Gold-Dataset bereinigen</div>
            <div class="criterion">T-63 / T-64<br>Architektur und Konfiguration</div>
          </div>
        </div>
      </div>
      <div class="page-number"></div>
    </section>

    <!-- ═══ 2 · Die Wortsuche kann schaden ════════════════════════════ -->
    <section class="slide" aria-label="Die Wortsuche kann schaden">
{TOP}
      <div class="content">
        <div class="story">
          <div class="eyebrow">Fazit · aus dem Beispiel</div>
          <h1>Die Wortsuche kann <span class="accent">schaden</span></h1>
          <p class="lead">Wir haben sie für exakte Fachbegriffe eingebaut. Bei Alltagssprache hat sie im Beispiel die richtige Antwort nach hinten gedrückt – und Fremdes hereingeholt.</p>
          <div class="learning">
            <strong>Learning</strong>
            Zwei Suchen sind nicht automatisch besser als eine. Wo die Wortsuche hilft und wo sie schadet, muss gemessen werden – nicht angenommen.
          </div>
        </div>
        <div class="panel">
          <div class="panel-label"><span>Im Beispiel</span><span class="status">beide Antworten trotzdem richtig</span></div>
          <div class="insights">
            <div class="insight"><strong>1 → 5</strong><div><h3><span class="qb q1"><span class="qi">§</span>Q1</span> Die Antwort wurde verdrängt</h3><p>Die Bedeutungssuche hatte sie auf Platz 1. Die Wortsuche kannte sie nicht – nach dem Mischen blieb Platz 5, der letzte, den das Modell sieht. Knapp drin.</p></div></div>
            <div class="insight bad"><strong>2 von 5</strong><div><h3><span class="qb q2"><span class="qi"><svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M2 2.5h12a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7l-3.5 3v-3H2a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1z"/></svg></span>Q2</span> Fremdes kam herein</h3><p>Die Wortsuche fand praktisch nur «wurde» – und brachte zwei Abschnitte aus dem EU AI Act in den Kontext.</p></div></div>
          </div>
          <div class="finding">
            <strong>Ein Platz tiefer, und das Modell hätte die Antwort nie gesehen.</strong> Über alle 80 Fragen des Gold-Datasets dasselbe Muster: In 13 von 15 Fällen lag die fehlende Quelle in der Kandidatenliste – nur nicht unter den fünf, die ins Modell gehen.
          </div>
        </div>
      </div>
      <div class="page-number"></div>
    </section>

    <!-- ═══ 3 · Hilft oder schadet? Beides. ═══════════════════════════ -->
    <section class="slide" aria-label="Hilft oder schadet">
{TOP}
      <div class="content">
        <div class="story">
          <div class="eyebrow">Fazit · nachgemessen</div>
          <h1>Hilft oder schadet? <span class="accent">Beides.</span></h1>
          <p class="lead">Nachgerechnet über die 56 Gold-Fragen mit bekannter Antwortseite: Was wäre mit der Bedeutungssuche allein ins Modell gegangen?</p>
          <div class="learning">
            <strong>Learning</strong>
            Unterm Strich fast neutral – 77,2 % statt 76,6 % der Antwortseiten im Kontext. Die Wortsuche hilft bei Fachbegriffen und Abkürzungen und schadet bei allgemeinen Formulierungen. Blindes Mischen nutzt nur die eine Hälfte.
          </div>
        </div>
        <div class="panel">
          <div class="panel-label"><span>Wortsuche · 56 Gold-Fragen</span><span class="status">Referenzmodell, Runde R04</span></div>
          <div class="tri">
            <div class="up"><b>3</b><span>hilft – Antwortseite nur dank Wortsuche im Kontext</span></div>
            <div class="down"><b>5</b><span>schadet – Antwortseite verdrängt</span></div>
            <div><b>48</b><span>kein Unterschied</span></div>
          </div>
          <div class="case">
            <span class="tag">hilft</span>
            <div class="qq">«Wann ist das Humanforschungsgesetz (HFG) in Kraft getreten …?»</div>
            <div class="rr">Bedeutung: Platz 7 · Wörter: <b>Platz 1</b> → im Kontext, Antwort geliefert</div>
          </div>
          <div class="case down">
            <span class="tag">schadet</span>
            <div class="qq">«Was umfasst die medizinische Grundversorgung in der Sozialhilfe?»</div>
            <div class="rr">Bedeutung: <b>Platz 1</b> · Wörter: nicht gefunden → verdrängt, <b>«Weiss ich nicht»</b></div>
          </div>
          <div class="mininote">Verglichen wird, welche Seiten ins Modell gehen – nicht, wie die Antwort ohne Wortsuche ausgefallen wäre.</div>
        </div>
      </div>
      <div class="page-number"></div>
    </section>

    <!-- ═══ 2 · Was wir als Nächstes messen würden ════════════════════ -->
    <section class="slide" aria-label="Was wir als Nächstes messen würden">
{TOP}
      <div class="content">
        <div class="story">
          <div class="eyebrow">Ausblick</div>
          <h1>Was wir als Nächstes <span class="accent">messen</span> würden</h1>
          <p class="lead">Geordnet nach gemessener Wirkung, nicht nach Aufwand.</p>
          <div class="learning">
            <strong>Die Antwort auf «Beides»</strong>
            Ein Re-Ranker bewertet die Kandidaten nach Inhalt, bevor auf fünf geschnitten wird – statt nur nach Platz. Das Ziel: den Nutzen der Wortsuche behalten, ohne dass sie verdrängt.
          </div>
        </div>
        <div class="panel">
          <div class="panel-label"><span>Stellschrauben</span><span class="status">aus der Optimierung T-62</span></div>
          <div class="levers">
            <div class="lever top"><b>P1</b><div><h3>Re-Ranker zwischen Fusion und Gate</h3><p>+17 Prozentpunkte Kopfraum: Die Quelle ist in 94,5 % der Fälle unter den Kandidaten, aber nur in 77,2 % im Kontext.</p></div></div>
            <div class="lever"><b>P2</b><div><h3>Self-Check Satz für Satz</h3><p>«Stützt Abschnitt [n] diesen Satz?» statt eines Gesamturteils – das kann auch ein kleines Modell kaum missverstehen.</p></div></div>
            <div class="lever"><b>P3</b><div><h3>Stufe 0 und 1 ersetzen</h3><p>Über 80 Fragen haben sie keine einzige Anfrage blockiert. Abschaffen oder durch einen inhaltlichen Relevanzentscheid ersetzen.</p></div></div>
            <div class="lever"><b>P4</b><div><h3>Embedding-Modell messen</h3><p>Das heutige Modell ist englischzentriert, der Korpus Verwaltungsdeutsch. Der einzige Hebel, der die Obergrenze selbst anhebt.</p></div></div>
          </div>
        </div>
      </div>
      <div class="page-number"></div>
    </section>

    <!-- ═══ 3 · Lokale Modelle ════════════════════════════════════════ -->
    <section class="slide" aria-label="Lokale Modelle">
{TOP}
      <div class="content">
        <div class="story">
          <div class="eyebrow">Ausblick · Lokale Modelle</div>
          <h1>Machbar. <span class="accent">Noch nicht gut genug.</span></h1>
          <p class="lead">Ein Modellwechsel ist kein Komponententausch: Das Modell muss das Ausgabeprotokoll der Pipeline bedienen – «Weiss ich nicht», Belege, Prüfurteil.</p>
          <div class="learning">
            <strong>Für den Pilot</strong>
            Azure OpenAI EU ist gesetzt. Lokale Modelle sind die Stufe danach – und wir wissen jetzt, woran sie zu messen sind.
          </div>
        </div>
        <div class="panel">
          <div class="panel-label"><span>Fünf Modelle, gleiche Pipeline</span><span class="status">Runde R04</span></div>
          <table class="rank">
            <thead><tr><th>Modell</th><th>fremde Fragen<br>verweigert</th><th>richtige<br>unterdrückt</th><th>Zeit pro<br>Antwort</th></tr></thead>
            <tbody>
              <tr class="ref"><td class="model">gpt-4o-mini<small>Referenz · Cloud</small></td><td class="num">90,9 %</td><td class="num">22,2 %</td><td class="num">1,2 s</td></tr>
              <tr><td class="model">ministral-3:14b<small>Mistral · EU-Anbieter</small></td><td class="num">95,5 %</td><td class="num hi">40,0 %</td><td class="num">16,0 s</td></tr>
              <tr><td class="model">gpt-oss:20b<small>OpenAI · offene Gewichte</small></td><td class="num">95,5 %</td><td class="num hi">37,8 %</td><td class="num">10,4 s</td></tr>
              <tr><td class="model">gemma4:26b<small>Google</small></td><td class="num">86,4 %</td><td class="num">11,1 %</td><td class="num hi">58,3 s</td></tr>
              <tr><td class="model">qwen3:8b<small>Alibaba</small></td><td class="num hi">68,2 %</td><td class="num">6,7 %</td><td class="num">5,9 s</td></tr>
            </tbody>
          </table>
          <div class="finding">
            <strong>Zu vorsichtig ist auch ein Fehler:</strong> Die beiden Modelle, die fremde Fragen am besten ablehnen, unterdrücken auch am meisten richtige Antworten. Und kein lokales Modell passt mit vollem Kontext in die 8 GB Grafikspeicher der Testmaschine.
          </div>
        </div>
      </div>
      <div class="page-number"></div>
    </section>

    <!-- ═══ 4 · Schluss ═══════════════════════════════════════════════ -->
    <section class="slide" aria-label="Schluss">
{TOP}
      <div class="content single">
        <div class="story">
          <div class="eyebrow">Schluss</div>
          <h1 class="big">Keine Antwort ohne Beleg. <span class="accent">Das hält.</span></h1>
          <p class="lead big">Was wir dazugelernt haben: Der Beleg dafür, dass es hält, ist die eigentliche Arbeit.</p>
        </div>
      </div>
      <div class="page-number"></div>
    </section>

"""

OUT.write_text(head + SLIDES + "  </main>" + tail, encoding="utf-8")
print("ok")
