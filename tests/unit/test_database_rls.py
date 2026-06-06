from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from starlette.requests import Request

from app.api.dependencies import get_current_session, get_db_session
from app.database import (
    DatabaseSession,
    SessionRlsContext,
    apply_session_rls_context_to_connection,
    get_session_rls_context,
    set_session_rls_context,
)
from app.services.auth import AuthenticatedSession


class FakePostgresConnection:
    def __init__(self) -> None:
        self.dialect = type("Dialect", (), {"name": "postgresql"})()
        self.calls: list[tuple[str, dict[str, str]]] = []

    def execute(self, statement: object, params: dict[str, str]) -> None:
        self.calls.append((str(statement), params))


class FakeSqliteConnection:
    def __init__(self) -> None:
        self.dialect = type("Dialect", (), {"name": "sqlite"})()
        self.calls: list[tuple[str, dict[str, str]]] = []

    def execute(self, statement: object, params: dict[str, str]) -> None:
        self.calls.append((str(statement), params))


class StubDatabase:
    def __init__(self, session: DatabaseSession) -> None:
        self._session = session

    @contextmanager
    def session(self) -> Any:
        yield self._session


class StubContainer:
    def __init__(self, session: DatabaseSession) -> None:
        self.database = StubDatabase(session)


class StubAuthService:
    def __init__(self, session: DatabaseSession, auth_session: AuthenticatedSession) -> None:
        self.session = session
        self._auth_session = auth_session

    def authenticate_bearer_token(self, bearer_token: str) -> AuthenticatedSession:
        assert bearer_token == "test-token"  # noqa: S105
        return self._auth_session


def make_request() -> Request:
    return Request({"type": "http", "headers": []})


def make_database_session() -> DatabaseSession:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    return DatabaseSession(bind=engine)


def make_authenticated_session() -> AuthenticatedSession:
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=30)
    return AuthenticatedSession(
        principal_type="user",
        principal_id="user-123",
        display_name="Tenant Operator",
        token_kind="operator",  # noqa: S106
        auth_mode="development_signed_bearer",
        issued_at=issued_at,
        expires_at=expires_at,
        platform_roles=(),
        platform_permissions=frozenset(),
        tenant_roles={
            "tenant-b": ("tenant_admin",),
            "tenant-a": ("tenant_admin",),
        },
        tenant_permissions={
            "tenant-b": frozenset({"tenant.action_intent.read"}),
            "tenant-a": frozenset({"tenant.action_intent.read"}),
        },
    )


def test_set_session_rls_context_normalizes_scope_and_principal() -> None:
    session = make_database_session()

    try:
        context = set_session_rls_context(
            session,
            tenant_ids=(" tenant-b ", "tenant-a", "tenant-a", ""),
            principal_id=" user-123 ",
            is_platform_admin=True,
        )

        assert context == SessionRlsContext(
            tenant_ids=("tenant-a", "tenant-b"),
            principal_id="user-123",
            is_platform_admin=True,
        )
        assert get_session_rls_context(session) == context
    finally:
        session.close()


def test_apply_session_rls_context_sets_postgres_transaction_settings() -> None:
    connection = FakePostgresConnection()
    context = SessionRlsContext(
        tenant_ids=("tenant-a", "tenant-b"),
        principal_id="user-123",
        is_platform_admin=False,
    )

    apply_session_rls_context_to_connection(connection, context)

    assert len(connection.calls) == 1
    statement, params = connection.calls[0]
    assert "set_config" in statement
    assert params == {
        "tenant_scope_setting": "app.current_tenant_scope",
        "tenant_scope_value": "tenant-a,tenant-b",
        "platform_admin_setting": "app.current_is_platform_admin",
        "platform_admin_value": "false",
        "principal_id_setting": "app.current_principal_id",
        "principal_id_value": "user-123",
    }


def test_apply_session_rls_context_skips_non_postgres_connections() -> None:
    connection = FakeSqliteConnection()
    context = SessionRlsContext(tenant_ids=("tenant-a",), principal_id="user-123")

    apply_session_rls_context_to_connection(connection, context)

    assert connection.calls == []


def test_get_db_session_exposes_request_scoped_session() -> None:
    session = make_database_session()
    request = make_request()
    dependency = get_db_session(request, StubContainer(session))

    try:
        yielded_session = next(dependency)
        assert yielded_session is session
        assert request.state.db_session is session
    finally:
        dependency.close()
        session.close()


def test_get_current_session_binds_authenticated_scope_into_db_session() -> None:
    session = make_database_session()
    request = make_request()
    request.state.db_session = session
    auth_session = make_authenticated_session()
    auth_service = StubAuthService(session, auth_session)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")

    try:
        resolved_session = get_current_session(request, credentials, auth_service)

        assert resolved_session == auth_session
        assert request.state.auth_session == auth_session
        assert get_session_rls_context(session) == SessionRlsContext(
            tenant_ids=("tenant-a", "tenant-b"),
            principal_id="user-123",
            is_platform_admin=False,
        )
    finally:
        session.close()
