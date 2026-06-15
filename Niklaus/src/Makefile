.PHONY: up down seed logs check qa qa-be qa-fe lint-be typecheck-be test-be

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

# --- frontend quality (ephemeral node:22-alpine; no make up needed) ---
# node_modules is kept in an anonymous volume to avoid polluting the host checkout
qa-fe:
	docker run --rm \
		-v "$(CURDIR)/frontend:/app" \
		-v /app/node_modules \
		-w /app node:22-alpine \
		sh -c "npm ci --silent && npm run lint && npm run typecheck && npm run test"

# --- full local quality gate ---
qa: qa-be qa-fe
