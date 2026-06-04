# CLAUDE.md

## Zweck dieser Datei

Nur Meta-Informationen und Referenzen. **Keine inhaltlichen Entscheide hier** — die gehören in `Docs/`.

---

## Single Source of Truth

**`Docs/` ist die einzige massgebliche Quelle** für alle Projektentscheide, Anforderungen und Architektur. Vor jeder nicht-trivialen Entscheidung zuerst den `Docs/`-Ordner konsultieren.

Operative Dokumente (Setup, Checklisten, Runbooks) liegen in `Ops/`.

Historische Kursartefakte liegen in `Artefakten/` — können veraltete oder fehlerhafte Inhalte enthalten; `Docs/` hat Vorrang.

---

## Repository-Konventionen

- **`Artefakten/Modul{N}Tag{M}/`** — Kursartefakte nach Modul/Tag; nicht reorganisieren.
- **Sprache:** Artefakte und Ordnernamen auf Deutsch. Code-Identifier und Commits English oder Deutsch — Kontext beachten.
- Leere `Artefakten/`-Unterordner sind Platzhalter für kommende Kurstage; Git trackt leere Verzeichnisse nicht.
