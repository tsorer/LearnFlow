# ADR-006 · Authentifizierungs-Strategie: JWT mit HTTP-only Cookie und SSO-Ready-Middleware

| | |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Autor** | LearnFlow Architecture Team |
| **Bezug** | US-05, QA-03 (Security), QA-05 (Maintainability) |
| **Abhängigkeit** | ADR-007 (Frontend-Framework) |

---

## Kontext

US-05 definiert die Authentifizierungsanforderungen für das MVP:

- Username/Passwort (lokal), Accounts per DB-Script
- Keine Self-Service-Registrierung
- Drei Rollen: `Lernende` / `Bereichsverantwortlicher` / `Admin`
- Nicht authentifizierte Requests → Redirect auf Login-Seite
- **Post-MVP**: SSO via Unternehmens-IdP (Azure AD / SAML 2.0 oder OIDC)

Die Post-MVP-SSO-Anforderung ist der entscheidende Architektur-Treiber: die Auth-Strategie muss heute so gebaut werden, dass der Wechsel zu SSO kein Refactoring der Business-Logik, der RBAC-Middleware oder der geschützten Endpunkte erfordert.

QA-03 (Security) stellt zudem folgende Anforderungen:
- Passwörter: Argon2id oder Bcrypt (kein MD5, kein SHA1, kein Plaintext)
- Session-Token: HTTP-only Cookie (XSS-Schutz) oder kurzlebiges JWT + Refresh-Token
- RBAC server-seitig erzwungen — kein Trust in Client-Claims
- Admin-Seite ohne Admin-Rolle → HTTP 403

---

## Entscheidung

**JWT-basierte Authentifizierung** mit kurzlebigem Access-Token (15 min) und langlebigem Refresh-Token (7 Tage), beide als **HTTP-only Cookies** übertragen.

Die gesamte Auth-Logik lebt in einer **`AuthMiddleware`-Schicht**, die hinter einem Interface definiert ist. RBAC ist in einer separaten **`RBACMiddleware`** gekapselt. Für den Post-MVP-SSO-Wechsel wird nur `AuthMiddleware` ersetzt — alle anderen Schichten bleiben unverändert.

### Token-Strategie

| Token | Typ | Lebensdauer | Transport | Inhalt |
|---|---|---|---|---|
| Access-Token | JWT (HS256) | 15 Minuten | HTTP-only Cookie | `userId`, `role`, `areaId`, `exp` |
| Refresh-Token | Opaque (UUID) | 7 Tage | HTTP-only Cookie | — (in DB gespeichert) |

**Warum kein reines Session-Cookie (server-side session)?**
JWT-Access-Tokens sind zustandslos und skalieren ohne Session-Store. Das Refresh-Token (in DB) erlaubt Server-seitige Invalidierung (Logout, Passwortänderung).

```typescript
// Access-Token-Payload (minimal — kein User-PII)
type AccessTokenPayload = {
  sub:    string   // userId (UUID)
  role:   Role     // 'learner' | 'area_manager' | 'admin'
  areaId: string   // zugewiesener Bereich
  exp:    number   // Unix Timestamp (now + 15 min)
}

type Role = 'learner' | 'area_manager' | 'admin'
```

### Request-Flow

```
Request
    │
    ▼
┌──────────────────────────────────────────────────────┐
│ AuthMiddleware                                       │
│                                                      │
│  MVP-Implementierung:                                │
│    1. Access-Token aus HTTP-only Cookie lesen        │
│    2. JWT-Signatur verifizieren (HS256 + Secret)     │
│    3. Ablaufzeit prüfen                              │
│    4. Wenn abgelaufen: Refresh-Token prüfen          │
│       → neues Access-Token ausstellen                │
│    5. request.user = { id, role, areaId } setzen     │
│                                                      │
│  Post-MVP SSO-Implementierung (OIDC/SAML):           │
│    1. OIDC-Token oder SAML-Assertion validieren      │
│    2. Claims auf { id, role, areaId } mappen         │
│    3. request.user setzen — identische Schnittstelle │
│                                                      │
│  Beide Implementierungen implementieren AuthMiddleware│
│  Interface → kein Code unterhalb ändert sich        │
└──────────────┬───────────────────────────────────────┘
               │ request.user gesetzt
               ▼
┌──────────────────────────────────────────────────────┐
│ RBACMiddleware (unverändert bei SSO-Wechsel)         │
│                                                      │
│  Liest: request.user.role                            │
│  Prüft: route.requiredRoles.includes(request.user.role)
│  → 403 Forbidden wenn nicht berechtigt              │
│  → kein Weiterleiten, kein Redirect bei API-Calls    │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
        Business Handler
```

### AuthMiddleware-Interface

```typescript
interface AuthMiddleware {
  /** Validiert den Request und befüllt request.user.
   *  Wirft AuthError wenn nicht authentifiziert. */
  authenticate(req: Request, res: Response, next: NextFunction): Promise<void>
}

// MVP: lokale JWT-Validierung
class LocalJWTAuthMiddleware implements AuthMiddleware { ... }

// Post-MVP: OIDC via Azure AD
class OIDCAuthMiddleware implements AuthMiddleware { ... }

// Tests: gibt immer einen fixen User zurück
class MockAuthMiddleware implements AuthMiddleware {
  constructor(private user: AuthUser) {}
  async authenticate(req, res, next) {
    (req as any).user = this.user
    next()
  }
}
```

### RBAC-Deklaration pro Route

```typescript
// Rollendeklaration an der Route — kein RBAC-Code in Handlern
router.post('/api/documents/upload',
  rbac(['area_manager', 'admin']),
  uploadHandler
)

router.get('/api/admin/config',
  rbac(['admin']),
  configHandler
)

router.post('/api/questions',
  rbac(['learner', 'area_manager', 'admin']),
  questionHandler
)

// rbac() gibt eine Middleware zurück, die request.user.role prüft
function rbac(allowedRoles: Role[]): RequestHandler {
  return (req, res, next) => {
    if (!allowedRoles.includes((req as any).user?.role))
      return res.status(403).json({ error: 'Forbidden' })
    next()
  }
}
```

### Passwort-Hashing

```typescript
// Argon2id — moderner Standard, resistent gegen GPU-Angriffe
import argon2 from 'argon2'

const ARGON2_OPTIONS = {
  type:        argon2.argon2id,
  memoryCost:  65536,   // 64 MB
  timeCost:    3,       // Iterationen
  parallelism: 4
}

async function hashPassword(plain: string): Promise<string> {
  return argon2.hash(plain, ARGON2_OPTIONS)
}

async function verifyPassword(hash: string, plain: string): Promise<boolean> {
  return argon2.verify(hash, plain)
}
```

### Datenbankschema

```sql
-- Nutzer (via DB-Script angelegt, keine Self-Service-Registrierung)
CREATE TABLE users (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  username    TEXT        NOT NULL UNIQUE,
  password_hash TEXT      NOT NULL,     -- Argon2id-Hash
  role        TEXT        NOT NULL CHECK (role IN ('learner','area_manager','admin')),
  area_id     TEXT        NOT NULL,     -- Pilot: hartcodiert, Post-MVP: FK
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  is_active   BOOLEAN     NOT NULL DEFAULT true
);

-- Refresh-Tokens (ermöglicht Server-seitige Invalidierung)
CREATE TABLE refresh_tokens (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash  TEXT        NOT NULL UNIQUE,   -- SHA-256 des Tokens
  expires_at  TIMESTAMPTZ NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at  TIMESTAMPTZ                    -- NULL = aktiv
);

CREATE INDEX ON refresh_tokens (user_id);
CREATE INDEX ON refresh_tokens (expires_at) WHERE revoked_at IS NULL;
```

### Login- und Logout-Flow

```
Login:
  POST /api/auth/login { username, password }
    → Passwort mit Argon2id verifizieren
    → Access-Token (JWT, 15 min) generieren
    → Refresh-Token (UUID) generieren, SHA-256 in DB speichern
    → Beide als HTTP-only Cookies setzen (Secure, SameSite=Strict)
    → 200 { role, areaId }   ← kein Token im Body

Token-Refresh (automatisch):
  POST /api/auth/refresh
    → Refresh-Token aus Cookie lesen
    → SHA-256 in DB suchen, Ablaufzeit + revoked_at prüfen
    → Neues Access-Token ausstellen
    → Altes Refresh-Token revoken, neues ausstellen (Token-Rotation)

Logout:
  POST /api/auth/logout
    → Refresh-Token in DB als revoked markieren
    → Beide Cookies löschen (Max-Age=0)
```

---

## Begründung

**Warum JWT + HTTP-only Cookie statt Server-Side Session?**

Server-Side Sessions (z.B. express-session + PostgreSQL-Store) sind zustandsbehaftet. Jeder Request benötigt einen DB-Lookup für die Session-Validierung. JWT-Access-Tokens sind zustandslos — Validierung ohne DB in < 1 ms. Der Refresh-Token-Mechanismus in der DB ermöglicht trotzdem Server-seitige Invalidierung bei Logout oder Sicherheitsvorfällen.

**Warum HTTP-only Cookie statt Authorization-Header (Bearer Token)?**

`Authorization: Bearer` im Header erfordert, dass JavaScript den Token liest und ihn bei jedem Request mitsetzt. HTTP-only Cookies sind für JavaScript nicht lesbar — XSS-Angriffe können den Token nicht stehlen. Der Nachteil (kein manueller API-Aufruf von ausserhalb des Browsers) ist für ein internes Tool irrelevant.

**Warum Argon2id statt Bcrypt?**

Argon2id ist der aktuelle OWASP-Standard (2024) und resist gegen GPU-basierte Brute-Force-Angriffe. Bcrypt ist bewährt und akzeptabel, aber Argon2id bietet Memory-Hardness als zusätzlichen Schutz. Kosten: eine npm-Library (`argon2`).

**Warum Refresh-Token-Rotation?**

Bei Rotation wird nach jedem Refresh der alte Token in der DB invalidiert und ein neuer ausgestellt. Das bedeutet: ein gestohlener Refresh-Token wird beim nächsten legitimen Refresh erkannt (Collision → beide Sessions invalidieren). Minimaler Mehraufwand, signifikante Sicherheitsverbesserung.

**Warum AuthMiddleware als Interface?**

Die Post-MVP-SSO-Anforderung (US-05) ist kein Nice-to-Have. Wenn SSO ohne Interface nachgerüstet wird, zieht sich die SAML/OIDC-Logik durch alle geschützten Endpunkte. Das Interface kapselt die Auth-Logik an genau einem Ort. Kosten: ein Interface, zwei Implementierungen.

---

## Betrachtete Alternativen

### Alternative 1 · Auth.js (NextAuth.js)

Auth.js ist eine umfassende Auth-Library für Next.js mit eingebautem Support für OAuth, OIDC, Credentials-Provider und SAML (via Adapter).

**Zurückgestellt**: Auth.js macht Sinn wenn ADR-007 Next.js wählt. Die SSO-Readiness ist dann durch die Library abgedeckt, nicht durch eigenes Interface-Design. Wenn Next.js gewählt wird (→ ADR-007), sollte Auth.js als Alternative zu dieser ADR erneut evaluiert werden.

**Trade-off**: Weniger Kontrolle über Token-Format und Cookie-Konfiguration, dafür weniger selbst zu implementieren. Empfehlung: Auth.js bevorzugen wenn Next.js als Framework gewählt wird.

### Alternative 2 · Reine Session-Cookies (express-session)

```typescript
app.use(session({ store: new PgSession({ pool }), secret, resave: false }))
```

**Abgelehnt**: DB-Lookup bei jedem Request (Session-Validierung). Horizontal schwerer skalierbar (alle Instanzen brauchen denselben Session-Store). SSO-Readiness erfordert dasselbe Interface-Konzept wie JWT.

### Alternative 3 · Keycloak (Self-Hosted Identity Provider)

Keycloak ist ein vollständiger OIDC/SAML IdP — würde sowohl MVP-Auth als auch Post-MVP-SSO abdecken.

**Abgelehnt**: Separater Server, erheblicher Setup- und Betriebsaufwand für ein 480h-MVP-Budget. Keycloak ist sinnvoll wenn das Unternehmen bereits einen zentralen IdP betreibt — dann entfällt die MVP-Phase und SSO ist sofort verfügbar.

---

## Konsequenzen

### Positiv
- SSO-Wechsel (Post-MVP) erfordert ausschliesslich eine neue `AuthMiddleware`-Implementierung — keine Änderung an Handlern, RBAC, Business-Logik
- `MockAuthMiddleware` macht alle geschützten Endpunkte testbar ohne Login-Flow
- HTTP-only Cookies verhindern XSS-Token-Diebstahl
- Argon2id bietet state-of-the-art Passwortschutz
- Token-Rotation erkennt gestohlene Refresh-Tokens

### Negativ / Risiken
- JWT-Invalidierung vor Ablauf (15 min) nicht möglich ohne DB-Lookup (z.B. bei Passwortänderung). Mitigation: Refresh-Token revoken → nächste Token-Rotation schlägt fehl
- `HS256` (symmetrisches Signing) erfordert, dass JWT-Secret sicher verwaltet wird (Secrets Manager, nie in Code). Bei Multi-Instance wäre `RS256` (asymmetrisch) besser — für MVP-Single-Instance akzeptabel
- Argon2id-Hashing dauert ~100–300 ms (bewusst, als Brute-Force-Schutz). Login-Latenz entsprechend höher als ohne Hashing — für UX akzeptabel, da Login selten

---

## Abhängigkeiten

| Abhängigkeit | Typ | Hinweis |
|---|---|---|
| ADR-007 (Frontend-Framework) | Koordiniert | Wenn Next.js → Auth.js als Alternative evaluieren (Alternative 1) |
| US-05 (Authentifizierung) | Direkt | Alle ACs von US-05 werden durch diese Entscheidung abgedeckt |
| QA-03 Security (M8, M9) | Validierung | RBAC server-side (M8) und Pseudonymisierung Feedback (M9) setzen diese Auth-Schicht voraus |
| ADR-003 (ConfigService) | Optional | JWT-Secret und Token-Lebensdauer als Config-Parameter möglich |

---

## Offen / Nächste Schritte

- [ ] ADR-007 (Frontend-Framework) abschliessen: wenn Next.js → Auth.js-Alternative evaluieren
- [ ] JWT-Secret-Management definieren: Umgebungsvariable, Vault oder Docker Secret?
- [ ] DB-Script für erste Admin- und Test-Accounts schreiben (Argon2id-Hashes)
- [ ] Cookie-Konfiguration für Entwicklungsumgebung (HTTPS nicht immer verfügbar): `Secure`-Flag nur in Produktion, `SameSite=Lax` für lokale Entwicklung
- [ ] SSO-Provider-Typ (Azure AD SAML 2.0 vs. OIDC) für Post-MVP-Planung klären — beeinflusst welche Adapter-Implementierung vorzubereiten ist
