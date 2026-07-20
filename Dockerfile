FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ACTION_CONTROL_PLANE_HOST=0.0.0.0 \
    ACTION_CONTROL_PLANE_PORT=8000 \
    ACTION_CONTROL_PLANE_EVIDENCE_STORAGE_ROOT=/var/lib/actenon-cloud/evidence

WORKDIR /srv/action-control-plane

# git is required because pyproject.toml has a git+https dependency on
# actenon-kernel. python:3.12-slim does not ship git by default.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip

COPY pyproject.toml README.md alembic.ini ./
COPY app ./app
COPY migrations ./migrations
COPY schemas ./schemas
COPY scripts ./scripts

RUN python -m pip install .

RUN useradd --system --create-home --home-dir /home/actioncontrol --shell /usr/sbin/nologin actioncontrol \
    && mkdir -p /var/lib/actenon-cloud/evidence \
    && chown -R actioncontrol:actioncontrol /srv/action-control-plane /var/lib/actenon-cloud \
    && chmod +x /srv/action-control-plane/scripts/container-entrypoint.sh

USER actioncontrol

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 CMD python -c "import os, sys, urllib.request; prefix=os.getenv('ACTION_CONTROL_PLANE_API_V1_PREFIX','/api/v1').rstrip('/'); port=os.getenv('ACTION_CONTROL_PLANE_PORT','8000'); url=f'http://127.0.0.1:{port}{prefix}/health/ready'; sys.exit(0 if urllib.request.urlopen(url, timeout=3).status == 200 else 1)"

ENTRYPOINT ["./scripts/container-entrypoint.sh"]
CMD ["web"]
