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
| 1.6 | TLS-Zertifikat auf dem Server eingerichtet und ins `webapp`-Image/Volume unter `/etc/nginx/certs/` gemountet | Dev | ⬜ |
| 1.6a | In `nginx.conf` **beide** TLS-Schritte ausgeführt: Redirect-Block einkommentiert **und** im Haupt-`server`-Block `listen 80` durch `listen 443 ssl` + `ssl_certificate*` ersetzt. Nur einer der beiden Schritte legt die App still (nginx meldet das bloss als Warnung) | Dev | ⬜ |
| 1.6b | `Strict-Transport-Security`-Header einkommentiert; danach `docker exec src-webapp-1 nginx -t` **ohne** Warnung `conflicting server name` und ein Aufruf über HTTPS erfolgreich geprüft | Dev | ⬜ |
| 1.7 | Alle Seed-Passwörter (`changeme1`–`changeme6`) durch starke individuelle Passwörter ersetzt (`make seed` mit angepasstem `seed_users.py` oder direktem DB-Update) | Dev | ⬜ |
| 1.8 | `EXPOSE_API_DOCS` in der Server-`.env` **nicht** gesetzt bzw. auf `false`. Gegenprobe: `/api/docs`, `/api/redoc` und `/api/openapi.json` liefern **404**. Eingeschaltet legen sie die vollständige API-Oberfläche ohne Authentifizierung offen | Dev | ⬜ |

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

### 3.2 Initialkonfiguration in `config`-Tabelle prüfen

Die Startwerte legen die Migrationen an (`0004`, `0007`, `0008`) — kein manuelles `INSERT` nötig.
Nur kontrollieren:

```sql
SELECT key, value FROM config ORDER BY key;
```

Nachjustieren (empirisch nach Pilot-Erfahrung) — **die beiden Konfidenz-Bänder in einer
Transaktion**, siehe Hinweis unten:

```sql
-- Konfidenz-Bänder (ADR-008 · US-02)
BEGIN;
UPDATE config SET value = '0.75' WHERE key = 'confidence_threshold_high';
UPDATE config SET value = '0.45' WHERE key = 'confidence_threshold_medium';
COMMIT;
-- Stale-Schwelle (US-06)
UPDATE config SET value = '90'   WHERE key = 'stale_days';
```

> Änderungen wirken sofort — die Werte werden pro Anfrage gelesen, kein Service-Neustart nötig.
> Nach dem Pilotstart sind sie über die Admin-Seite (US-11) ohne Deployment anpassbar.

> **Warum `BEGIN; … COMMIT;`** (Migration `0009`, ADR-008 Nachtrag 2026-08-16): Die Datenbank
> lehnt einen Konfidenz-Wert ab, der keine Zahl in [0, 1] ist (`0,90` mit Komma etwa), und
> ebenso `medium` über `high`. Die Prüfung der Band-Reihenfolge ist auf das Transaktionsende
> aufgeschoben. psql arbeitet ohne `BEGIN` im Autocommit — jedes `UPDATE` ist dann seine eigene
> Transaktion, und beim **Senken beider Bänder** scheitert schon das erste, weil dazwischen
> kurz `medium > high` gilt. Innerhalb einer Transaktion ist die Reihenfolge egal.
>
> Eine Fehlermeldung hier heisst: der Wert ist **nicht** gesetzt worden. Das ist Absicht —
> früher fiel ein solcher Wert stillschweigend auf die lockereren Startwerte zurück.

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
