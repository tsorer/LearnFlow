# ADR-007 · Frontend-Framework: Next.js mit TypeScript und App Router

| | |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Autor** | LearnFlow Architecture Team |
| **Bezug** | US-01, US-03, US-07, US-08, US-09, US-11, QA-05 (Maintainability) |
| **Abhängigkeit** | ADR-002 (Discriminated Union / TypeScript), ADR-006 (Auth-Strategie) |

---

## Kontext

LearnFlow benötigt vier funktional unterschiedliche UI-Bereiche:

| Bereich | Hauptfunktionen | Besonderheiten |
|---|---|---|
| **Chat-Interface** (Lara) | Frage stellen, Antwort mit Quellenlinks lesen, Feedback geben, Folgefragen | LLM-Streaming, progressive Darstellung, Session-Verlauf |
| **Lern-Interface** (Lara) | Quiz absolvieren, Ergebnis einsehen | — |
| **Bereichsverantwortlicher-Dashboard** (Stefan) | Dokumente hochladen/verwalten, Quiz-Fragen freigeben, Wissenslücken-Cluster | Datei-Upload, Status-Polling, Review-Workflow |
| **Admin-Seite** (Admin) | Schwellenwerte anpassen, Audit-Log einsehen | Formular-getrieben, wenig Traffic |

Aus ADR-002 ergibt sich eine technische Vorentscheidung: der **Discriminated-Union-Ansatz** für die RAG-Pipeline-Ergebnisse ist nativ und vollständig typsicher nur in **TypeScript** umsetzbar. Das Frontend-Framework muss TypeScript unterstützen.

Aus ADR-006 ergibt sich die Post-MVP-SSO-Anforderung (OIDC/SAML 2.0): das Framework sollte entweder eine bewährte Auth-Integration haben oder das AuthMiddleware-Interface aus ADR-006 einfach einbinden lassen.

**Scope: Desktop-Browser, kein Mobile, kein Responsive-CSS als MVP-Anforderung.**

---

## Entscheidung

**Next.js 15 (App Router) mit TypeScript** als Full-Stack-Framework.

Next.js übernimmt sowohl das Frontend (React-Komponenten) als auch das Backend (API-Routes, Server Actions) — kein separater API-Server für das MVP nötig. Das vereinfacht Deployment, eliminiert CORS-Konfiguration und reduziert den Infrastruktur-Footprint für ein 480h-Budget.

### Architektur-Übersicht

```
Browser
    │  HTTPS
    ▼
┌──────────────────────────────────────────────────────────────┐
│  Next.js (App Router)                                        │
│                                                              │
│  app/                                                        │
│    (auth)/login/         → Login-Seite (public)              │
│    (learner)/chat/       → Chat-Interface (Lara)             │
│    (learner)/quiz/       → Quiz (Lara)                       │
│    (manager)/documents/  → Dokument-Verwaltung (Stefan)      │
│    (manager)/quiz-review/→ Quiz-Freigabe (Stefan)            │
│    (manager)/gaps/       → Wissenslücken (Stefan)            │
│    (admin)/config/       → Admin-Konfiguration               │
│                                                              │
│  app/api/                → API-Routes (Server-Side)          │
│    auth/login/           → POST: Login, Token setzen         │
│    auth/refresh/         → POST: Token-Rotation              │
│    auth/logout/          → POST: Token revoken               │
│    questions/            → POST: RAG-Pipeline aufrufen       │
│    documents/            → GET/POST/DELETE: Corpus-Verwaltung│
│    quiz/                 → GET/POST: Quiz-Logik              │
│    admin/config/         → GET/POST: Konfiguration           │
└───────────────────────────────┬──────────────────────────────┘
                                │ (interner Aufruf)
                                ▼
                    Python Backend-Services
                    (RAG-Engine, Embedding,
                     Chunking, pgvector)
```

> **Hinweis zur Backend-Aufteilung:** Die RAG-Engine, der Embedding-Adapter (ADR-005) und der Vektor-DB-Zugriff werden in einem separaten **Python-Backend-Service** implementiert (besseres ML-Ökosystem: `sentence-transformers`, `pdfplumber`, `python-docx`). Next.js API-Routes kommunizieren via HTTP mit diesem Service. Das ist die einzige Service-Grenze im MVP.

### Warum TypeScript obligatorisch ist

ADR-002 definiert `RAGResult` als Discriminated Union. TypeScript erzwingt den Exhaustiveness-Check im `switch`-Statement — vergessene Varianten werden Build-Fehler, keine Runtime-Fehler:

```typescript
// Compiler-Fehler wenn eine RAGResult-Variante nicht behandelt wird
function renderResult(result: RAGResult): React.ReactNode {
  switch (result.kind) {
    case 'answer':      return <AnswerCard ... />
    case 'dont_know':   return <DontKnowCard hint={result.hint} />
    case 'no_source':   return <NoSourceCard />
    case 'suppressed':  return <NoSourceCard />
    case 'unavailable': return <ErrorCard message={result.message} />
    case 'timeout':     return <ErrorCard message="Zeitüberschreitung." />
    // Kein default nötig — TypeScript erkennt: alle Varianten behandelt
  }
}
```

### LLM-Streaming im Chat-Interface

US-09 (Folgefragen) und die p95-Anforderung (≤ 10 s, QA-01) profitieren stark von streaming Darstellung. Next.js App Router und React 18 bieten native Streaming-Unterstützung:

```typescript
// app/api/questions/route.ts
export async function POST(req: Request) {
  const { question, history } = await req.json()

  const stream = new ReadableStream({
    async start(controller) {
      const ragResult = await runRAGPipeline(question, history)

      if (ragResult.kind !== 'answer') {
        // Nicht-Antwort-Varianten: sofort als JSON senden
        controller.enqueue(JSON.stringify(ragResult))
        controller.close()
        return
      }

      // Antwort: chunk-weise streamen
      for await (const chunk of llmAdapter.stream(ragResult.prompt)) {
        controller.enqueue(chunk)
      }
      controller.close()
    }
  })

  return new Response(stream, {
    headers: { 'Content-Type': 'text/event-stream' }
  })
}
```

```typescript
// Komponente: progressive Darstellung der Antwort
function ChatMessage({ questionId }: { questionId: string }) {
  const [content, setContent] = useState('')
  const [result, setResult] = useState<RAGResult | null>(null)

  useEffect(() => {
    const reader = fetchAnswer(questionId).getReader()
    // ReadableStream chunk-weise lesen → setContent aktualisieren
    // Letzte Nachricht: vollständiges RAGResult-Objekt (Quellen, Konfidenz)
  }, [questionId])

  if (!result) return <StreamingText content={content} />
  return renderResult(result)
}
```

### Auth.js als MVP-Auth-Integration (wenn ADR-006 Next.js-Pfad)

Falls ADR-006 die Auth.js-Empfehlung übernimmt (Alternative 1 in ADR-006), bietet Next.js native Integration:

```typescript
// auth.ts
import NextAuth from 'next-auth'
import Credentials from 'next-auth/providers/credentials'

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      async authorize({ username, password }) {
        // Argon2id-Verifikation gegen DB
        const user = await verifyUser(username as string, password as string)
        return user ?? null
      }
    })
  ],
  // Post-MVP: SAML/OIDC-Provider hier ergänzen — kein Code ausserhalb ändert sich
  callbacks: {
    jwt({ token, user }) {
      if (user) { token.role = user.role; token.areaId = user.areaId }
      return token
    },
    session({ session, token }) {
      session.user.role   = token.role as Role
      session.user.areaId = token.areaId as string
      return session
    }
  }
})
```

```typescript
// Middleware: schützt alle Routen ausser /login
// middleware.ts (Next.js Middleware, läuft auf Edge)
export { auth as middleware } from './auth'
export const config = { matcher: ['/((?!login|_next|api/auth).*)'] }
```

### Verzeichnisstruktur

```
learnflow/
├── app/
│   ├── (auth)/
│   │   └── login/
│   │       └── page.tsx
│   ├── (learner)/
│   │   ├── chat/
│   │   │   └── page.tsx
│   │   └── quiz/
│   │       └── page.tsx
│   ├── (manager)/
│   │   ├── documents/
│   │   ├── quiz-review/
│   │   └── gaps/
│   ├── (admin)/
│   │   └── config/
│   └── api/
│       ├── auth/
│       ├── questions/
│       ├── documents/
│       ├── quiz/
│       └── admin/
├── components/
│   ├── chat/
│   │   ├── AnswerCard.tsx
│   │   ├── LimitedAnswerCard.tsx
│   │   ├── DontKnowCard.tsx
│   │   ├── NoSourceCard.tsx
│   │   └── ErrorCard.tsx
│   └── shared/
├── lib/
│   ├── rag/              ← RAGResult-Typen, Pipeline-Client
│   ├── auth/             ← AuthMiddleware-Interface + Implementierung
│   └── config/           ← ConfigService-Client
├── types/
│   └── rag.ts            ← RAGResult Discriminated Union (aus ADR-002)
└── middleware.ts          ← Auth-Schutz aller Routen
```

---

## Begründung

**Warum Next.js und nicht React SPA + separater Express-Server?**

Ein React SPA mit separatem API-Server wäre zwei zu deplogende und wartende Services. Für ein 1-FTE-Team mit 480h-Budget ist die Vereinfachung durch Next.js (ein Deployment, ein Dev-Server, kein CORS) erheblich. API-Routes in Next.js sind vollwertige Node.js-Handler — kein Funktionalitätsverlust.

**Warum App Router und nicht Pages Router?**

App Router (Next.js 13+) bietet native Streaming-Unterstützung via React 18 Suspense und `ReadableStream`. Das ist für die LLM-Streaming-Anforderung (US-01 p95, US-09) der entscheidende Vorteil. Pages Router würde manuelle Server-Sent-Events-Implementierung erfordern.

**Warum kein SvelteKit?**

SvelteKit ist schneller, leichtgewichtiger und hat ausgezeichnetes DX. Der Hauptgrund gegen SvelteKit: Svelte ist kein TypeScript-First-Framework in dem Sinn, dass die Discriminated-Union-Exhaustiveness-Prüfung in `switch`-Statements (ADR-002) in Svelte-Templates nicht erzwungen wird. TypeScript-Sicherheit ist hier keine optionale Verbesserung, sondern eine Kernanforderung.

**Warum kein Remix?**

Remix ist ein valider Konkurrent zu Next.js. Die Entscheidung zugunsten von Next.js basiert auf: grösserem Ökosystem, besserer Auth.js-Integration und grösserer Team-Verbreitung. Technisch wäre Remix gleichwertig.

**Warum Python für Backend-Services und nicht rein Node.js?**

Das ML-Ökosystem für Embedding (`sentence-transformers`), PDF-Parsing (`pdfplumber`, `pymupdf`) und zukünftige Scoring-Modelle ist in Python deutlich reifer als in Node.js. Eine einzelne Service-Grenze (Next.js → Python-Backend) hält diese Stärke nutzbar ohne die Frontend-Entwicklung auf Python zu zwingen.

---

## Betrachtete Alternativen

### Alternative 1 · SvelteKit + TypeScript

Leichtgewichtiger, schnellere Compile-Zeiten, weniger JavaScript im Browser.

**Abgelehnt**: Exhaustiveness-Check für Discriminated Unions in Svelte-Templates nicht erzwingbar. TypeScript-Integration schwächer als in Next.js. Kleineres Ökosystem für Auth (Post-MVP SSO).

### Alternative 2 · React SPA (Vite) + Express.js API

Klare Trennung Frontend / Backend. Bekanntes Setup.

**Abgelehnt**: Zwei separate Services zu deployen und zu betreiben. CORS-Konfiguration. Kein natives Streaming ohne SSE-Implementierung. Kein Mehrwert gegenüber Next.js bei gleichem Aufwand.

### Alternative 3 · Vue 3 + Nuxt

Ähnliche Eigenschaften wie Next.js, etwas kleiner im Ökosystem.

**Abgelehnt**: Kein technischer Vorteil gegenüber Next.js für diesen Use-Case. Geringere Verbreitung im Team typischerweise. Auth.js unterstützt Nuxt schlechter als Next.js.

---

## Konsequenzen

### Positiv
- Ein einziges Deployment für Frontend und BFF-API — minimaler Betriebsaufwand
- TypeScript end-to-end: Discriminated Unions aus ADR-002 sind im Frontend voll typsicher
- Natives Streaming für LLM-Antworten (App Router + React 18)
- Auth.js bietet direkte Post-MVP SSO-Erweiterung ohne Refactoring
- Route-Groups (z.B. `(admin)`) isolieren RBAC-Anforderungen pro Bereich

### Negativ / Risiken
- Next.js App Router ist jünger als Pages Router — mehr API-Instabilität, mehr Community-Fragen zu edge cases
- Python-Backend als zweiter Service: eine Service-Grenze mehr als bei einer rein Node.js-Lösung. Mitigation: klares Interface, lokale Entwicklung mit Docker Compose
- Server Components vs. Client Components Unterscheidung: erhöhter Erklärungsaufwand beim Onboarding; Streaming-Logik mit `ReadableStream` ist nicht trivial

---

## Abhängigkeiten

| Abhängigkeit | Typ | Hinweis |
|---|---|---|
| ADR-002 (Discriminated Union) | Voraussetzung | TypeScript ist Pflicht — Next.js erfüllt das |
| ADR-006 (Auth-Strategie) | Koordiniert | Auth.js als bevorzugte MVP-Auth wenn Next.js gewählt (Alternative 1 in ADR-006) |
| ADR-005 (RAG-Stack / Python) | Nachgelagert | Next.js API-Routes kommunizieren mit Python-Backend via HTTP |
| US-09 (Folgefragen) | Feature-Anforderung | Konversationshistorie (max. 3 Paare) im Client-State; kein Server-State nötig |

---

## Offen / Nächste Schritte

- [ ] ADR-006 aktualisieren: Auth.js als primäre Auth-Integration wenn Next.js bestätigt
- [ ] Python-Backend-Service-Interface definieren: OpenAPI-Spec oder TypeScript-Types für den HTTP-Kontrakt
- [ ] Docker-Compose-Setup für lokale Entwicklung: Next.js + Python-Backend + PostgreSQL (mit pgvector)
- [ ] Entscheiden: shadcn/ui oder Tailwind CSS direkt als Styling-Strategie (beeinflusst Komponenten-Bibliothek)
- [ ] Streaming-Implementation für Chat protoypisch testen — p95-Messung mit Mock-LLM und realem Netzwerk
