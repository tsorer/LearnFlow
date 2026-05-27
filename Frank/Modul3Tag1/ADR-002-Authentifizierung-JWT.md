# ADR-002: JWT + bcrypt als Authentifizierungsmechanismus, Auth-Layer SSO-vorbereitet

| | |
|---|---|
| **Status** | Accepted |
| **Datum** | 2026-05-27 |
| **Projekt** | LearnFlow — interne RAG-basierte Lernplattform |

---

## Context

LearnFlow enthält interne Unternehmensdokumente und Fachprozesse — kein Zugriff darf ohne Authentifizierung und rollenbasierte Autorisierung möglich sein. Im MVP werden Accounts per DB-Script angelegt; kein Self-Service-Registrierungsflow ist vorgesehen. Drei Rollen sind definiert: Lernende, Bereichsverantwortliche, Admins.

Post-MVP ist Azure AD / SAML SSO explizit geplant. Die Auth-Basis muss so gebaut sein, dass diese Migration ausschliesslich den Auth-Layer betrifft — kein Downstream-Code darf geändert werden müssen. Gleichwohl ist SAML/Azure AD technisch fundamental anders als Username/Passwort + JWT (anderer Auth-Flow, andere Token-Formate, andere Session-Logik): die "SSO-Vorbereitung" bedeutet eine klare Modulgrenze, nicht eine triviale Migration.

DSGVO verlangt, dass personenbezogene Daten die EU nicht verlassen. Die Auth-Lösung muss self-hosted oder nachweislich EU-konform betrieben werden können.

**Voraussetzung:** Sämtliche Kommunikation läuft ausschliesslich über HTTPS/TLS. JWT-Token über unverschlüsseltes HTTP übertragen würde die gesamte Auth-Architektur kompromittieren. TLS ist nicht optional.

## Decision

Wir verwenden **JWT (JSON Web Tokens) mit 4 Stunden Gültigkeit** für die Session-Verwaltung und **Argon2id** für das Passwort-Hashing. Accounts werden ausschliesslich per DB-Script angelegt — kein öffentlicher Registrierungsendpunkt wird implementiert.

**JWT-Gültigkeit 4h statt 8h:** Ein Arbeitstag endet meist nach 8 Stunden — ein kompromittierter Token soll jedoch nicht den vollen Tag gültig bleiben. 4 Stunden ist der Kompromiss zwischen Nutzungskomfort (selteneres Re-Login) und Missbrauchsfenster.

**Argon2id statt bcrypt:** Argon2id ist seit 2022 der OWASP-Standard für Passwort-Hashing (memory-hard, resistent gegen GPU-Angriffe). bcrypt ist bewährt, aber für neue Implementierungen nicht mehr die empfohlene Wahl.

**JWT-Payload:** Enthält ausschliesslich `user_id` und `role`. Kein Name, keine E-Mail, keine weiteren personenbezogenen Daten. Tokens werden als **HttpOnly Cookie** gesetzt — nicht in `localStorage` — um XSS-Angriffe zu mitigieren.

**Rolle im JWT und Revocation:** Da JWTs stateless sind, wirkt ein Rollen-Entzug erst nach Token-Ablauf (bis zu 4 h). Für den MVP ist das akzeptiert — bei sicherheitskritischen Rollen-Änderungen (z. B. Admin-Entzug) muss der betroffene User explizit über die Admin-UI ausgeloggt werden, was einen Token-Blacklist-Eintrag in der Datenbank erzeugt. Diese Liste wird nur für explizite Entzüge genutzt, nicht für reguläre Abläufe.

**JWT Secret Management:** Das Secret wird als Umgebungsvariable injiziert — niemals in der Codebase oder im Repository. Im MVP: Docker-Secret oder `.env` ausserhalb des Repos. Das Secret wird rotiert wenn ein Verdacht auf Kompromittierung besteht; bei Rotation werden alle aktiven Sessions beendet (bewusster Trade-off).

Der Auth-Layer wird als **eigenständiges, gekapseltes Modul** implementiert. Die restliche Applikation (RAG-Pipeline, Admin-UI, Quiz) kennt nur das Interface des Auth-Moduls. Die SSO-Migration Post-MVP ist ein Umbau innerhalb dieses Moduls — der Downstream-Code bleibt unverändert, aber der Aufwand der Migration (SAML-Flow, Token-Format-Konvertierung) ist nicht trivial und muss als eigenes Projekt geplant werden.

**Rollenprüfung** erfolgt serverseitig bei jedem Request auf API-Ebene — nicht nur in der UI.

## Consequences

**Positiv**

- Stateless: kein shared Session-State — Skalierung unproblematisch
- Argon2id schützt Passwörter auch bei DB-Leak (memory-hard, resistent gegen GPU-Angriffe)
- HttpOnly Cookie schützt vor XSS-basiertem Token-Diebstahl
- Minimaler Token-Blacklist nur für explizite Admin-Entzüge: sofortiger Rollen-Entzug im Notfall möglich
- SSO-Migration Post-MVP auf Auth-Modul beschränkt — kein Downstream-Code betroffen
- Kein US-Cloud-Abhängigkeit: vollständig self-hosted, DSGVO-konform
- Kein Self-Service = kein Wildwuchs: nur freigegebene Accounts können sich einloggen

**Negativ**

- Reguläre Token-Revocation bleibt schwierig: ohne expliziten Admin-Entzug gilt der Token bis zum Ablauf (max. 4 h)
- Kein Refresh-Token-Mechanismus: Nutzerinnen melden sich alle 4 Stunden erneut an — bewusster Trade-off gegen Komplexität
- Account-Verwaltung per DB-Script ist manuell: kein delegierter Self-Service
- SSO-Migration Post-MVP ist kein trivialer Umbau: SAML/Azure AD erfordert anderen Auth-Flow und Token-Format — der Auth-Layer begrenzt die Auswirkungen, eliminiert den Aufwand nicht
- Secret-Rotation beendet alle aktiven Sessions — muss im Wartungsfenster durchgeführt werden
