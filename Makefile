# Ein Befehl, der lokal exakt das prueft, was die CI prueft.
#   make check            -> Backend + Frontend
#   make check-backend    -> nur Python (ruff, mypy, pytest)
#   make check-frontend   -> nur TypeScript (eslint, tsc, vitest)

.PHONY: check check-backend check-frontend

check: check-backend check-frontend

check-backend:
	cd src/backend && ruff check .
	cd src/backend && if find . -name '*.py' | grep -q .; then mypy .; else echo "Keine .py-Dateien — mypy uebersprungen."; fi
	cd src/backend && { pytest || [ $$? -eq 5 ]; }

check-frontend:
	cd src/frontend && npm run check
