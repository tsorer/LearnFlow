# LearnFlow — Pilotstart-Checkliste

*Erstellt: 2026-06-04 · Verantwortlich: Entwicklungsteam (Frank, Niklaus, Reto, Christoph)*

Diese Checkliste beschreibt alle Schritte, die **vor dem ersten Login eines echten Nutzers** abgeschlossen sein müssen.

---

## 1 · Infrastruktur

| # | Aufgabe | Verantwortlich | Status |
|---|---------|---------------|--------|
| 1.1 | Docker Compose läuft stabil auf dem Pilot-Server (API, Frontend, PostgreSQL, Worker) | Dev | ⬜ |
| 1.2 | Täglicher `pg_dump`-Cron in Docker Compose konfiguriert und getestet (Backup landet in `/backups/`) | Dev | ⬜ |
| 1.3 | Backup-Restore einmal durchgespielt (Wiederherstellung verifiziert) | Dev | ⬜ |
| 1.4 | `.env`-Datei auf Server mit Produktionswerten befüllt (kein `localhost`, kein `dev`-Key) | Dev | ⬜ |
| 1.5 | `JWT_SECRET` auf starken Zufallswert gesetzt (`openssl rand -hex 32`); Standardwert `changeme*` wurde **nie** deployed | Dev | ⬜ |
| 1.6 | TLS-Zertifikat auf dem Server eingerichtet; HTTP→HTTPS-Redirect in `nginx.conf` aktiviert (auskommentierter Block); `Strict-Transport-Security`-Header einkommentiert | Dev | ⬜ |
| 1.7 | Alle Seed-Passwörter (`changeme1`–`changeme6`) durch starke individuelle Passwörter ersetzt (`make seed` mit angepasstem `seed_users.py` oder direktem DB-Update) | Dev | ⬜ |

---

## 2 · Provider-Umstellung (Compliance-Blocker)

| # | Aufgabe | Verantwortlich | Status |
|---|---------|---------------|--------|
| 2.1 | LiteLLM-`config` auf **Azure OpenAI EU** umgestellt (kein OpenAI Direct US mehr) | Dev | ⬜ |
| 2.2 | Embedding-Modell ebenfalls auf Azure OpenAI EU konfiguriert | Dev | ⬜ |
| 2.3 | Smoke-Test: eine Frage stellen, Antwort mit Quellenangabe erscheint korrekt | Dev | ⬜ |

---

## 3 · Datenbank initialisieren

### 3.1 Schema anlegen

```bash
docker compose exec api python -m alembic upgrade head
```

### 3.2 Initialkonfiguration in `config`-Tabelle setzen

```sql
-- Konfidenz-Schwellenwerte (empirisch anpassen nach Pilot-Erfahrung)
INSERT INTO config (key, value) VALUES
  ('confidence_threshold_high',  '0.75'),
  ('confidence_threshold_medium', '0.45'),
  ('stale_threshold_days',       '90');
```

> Die Werte können nach dem Pilotstart über die Admin-Seite (US-11) ohne Deployment angepasst werden.

---

## 4 · Accounts anlegen (DB-Script)

Kein Admin-UI im MVP — Accounts werden manuell per SQL angelegt.

### Rollen

| Rolle | Beschreibung |
|-------|-------------|
| `admin` | Technische Konfiguration (Schwellenwerte, System) |
| `user` | Lernende und Bereichsverantwortliche (inkl. Stefan) |

> **Hinweis:** Bereichsverantwortliche (Stefan-Rolle) haben im MVP dieselbe Rolle `user` wie Lernende — die Unterscheidung erfolgt durch separate Navigations-Rechte im Frontend (Upload/Dashboard für Stefan sichtbar).

### Script

```sql
-- Passwörter als bcrypt-Hash (z. B. mit `python -c "import bcrypt; print(bcrypt.hashpw(b'passwort', bcrypt.gensalt()).decode())"`)

INSERT INTO users (username, password_hash, role) VALUES
  ('stefan.muster',   '<bcrypt-hash>', 'user'),   -- Bereichsverantwortlicher
  ('lara.beispiel',   '<bcrypt-hash>', 'user'),   -- Lernende (Beispiel)
  ('admin',           '<bcrypt-hash>', 'admin');  -- Technischer Admin
```

### Passwort-Hash generieren

```bash
docker compose exec api python -c \
  "import bcrypt; print(bcrypt.hashpw(b'PASSWORT_HIER', bcrypt.gensalt()).decode())"
```

> Passwörter **nie** im Klartext in SQL-Skripten speichern. Hash lokal generieren, dann einfügen.

---

## 5 · Initialer Lernkorpus

| # | Aufgabe | Verantwortlich | Status |
|---|---------|---------------|--------|
| 5.1 | Stefan ist eingeloggt und hat Zugriff auf Upload-Funktion getestet | Stefan / Dev | ⬜ |
| 5.2 | Mindestens 3 Pilot-Dokumente hochgeladen (PDF/DOCX/MD) | Stefan | ⬜ |
| 5.3 | Chunking und Embedding erfolgreich durchgelaufen (Worker-Log geprüft) | Dev | ⬜ |
| 5.4 | Testfrage aus Pilot-Dokument gestellt — Antwort mit korrekter Quellenangabe | Stefan + Dev | ⬜ |

---

## 6 · Smoke-Test vor Go-Live

| # | Test | Erwartetes Ergebnis |
|---|------|---------------------|
| 6.1 | Login mit gültigem Account | Weiterleitung auf Dashboard |
| 6.2 | Login mit falschem Passwort | Fehlermeldung, kein Zugang |
| 6.3 | Frage aus Korpus stellen | Antwort mit Quellenlink + Seitenangabe |
| 6.4 | Frage ausserhalb Korpus stellen | «Weiss ich nicht»-Antwort (kein Halluzinieren) |
| 6.5 | Dokument hochladen (Stefan) | Erfolgsmeldung, Dokument erscheint in Liste |
| 6.6 | Backup-Cron ausgeführt | Dump-Datei in `/backups/` vorhanden |

---

## 7 · Go-Live-Freigabe

- [ ] Alle Blocker-Punkte aus dieser Liste abgehakt
- [ ] Provider auf Azure OpenAI EU umgestellt (Punkt 2)
- [ ] Backup verifiziert (Punkt 1.3)
- [ ] Stefan hat Smoke-Test 6.4 (Out-of-Corpus) bestätigt
- [ ] **Go-Live erteilt durch:** ___________________  · Datum: ___________
