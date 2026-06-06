from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.models  # noqa: F401
from app.config import Settings
from app.database import Base
from app.main import create_app


def bootstrap_platform_admin(test_client: TestClient, settings: Settings) -> dict[str, object]:
    response = test_client.post(
        "/api/v1/auth/bootstrap/platform-admin",
        headers={
            "X-Action-Control-Plane-Bootstrap-Token": settings.bootstrap_admin_token,
        },
        json={
            "email": "platform-admin@example.com",
            "display_name": "Platform Admin",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'test.db'}",
        evidence_storage_root=str(tmp_path / "evidence"),
        enable_docs=False,
        log_format="console",
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    with TestClient(create_app(test_settings)) as test_client:
        engine = test_client.app.state.container.database.engine
        assert engine is not None
        Base.metadata.create_all(bind=engine)
        bootstrap = bootstrap_platform_admin(test_client, test_settings)
        test_client.headers.update({"Authorization": f"Bearer {bootstrap['access_token']}"})
        yield test_client
        Base.metadata.drop_all(bind=engine)
