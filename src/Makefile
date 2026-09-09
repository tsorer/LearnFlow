.PHONY: up down seed seed-corpus logs check qa qa-be qa-fe generate-api lint-be typecheck-be test-be e2e e2e-logs e2e-down eval perf

# --- infra ---
up:
	docker compose up -d --build

down:
	docker compose down

seed:
	docker exec src-api-1 python seed_users.py

# T-28: uploads + indexes the real LearningCorpus PDFs (needs a real OPENAI_API_KEY,
# real embedding calls). Separate from `seed`: costs provider budget and time, so
# only `make eval` needs it, not every e2e run.
seed-corpus:
	docker exec src-api-1 python seed_corpus.py

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

# --- end-to-end (T-09) — eigenes Compose-Projekt, flüchtige DB (T-55, #123) ---
#
# Läuft im api-Container: der bringt pytest/httpx schon mit und sitzt im
# edge-Netz, der Test spricht die API also durch nginx (webapp) an — derselbe
# Weg, den der Browser nimmt. Nicht Teil von `make qa`.
#
# Braucht **keinen** laufenden Dev-Stack mehr: das Target fährt seinen eigenen
# hoch und wieder herunter.
#
# Lief bis T-55 gegen den Entwicklungs-Stack und damit gegen die persistente
# `learnflow`-Datenbank. Jetzt fährt `make e2e` einen zweiten, vollständig
# getrennten Stack hoch (siehe docker-compose.e2e.yml) — der Dev-Stack bleibt
# unberührt und lauffähig, und ein abgebrochener Lauf kann ihn nicht verbiegen.
#
# `webapp` allein anfordern, nicht den worker: `depends_on` zieht
# webapp -> api -> db hoch, während der worker sonst neben der api startet, also
# vor deren `alembic upgrade head`, die pgqueuer-Tabellen nicht findet und in
# einen Restart-Loop läuft, auf den `--wait` vergeblich wartet. Der Login-Flow
# braucht ihn nicht.
E2E_PROJECT := learnflow-e2e
E2E_COMPOSE := docker compose -p $(E2E_PROJECT) -f docker-compose.yml -f docker-compose.e2e.yml

e2e:
	@set -e; \
	$(E2E_COMPOSE) up -d --build --wait --wait-timeout 300 webapp; \
	$(E2E_COMPOSE) exec -T api python seed_users.py; \
	set +e; \
	$(E2E_COMPOSE) exec -T -e E2E_BASE_URL=http://webapp api pytest e2e -q; \
	status=$$?; \
	if [ $$status -eq 0 ]; then \
		$(E2E_COMPOSE) down --remove-orphans; \
	else \
		echo ""; \
		echo "e2e rot — der Stack bleibt für die Nachschau stehen:"; \
		echo "  make e2e-logs    Container-Logs"; \
		echo "  make e2e-down    aufräumen"; \
	fi; \
	exit $$status

e2e-logs:
	$(E2E_COMPOSE) logs --no-color --tail=200

# Ohne -v, obwohl dieses Projekt gar kein benanntes Volume hat (die Datenbank
# liegt auf tmpfs): `pgdata` trägt in docker-compose.yml einen globalen Namen,
# und ein `-v`, das hier einmal steht, wird irgendwann in ein Projekt kopiert,
# das ihn nicht überschrieben hat — und löscht dort die Entwicklungsdatenbank.
e2e-down:
	$(E2E_COMPOSE) down --remove-orphans

# --- out-of-corpus refusal rate (T-28, requires: make up && make seed && make seed-corpus) ---
# Same execution path as `e2e`: inside the api container, through nginx. Needs a
# real OPENAI_API_KEY (real embedding calls against the indexed corpus), so this is
# a manually run release gate, not a CI job (T-53, #110) -- not part of `make qa`
# or `make e2e` either way.
eval:
	docker exec -e E2E_BASE_URL=http://webapp src-api-1 pytest eval

# --- query latency (T-22, #29, requires: make up && make seed && make seed-corpus) ---
# Same execution path as eval: inside the api container, through nginx. Needs a real
# OPENAI_API_KEY (real embedding + generation calls against the indexed corpus) and
# fires several seeded accounts concurrently to approximate Normallast, so this is a
# manually run local check, not a CI job (T-53, #110, same constraint as `eval`) --
# not part of `make qa` or `make e2e` either way.
perf:
	docker exec -e E2E_BASE_URL=http://webapp src-api-1 pytest perf

# --- full local quality gate ---
qa: qa-be qa-fe
