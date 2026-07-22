from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

RLS_CONTEXT_INFO_KEY = "rls_context"
RLS_TENANT_SCOPE_SETTING = "app.current_tenant_scope"
RLS_PLATFORM_ADMIN_SETTING = "app.current_is_platform_admin"
RLS_PRINCIPAL_ID_SETTING = "app.current_principal_id"


class Base(DeclarativeBase):
    pass


@dataclass(frozen=True, slots=True)
class SessionRlsContext:
    tenant_ids: tuple[str, ...] = ()
    principal_id: str | None = None
    is_platform_admin: bool = False

    @property
    def tenant_scope_value(self) -> str:
        return ",".join(self.tenant_ids)

    @property
    def platform_admin_value(self) -> str:
        return "true" if self.is_platform_admin else "false"


class DatabaseSession(Session):
    pass


def normalize_session_rls_context(
    *,
    tenant_ids: Iterable[str] = (),
    principal_id: str | None = None,
    is_platform_admin: bool = False,
) -> SessionRlsContext:
    normalized_tenant_ids = tuple(
        sorted({tenant_id.strip() for tenant_id in tenant_ids if tenant_id and tenant_id.strip()})
    )
    normalized_principal_id = (
        principal_id.strip() if principal_id and principal_id.strip() else None
    )
    return SessionRlsContext(
        tenant_ids=normalized_tenant_ids,
        principal_id=normalized_principal_id,
        is_platform_admin=is_platform_admin,
    )


def get_session_rls_context(session: Session) -> SessionRlsContext:
    context = session.info.get(RLS_CONTEXT_INFO_KEY)
    if isinstance(context, SessionRlsContext):
        return context
    return SessionRlsContext()


def apply_session_rls_context_to_connection(
    connection: object,
    context: SessionRlsContext,
) -> None:
    dialect = getattr(connection, "dialect", None)
    if getattr(dialect, "name", None) != "postgresql":
        return

    execute = connection.execute
    execute(
        text(
            "SELECT "
            "set_config(:tenant_scope_setting, :tenant_scope_value, true), "
            "set_config(:platform_admin_setting, :platform_admin_value, true), "
            "set_config(:principal_id_setting, :principal_id_value, true)"
        ),
        {
            "tenant_scope_setting": RLS_TENANT_SCOPE_SETTING,
            "tenant_scope_value": context.tenant_scope_value,
            "platform_admin_setting": RLS_PLATFORM_ADMIN_SETTING,
            "platform_admin_value": context.platform_admin_value,
            "principal_id_setting": RLS_PRINCIPAL_ID_SETTING,
            "principal_id_value": context.principal_id or "",
        },
    )


def set_session_rls_context(
    session: Session,
    *,
    tenant_ids: Iterable[str] = (),
    principal_id: str | None = None,
    is_platform_admin: bool = False,
) -> SessionRlsContext:
    context = normalize_session_rls_context(
        tenant_ids=tenant_ids,
        principal_id=principal_id,
        is_platform_admin=is_platform_admin,
    )
    session.info[RLS_CONTEXT_INFO_KEY] = context

    if session.in_transaction():
        apply_session_rls_context_to_connection(session.connection(), context)

    return context


@event.listens_for(DatabaseSession, "after_begin")
def _apply_rls_context_after_begin(
    session: Session,
    _transaction: object,
    connection: object,
) -> None:
    apply_session_rls_context_to_connection(connection, get_session_rls_context(session))


class Database:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self.engine: Engine | None = None
        self._session_factory: sessionmaker[DatabaseSession] | None = None

    def connect(self) -> None:
        if self.engine is not None:
            return

        url = make_url(self._database_url)
        self._prepare_sqlite_directory(url)

        engine_kwargs: dict[str, object] = {
            "future": True,
            "pool_pre_ping": True,
        }

        if url.get_backend_name() == "sqlite":
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            if url.database in (None, "", ":memory:"):
                engine_kwargs["poolclass"] = StaticPool

        self.engine = create_engine(url, **engine_kwargs)
        self._session_factory = sessionmaker(
            bind=self.engine,
            class_=DatabaseSession,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    def disconnect(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
        self.engine = None
        self._session_factory = None

    def healthcheck(self) -> bool:
        if self.engine is None:
            return False

        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True

    @contextmanager
    def session(self) -> Iterator[Session]:
        if self._session_factory is None:
            raise RuntimeError("database session requested before initialization")

        session = self._session_factory()
        set_session_rls_context(session)
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _prepare_sqlite_directory(self, url: URL) -> None:
        if url.get_backend_name() != "sqlite":
            return
        if url.database in (None, "", ":memory:"):
            return

        database_path = Path(url.database)
        if not database_path.is_absolute():
            database_path = Path.cwd() / database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
