# ADR-001: Architekturstil — Modularer Monolith

| Feld          | Inhalt                                                   |
| ------------- | -------------------------------------------------------- |
| **Status**    | Accepted                                                 |
| **Datum**     | 2026-05-27 · aktualisiert 2026-06-03                     |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto, Christoph) |

---

## Kontext

LearnFlow ist ein interner Pilot für einen einzigen Bereich mit maximal 30 gleichzeitigen Nutzern und einem Umsetzungsbudget von 360 Personenstunden (von 480 h gesamt; ~120 h für Planung/Analyse/Architektur). Microservices erfordern Service Discovery, Netzwerk-Mesh und separate Deployment-Pipelines pro Service — ein Overhead, der bei diesem Budget und dieser Nutzerzahl nicht zu rechtfertigen ist. Die Maintainability-NFA verlangt klare Modul-Grenzen (Konfiguration ohne Code-Deployment, austauschbare RAG-Komponenten), ohne dass dafür ein verteiltes System nötig wäre.

---

## Entscheidung

Wir bauen LearnFlow als **modularen Monolithen**: alle Module (RAG-Pipeline, Auth, Dokument-Management, Feedback, Admin) laufen in einem einzigen Deployment-Artefakt. Modul-Grenzen werden durch explizite Service-Interfaces durchgesetzt — kein direkter Datenbank-Aufruf über Modul-Grenzen hinweg, kein shared State. Das Design ist von Anfang an stateless, um einen späteren Ausbau zu ermöglichen.

---

## Konsequenzen

### Positive Konsequenzen

- **+** Ein Deployment-Artefakt: kein Netzwerk-Overhead zwischen Modulen, einfacheres lokales Debugging für alle vier Personen.
- **+** Kein Ops-Overhead durch Service Discovery, Load Balancer oder verteiltes Tracing — eingesparte Zeit fliesst in RAG-Qualität.
- **+** Stateless-Design + klare Service-Interfaces halten die Tür für einen späteren Ausbau offen, ohne dass heute Microservice-Infrastruktur gebaut werden muss.
- **+** Einfacheres Onboarding: neue Teammitglieder starten mit einem einzigen `docker compose up`.

### Negative Konsequenzen

- **−** Single Deployment-Unit: ein Crash oder Fehler kann alle Module betreffen. Bewusst akzeptiert für den Business-Hours-Pilot mit < 30 Nutzern.
- **−** Disziplin erforderlich: ohne explizit durchgesetzte Modul-Grenzen entsteht über Zeit ein klassischer Big-Ball-of-Mud-Monolith. Mitigation: Code-Review checkt auf direkte DB-Calls über Modul-Grenzen.
- **−** Horizontales Scaling des Monolithen bedeutet das Skalieren aller Module — auch jener, die keinen Engpass haben. Für den Pilot irrelevant; bei Post-MVP-Wachstum zu überdenken.

---

## Abgewogene Alternativen

| Alternative                                   | Warum verworfen                                                                                                                                                           |
| --------------------------------------------- | ----------------------------------------------------------------------------