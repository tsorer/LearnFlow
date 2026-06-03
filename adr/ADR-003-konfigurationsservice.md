# ADR-003 · Konfigurationsservice: PostgreSQL mit In-Process-Cache und Audit-Log

| | |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Autor** | LearnFlow Architecture Team |
| **Bezug** | US-02, US-06, US-11, QA-04 (Reliability), QA-05 (Maintainability) |
| **Massnahme** | M7 |

---

## Kontext

Drei User Stories setzen voraus, dass Systemparameter zur Laufzeit änderbar sind — ohne Code-Deployment und ohne Applikations-Neustart:

| Parameter | Story | Standardwert |
|---|---|---|
| Konfidenz-Schwellenwert (`min_confidence_score`) | US-02 | TBD (via Spike) |
| Self-Check-Suppress-Schwellenwert (`suppress_threshold`) | US-02 | 0.50 |
| Self-Check-Limited-Schwellenwert (`limited_threshold`) | US-02 | 0.80 |
| Stale-Schwellenwert in Tagen (`stale_days`) | US-06 | 90 |

US-11 ergänzt: *Konfigurationsänderungen werden mit Zeitstempel und ausführender Person protokolliert.* Änderungen müssen sofort wirken. Die Admin-Seite (US-11) und das DB-Script sind beide valide Schreibwege.

Das zentrale Problem mit ENV-Variablen oder Config-Files: sie erfordern einen Neustart, um neu gelesen zu werden. Das widerspricht der MUST-Anforderung.

---

## Entscheidung

Konfigurationsparameter werden in der **bestehenden PostgreSQL-Datenbank** gespeichert. Ein zentraler `ConfigService` liest Werte über einen **In-Process-Cache mit TTL und sofortiger Invalidierung beim Schreiben**. Alle Schreiboperationen werden transaktionssicher in einem unveränderlichen **Audit-Log** protokolliert.

Der `ConfigService` ist hinter einem Interface definiert — in Tests wird er durch eine In-Memory-Implementierung ersetzt.

### Datenbankschema

```sql
-- Aktuelle Parameterwerte
CREATE TABLE config_params (
  key         TEXT PRIMARY KEY,
  value       TEXT        NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Initialbefüllung (via DB-Script oder Migration)
INSERT INTO config_params (key, value) VALUES
  ('min_confidence_score',  '0.65'),
  ('suppress_threshold',    '0.50'),
  ('limited_threshold',     '0.80'),
  ('stale_days',            '90');

-- Unveränderliches Audit-Log
-- Keine UPDATE- oder DELETE-Rechte für die Applikation auf dieser Tabelle
CREATE TABLE config_audit_log (
  id          BIGSERIAL   PRIMARY KEY,
  key         TEXT        NOT NULL,
  old_value   TEXT,                   -- NULL bei Erstanlage
  new_value   TEXT        NOT NULL,
  changed_by  TEXT        NOT NULL,   -- Username (kein FK: User könnte gelöscht werden)
  changed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Datenbankberechtigungen:**

| Tabelle | App-Rolle | Admin-UI-Rolle |
|---|---|---|
| `config_params` | SELECT, UPDATE | SELECT, UPDATE |
| `config_audit_log` | SELECT, INSERT | SELECT, INSERT |

Kein DELETE, kein TRUNCATE auf `config_audit_log` — weder für die App noch für die Admin-UI.

### Interface

```typescript
interface ConfigService {
  get(key: string): Promise<string>
  getNumber(key: string): Promise<number>
  getThresholds(): Promise<ConfidenceThresholds>
  set(key: string, value: string, changedBy: string): Promise<void>
}

type ConfidenceThresholds = {
  minConfidenceScore: number   // 'min_confidence_score'
  suppressThreshold:  number   // 'suppress_threshold'
  limitedThreshold:   number   // 'limited_threshold'
}
```

### Produktions-Implementierung (DBConfigService)

```typescript
class DBConfigService implements ConfigService {

  private cache = new Map<string, { value: string; expiresAt: number }>()
  private readonly TTL_MS = 30_000   // 30 Sekunden

  constructor(private db: Database) {}

  async get(key: string): Promise<string> {
    const cached = this.cache.get(key)
    if (cached && Date.now() < cached.expiresAt)
      return cached.value

    const row = await this.db.queryOne<{ value: string }>(
      'SELECT value FROM config_params WHERE key = $1', [key]
    )
    if (!row) throw new ConfigKeyNotFoundError(key)

    this.cache.set(key, { value: row.value, expiresAt: Date.now() + this.TTL_MS })
    return row.value
  }

  async getNumber(key: string): Promise<number> {
    const raw = await this.get(key)
    const n = parseFloat(raw)
    if (isNaN(n)) throw new ConfigValueError(key, raw)
    return n
  }

  async getThresholds(): Promise<ConfidenceThresholds> {
    const [minScore, suppress, limited] = await Promise.all([
      this.getNumber('min_confidence_score'),
      this.getNumber('suppress_threshold'),
      this.getNumber('limited_threshold')
    ])
    return {
      minConfidenceScore: minScore,
      suppressThreshold:  suppress,
      limitedThreshold:   limited
    }
  }

  async set(key: string, newValue: string, changedBy: string): Promise<void> {
    const oldValue = await this.get(key).catch(() => null)

    await this.db.transaction(async (tx) => {
      await tx.execute(
        'UPDATE config_params SET value = $1, updated_at = now() WHERE key = $2',
        [newValue, key]
      )
      await tx.execute(
        `INSERT INTO config_audit_log (key, old_value, new_value, changed_by)
         VALUES ($1, $2, $3, $4)`,
        [key, oldValue, newValue, changedBy]
      )
    })

    this.cache.delete(key)   // sofortige Invalidierung — nächster Lesezugriff trifft DB
  }
}
```

### Test-Implementierung (InMemoryConfigService)

```typescript
class InMemoryConfigService implements ConfigService {

  private store: Map<string, string>

  constructor(overrides: Record<string, string> = {}) {
    this.store = new Map({
      'min_confidence_score': '0.65',
      'suppress_threshold':   '0.50',
      'limited_threshold':    '0.80',
      'stale_days':           '90',
      ...overrides
    })
  }

  async get(key: string): Promise<string> {
    const v = this.store.get(key)
    if (!v) throw new ConfigKeyNotFoundError(key)
    return v
  }

  async getNumber(key: string): Promise<number> {
    return parseFloat(await this.get(key))
  }

  async getThresholds(): Promise<ConfidenceThresholds> { ... }

  async set(key: string, value: string, _changedBy: string): Promise<void> {
    this.store.set(key, value)    // kein Audit-Log nötig in Tests
  }
}
```

### Verhalten bei Änderungen

```
Zeitachse einer Schwellenwert-Änderung:

  t=0   Admin setzt suppress_threshold = 0.60 (via Admin-UI)
  t=0   ConfigService.set() → DB UPDATE + Audit-Log INSERT (1 Transaktion)
  t=0   cache.delete('suppress_threshold')
  t=1s  Nächste Anfrage an ConfidenceEvaluator: cache miss → DB-Lesezugriff
  t=1s  Neuer Wert 0.60 ist aktiv — kein Neustart, kein Deployment

  [Single-Instance-Betrieb: Änderung wirkt innerhalb von ~1 Sekunde]
  [Multi-Instance (Post-MVP): Wert wird auf anderen Instanzen spätestens
   nach TTL=30s aus DB gelesen]
```

---

## Begründung

**Warum nicht ENV-Variablen?**

ENV-Variablen werden beim Prozessstart eingelesen. Änderungen erfordern einen Neustart — das widerspricht der expliziten MUST-Anforderung aus US-11.

**Warum nicht Redis als primärer Config-Store?**

Redis würde Sub-Sekunden-Propagation bei mehreren App-Instanzen ermöglichen. Im MVP ist jedoch eine einzige App-Instanz geplant (20 concurrent users). Redis als neue Infrastrukturkomponente einzuführen, um ein 30-Sekunden-Propagationsproblem zu lösen, das im Pilotbetrieb nie auftreten wird, widerspricht dem Budget-Constraint (480 Stunden, 1 FTE Maintenance).

Der Upgrade-Pfad zu Redis (Option B) ist dokumentiert und kann bei Post-MVP-Skalierung ohne Änderung am Interface nachgerüstet werden.

**Warum sofortige Cache-Invalidierung bei `set()` statt reinem TTL?**

Rein TTL-basierter Cache bedeutet: direkt nach einer Admin-Änderung sieht dieselbe Instanz für bis zu 30 Sekunden den alten Wert. Das ist für Konfigurationsänderungen, die ein Admin gerade vorgenommen hat, eine schlechte Erfahrung und schwer zu debuggen. Sofortige Invalidierung bei `set()` kostet eine Zeile Code und eliminiert das Problem vollständig für Single-Instance.

**Warum kein FK von `changed_by` auf die `users`-Tabelle?**

Administratoren könnten aus der Datenbank gelöscht werden (z.B. Mitarbeitendenwechsel). Ein FK würde entweder den Löschvorgang blockieren oder das Audit-Log korrumpieren. Der Username als Text ist ausreichend für Audit-Zwecke und überlebt User-Löschoperationen.

---

## Betrachtete Alternativen

### Alternative 1 · ENV-Variablen / Config-File

Parameter in `.env` oder `config.yaml`, eingelesen beim Start.

**Abgelehnt**: Änderungen erfordern Neustart. Verletzt MUST-Anforderung US-11 direkt.

### Alternative 2 · Redis als Config-Store mit Pub/Sub-Invalidierung

```
Admin → UPDATE config_params (PostgreSQL) + PUBLISH config:invalidate (Redis)
Alle Instanzen → SUBSCRIBE → cache.delete(key)
```

**Nicht abgelehnt, sondern zurückgestellt**: Korrekte Architektur für Multi-Instance-Betrieb. Für MVP (Single-Instance, 20 Users) unverhältnismässig. Interface bleibt kompatibel — Upgrade ohne Business-Logik-Änderung möglich.

**Upgrade-Trigger:** Wenn mehr als eine App-Instanz betrieben wird, Option B nachrüsten.

### Alternative 3 · Polling ohne Cache

Jeder `get()`-Aufruf liest direkt aus der DB.

```typescript
async get(key: string): Promise<string> {
  return (await db.queryOne('SELECT value FROM config_params WHERE key=$1', [key])).value
}
```

**Abgelehnt**: Der `ConfidenceEvaluator` ruft `getThresholds()` bei jeder Nutzeranfrage auf. Bei 20 concurrent users und mehrfachen Aufrufen pro Anfrage würden 60–100 DB-Queries pro Sekunde allein für Config-Reads entstehen. Option A löst das ohne spürbare Mehrkosten.

---

## Konsequenzen

### Positiv
- Keine neue Infrastrukturkomponente: Config lebt in der bereits vorhandenen PostgreSQL-Instanz
- Audit-Log transaktionssicher: Config-Änderung und Log-Eintrag gelingen oder scheitern gemeinsam — kein inkonsistenter Zustand möglich
- `InMemoryConfigService` macht alle Komponenten, die Config lesen, ohne DB testbar
- Schwellenwerte sind niemals Magic Numbers im Code — zentralisiert, versioniert, auditierbar
- Lesezugriff pro Anfrage: 0 DB-Queries (Cache-Hit) oder 1 DB-Query (Cache-Miss nach Invalidierung)

### Negativ / Risiken
- Bei zukünftigem Multi-Instance-Betrieb: bis zu 30 Sekunden Inkonsistenz zwischen Instanzen nach einer Änderung (akzeptabel für MVP, muss bei Scale-Up adressiert werden)
- `TTL_MS = 30_000` ist eine Konstante — sollte sie selbst konfigurierbar sein? Bewusst ausgelassen: Meta-Konfiguration erhöht Komplexität ohne MVP-Nutzen
- DB-Ausfall macht Config-Reads unmöglich: fallback auf gecachte Werte (bis TTL abläuft) ist vorhanden, aber kein expliziter Kaltstart-Fallback definiert

---

## Abhängigkeiten

| Abhängigkeit | Typ | Hinweis |
|---|---|---|
| ADR-001 (ConfidenceEvaluator) | Konsument | Liest `getThresholds()` bei jeder Anfrage |
| ADR-002 (RAG-Pipeline) | Indirekt | Über ADR-001 |
| US-11 Admin-Seite | Schreibweg | Admin-UI ruft `ConfigService.set()` auf |
| QA-03 Security | Voraussetzung | Admin-Seite nur für Admin-Rolle erreichbar (→ separates ADR für Auth empfohlen) |
| PostgreSQL | Infrastruktur | Kein zusätzliches System erforderlich |

---

## Offen / Nächste Schritte

- [ ] Initiale Schwellenwerte für `min_confidence_score` und `suppress_threshold` nach RAG-Spike festlegen und in Seed-Migration eintragen
- [ ] DB-Migrationsscript für `config_params` und `config_audit_log` erstellen (Teil von Sprint 0)
- [ ] Entscheiden: Admin-UI (US-11) zeigt Audit-Log als read-only Tabelle an — Scope für MVP?
- [ ] Kaltstart-Verhalten bei leerem Cache und DB-Ausfall definieren (Default-Werte im Code als letzter Fallback?)
- [ ] `TTL_MS` als Deployment-Konstante dokumentieren (nicht konfigurierbar, aber bekannt)
