.PHONY: up down seed logs check qa qa-be qa-fe generate-api lint-be typecheck-be test-be e2e

# --- infra ---
up:
	docker compose up -d --build

down:
	docker compose down

seed:
	docker exec src-api-1 python seed_users.py

logs:
	docker compose logs -f

# --- health check (all 4 services healthy) ---
check:
	@docker compose config --quiet
	@docker compose ps --format json | python -c "\
import sys, json; \
raw = sys.stdin.read().strip(); \
services = json.loads('[' + raw.replace('}\n{', '},{') + ']') if raw.startswith('{') else json.loads(raw); \
bad = [c['Name'] for c in services if c.get('Health', 'healthy') not in ('healthy', '')]; \
(print('Unhealthy:', ', '.join(bad)) or sys.exit(1)) if bad else print('All services healthy.')"

# --- backend quality (requires: make up) ---
lint-be:
	docker exec src-api-1 ruff check .

typecheck-be:
	docker exec src-api-1 mypy app worker

test-be:
	docker exec src-api-1 pytest

qa-be: lint-be typecheck-be test-be

# --- frontend quality (ephemeral node:22-alpine; kein make up nötig) ---
# openapi.yaml wird read-only nach /backend gemountet, damit der Drift-Check
# (T-39) die Spec unter demselben relativen Pfad findet wie im CI-Checkout:
# von /app aus ist ../backend/openapi.yaml genau dieser Mount.
qa-fe:
	docker run --rm \
		-v "$(CURDIR)/frontend:/app" \
		-v "$(CURDIR)/backend/openapi.yaml:/backend/openapi.yaml:ro" \
		-v //app/node_modules \
		-w //app node:22-alpine \
		sh -c "npm ci --silent && npm run lint && npm run check && npm run test"

# --- API-Typen neu generieren (nach jeder openapi.yaml-Änderung) ---
# Auch für Backend-Entwickler ohne lokales Node: derselbe Container wie qa-fe.
# Die erzeugte src/api/schema.d.ts gehört in denselben Commit wie die Spec.
#
# Benanntes Volume statt anonymem, und `npm ci` nur beim ersten Mal: der
# Generator selbst braucht unter einer Sekunde, ein voller Install jedes Mal
# machte den Befehl teurer als das Problem. CLAUDE.md schreibt ihn nach jeder
# Spec-Änderung vor — was Minuten kostet, wird umgangen.
#
# Die Bedingung prüft die Binärdatei, nicht das Lockfile: nach einem Bump von
# openapi-typescript generiert das Volume weiter mit der alten Version, und die
# committeten Typen fallen in der CI durch — mit genau dem Befehl in der
# Meldung, den man gerade ausgeführt hat. Dann einmalig:
#   docker volume rm learnflow-fe-node-modules
generate-api:
	docker run --rm \
		-v "$(CURDIR)/frontend:/app" \
		-v "$(CURDIR)/backend/openapi.yaml:/backend/openapi.yaml:ro" \
		-v learnflow-fe-node-modules://app/node_modules \
		-w //app node:22-alpine \
		sh -c "[ -x node_modules/.bin/openapi-typescript ] || npm ci --silent; npm run generate:api"

# --- end-to-end (T-09, requires: make up && make seed) ---
# Runs inside the api container: it already ships pytest/httpx and sits on the
# edge network, so the test talks to the API through nginx (webapp) — the same
# path the browser takes. Not part of `make qa`; it needs the running stack.
e2e:
	docker exec -e E2E_BASE_URL=http://webapp src-api-1 pytest e2e

# --- full local quality gate ---
qa: qa-be qa-fe
