# LearnFlow – Lokales Setup

---

## Voraussetzungen

- Python 3.11+
- Node.js 20+
- Angular CLI: `npm install -g @angular/cli`
- Git

---

## 1. Repository klonen

```bash
git clone https://github.com/[org]/LearnFlow.git
cd LearnFlow
```

---

## 2. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Umgebungsvariablen
cp .env.example .env
# .env mit echten Werten befüllen (Azure OpenAI Key etc.)

# Backend starten
uvicorn app.main:app --reload
# → läuft auf http://localhost:8000
# → API-Docs: http://localhost:8000/docs
```

---

## 3. Frontend setup

```bash
cd frontend
npm install
ng serve
# → läuft auf http://localhost:4200
```

---

## 4. Tests ausführen

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && ng test
```

---

## Umgebungsvariablen

Siehe `backend/.env.example` für alle nötigen Variablen.
Echte Werte werden **nicht** ins Repo committed – bitte bei einem Teammitglied anfragen.

---

## Hilfreiche Links

- API-Dokumentation: http://localhost:8000/docs (nach Backend-Start)
- Angular Dev-Server: http://localhost:4200
- Projektplan: `Artefakten/Modul1Tag2/LearnFlow_Plan_15Wochen.md`
