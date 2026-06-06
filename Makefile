PYTHON ?= .venv/bin/python
PIP ?= $(PYTHON) -m pip
APP_MODULE ?= app.main:app
COMPOSE_ENV_FILE ?= .env.compose
DOCKER_COMPOSE ?= docker compose --env-file $(COMPOSE_ENV_FILE)

.PHONY: install run test verify judge lint check package-check clean migrate-up migrate-revision container-build container-config container-db-up container-migrate container-up container-down container-logs container-ps container-verify

install:
	$(PIP) install --upgrade pip
	$(PIP) install -e .[dev]

run:
	$(PYTHON) -m uvicorn $(APP_MODULE) --host 127.0.0.1 --port 8000 --reload

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m pytest

verify:
	bash scripts/verify.sh

judge:
	bash scripts/judge.sh

lint:
	$(PYTHON) -m ruff check --no-cache app tests scripts

check:
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) verify

package-check:
	@TMP_DIR="$$(mktemp -d)"; \
	rm -rf build dist action_control_plane.egg-info actenon_cloud.egg-info; \
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m build --sdist --wheel --outdir "$$TMP_DIR" >/dev/null; \
	ls "$$TMP_DIR" >/dev/null; \
	rm -rf build dist action_control_plane.egg-info actenon_cloud.egg-info .ruff_cache; \
	find app migrations tests -type d -name '__pycache__' -prune -exec rm -rf {} +; \
	rm -rf "$$TMP_DIR"

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .tox .nox .cache build dist action_control_plane.egg-info actenon_cloud.egg-info
	find app migrations tests -type d -name '__pycache__' -prune -exec rm -rf {} +

migrate-up:
	$(PYTHON) -m alembic upgrade head

migrate-revision:
	@if [ -z "$(MESSAGE)" ]; then echo "Usage: make migrate-revision MESSAGE=message"; exit 1; fi
	$(PYTHON) -m alembic revision --autogenerate -m "$(MESSAGE)"

container-build:
	$(DOCKER_COMPOSE) build

container-config:
	$(DOCKER_COMPOSE) config

container-db-up:
	$(DOCKER_COMPOSE) up -d db

container-migrate:
	$(DOCKER_COMPOSE) run --rm migrate

container-up:
	$(DOCKER_COMPOSE) up -d db
	$(DOCKER_COMPOSE) run --rm migrate
	$(DOCKER_COMPOSE) up -d app

container-down:
	$(DOCKER_COMPOSE) down --remove-orphans

container-logs:
	$(DOCKER_COMPOSE) logs -f app

container-ps:
	$(DOCKER_COMPOSE) ps

container-verify:
	@set -a; . $(COMPOSE_ENV_FILE); set +a; \
	curl -fsS "http://127.0.0.1:$${ACTION_CONTROL_PLANE_PORT:-8000}/api/v1/health/live"; \
	echo; \
	curl -fsS "http://127.0.0.1:$${ACTION_CONTROL_PLANE_PORT:-8000}/api/v1/health/ready"; \
	echo
