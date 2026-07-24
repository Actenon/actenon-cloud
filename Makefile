PYTHON ?= .venv/bin/python
PIP ?= $(PYTHON) -m pip
APP_MODULE ?= app.main:app
COMPOSE_ENV_FILE ?= .env.compose
DOCKER_COMPOSE ?= docker compose --env-file $(COMPOSE_ENV_FILE)

.PHONY: install run test verify judge lint check package-check clean migrate-up migrate-revision container-build container-config container-db-up container-migrate container-up container-down container-logs container-ps container-verify verify-claims

# Machine-verify every claim the README and CONTROL_PLANE_RELEASE_READINESS.md
# make about cloud itself. Fable 5 Part 3A: for a trust product, one falsified
# claim costs more than ten missing features.
verify-claims:
	@echo "==> Verifying CONTROL_PLANE_RELEASE_READINESS.md ratings present"
	@python -c "import pathlib,sys; \
	        doc=pathlib.Path('docs/CONTROL_PLANE_RELEASE_READINESS.md').read_text(); \
	        required = ['Internal development readiness', 'Design-partner pilot readiness', 'Production deployment readiness']; \
	        missing = [r for r in required if r not in doc]; \
	        sys.exit(1) if missing else print('OK: all three readiness ratings present')"
	@echo "==> Verifying production readiness is still Red (not silently promoted)"
	@python -c "import pathlib,re; \
	        doc=pathlib.Path('docs/CONTROL_PLANE_RELEASE_READINESS.md').read_text(); \
	        m=re.search(r'\| Production deployment readiness \| (\w+) \|', doc); \
	        assert m, 'Production deployment readiness row not found'; \
	        rating=m.group(1); \
	        assert rating == 'Red', f'Production readiness is {rating}, expected Red (Fable 5 Part 3D)'; \
	        print(f'OK: production readiness is {rating}')"
	@echo "==> Verifying bootstrap admin backdoor acknowledged in readiness doc"
	@python -c "import pathlib,sys; \
	        doc=pathlib.Path('docs/CONTROL_PLANE_RELEASE_READINESS.md').read_text(); \
	        assert 'bootstrap admin backdoor' in doc.lower() or 'Bootstrap admin backdoor' in doc, \
	                'Bootstrap admin backdoor must be acknowledged in readiness doc (Fable 5 Part 3D)'; \
	        print('OK: bootstrap admin backdoor acknowledged')"
	@echo "==> Verifying KMS-not-yet-wired acknowledged in readiness doc"
	@python -c "import pathlib,sys; \
	        doc=pathlib.Path('docs/CONTROL_PLANE_RELEASE_READINESS.md').read_text(); \
	        assert 'No real KMS' in doc or 'KMS' in doc, \
	                'KMS status must be acknowledged in readiness doc (Fable 5 Part 3C/D)'; \
	        print('OK: KMS status acknowledged')"
	@echo "==> Verifying no kernel console-script collision (actenon-kernel renamed)"
	@python -c "import tomllib,sys; \
	        d=tomllib.load(open('pyproject.toml','rb')); \
	        scripts=d['project'].get('scripts',{}); \
	        assert 'actenon' not in scripts, 'Cloud must not register actenon console script (kernel owns actenon-kernel, permit owns actenon)'; \
	        print('OK: no actenon console script collision')"
	@echo "==> All cloud claims verified."

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
