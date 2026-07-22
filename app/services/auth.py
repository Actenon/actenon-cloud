from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import (
    ActionIntentRecord,
    AuditEvent,
    EscrowRecord,
    EvidenceObject,
    IssuedProof,
    MembershipStatus,
    Policy,
    ReceiptRecord,
    ReconciliationRecord,
    Role,
    RoleScope,
    ServicePrincipal,
    ServicePrincipalStatus,
    SigningKeyReference,
    Tenant,
    TenantMembership,
    User,
    UserStatus,
)

PLATFORM_ADMIN_MANAGE = "platform.admin.manage"
PLATFORM_TENANTS_MANAGE = "platform.tenants.manage"
PLATFORM_AUTH_MANAGE = "platform.auth.manage"
PLATFORM_AUDIT_READ = "platform.audit.read"

TENANT_MEMBERSHIP_MANAGE = "tenant.membership.manage"
TENANT_POLICY_READ = "tenant.policy.read"
TENANT_POLICY_WRITE = "tenant.policy.write"
TENANT_ACTION_INTENT_READ = "tenant.action_intent.read"
TENANT_ACTION_INTENT_WRITE = "tenant.action_intent.write"
TENANT_APPROVAL_READ = "tenant.approval.read"
TENANT_APPROVAL_WRITE = "tenant.approval.write"
TENANT_EVIDENCE_READ = "tenant.evidence.read"
TENANT_EVIDENCE_WRITE = "tenant.evidence.write"
TENANT_ISSUANCE_READ = "tenant.issuance.read"
TENANT_ISSUANCE_WRITE = "tenant.issuance.write"
TENANT_ESCROW_READ = "tenant.escrow.read"
TENANT_ESCROW_WRITE = "tenant.escrow.write"
TENANT_RECEIPT_READ = "tenant.receipt.read"
TENANT_RECEIPT_WRITE = "tenant.receipt.write"
TENANT_AUDIT_READ = "tenant.audit.read"
TOKEN_KIND_OPERATOR = "operator"  # noqa: S105
TOKEN_KIND_SERVICE = "service"  # noqa: S105
TOKEN_TYPE_BEARER = "bearer"  # noqa: S105
AUTH_MODE_DEVELOPMENT_SIGNED_BEARER = "development_signed_bearer"
AUTH_MODE_EXTERNAL_MANAGED_BEARER = "external_managed_bearer"


class AuthenticationError(PermissionError):
    pass


class AuthorizationError(PermissionError):
    pass


class AuthValidationError(ValueError):
    pass


class AuthConflictError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    principal_type: Literal["user", "service_principal"]
    principal_id: str
    display_name: str
    token_kind: Literal["operator", "service"]
    auth_mode: str
    issued_at: datetime
    expires_at: datetime
    platform_roles: tuple[str, ...]
    platform_permissions: frozenset[str]
    tenant_roles: dict[str, tuple[str, ...]]
    tenant_permissions: dict[str, frozenset[str]]

    @property
    def tenant_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.tenant_permissions))

    @property
    def is_platform_admin(self) -> bool:
        return PLATFORM_ADMIN_MANAGE in self.platform_permissions

    def has_platform_permission(self, permission: str) -> bool:
        return permission in self.platform_permissions

    def has_any_tenant_access(self, tenant_id: str) -> bool:
        return self.is_platform_admin or tenant_id in self.tenant_permissions

    def has_tenant_permission(self, tenant_id: str, permission: str) -> bool:
        if self.is_platform_admin:
            return True
        return permission in self.tenant_permissions.get(tenant_id, frozenset())


@dataclass(frozen=True, slots=True)
class IssuedToken:
    access_token: str
    token_type: str
    expires_at: datetime


SYSTEM_ROLE_DEFINITIONS = (
    {
        "scope": RoleScope.platform,
        "name": "platform_admin",
        "description": "Full platform administration for Actenon Cloud.",
        "permissions": [
            PLATFORM_ADMIN_MANAGE,
            PLATFORM_TENANTS_MANAGE,
            PLATFORM_AUTH_MANAGE,
            PLATFORM_AUDIT_READ,
        ],
    },
    {
        "scope": RoleScope.tenant,
        "name": "tenant_admin",
        "description": "Full tenant-level administration for finance control-plane workflows.",
        "permissions": [
            TENANT_MEMBERSHIP_MANAGE,
            TENANT_POLICY_READ,
            TENANT_POLICY_WRITE,
            TENANT_ACTION_INTENT_READ,
            TENANT_ACTION_INTENT_WRITE,
            TENANT_APPROVAL_READ,
            TENANT_APPROVAL_WRITE,
            TENANT_EVIDENCE_READ,
            TENANT_EVIDENCE_WRITE,
            TENANT_ISSUANCE_READ,
            TENANT_ISSUANCE_WRITE,
            TENANT_ESCROW_READ,
            TENANT_ESCROW_WRITE,
            TENANT_RECEIPT_READ,
            TENANT_RECEIPT_WRITE,
            TENANT_AUDIT_READ,
        ],
    },
    {
        "scope": RoleScope.tenant,
        "name": "policy_admin",
        "description": "Can manage workflow policy definitions within a tenant.",
        "permissions": [
            TENANT_POLICY_READ,
            TENANT_POLICY_WRITE,
            TENANT_ACTION_INTENT_READ,
        ],
    },
    {
        "scope": RoleScope.tenant,
        "name": "audit_viewer",
        "description": "Can review searchable finance traces, receipts, and audit exports.",
        "permissions": [
            TENANT_ACTION_INTENT_READ,
            TENANT_RECEIPT_READ,
            TENANT_AUDIT_READ,
        ],
    },
    {
        "scope": RoleScope.tenant,
        "name": "service_operator",
        "description": (
            "Service-to-service operator for issuance, escrow, receipt, "
            "and audit hooks."
        ),
        "permissions": [
            TENANT_ACTION_INTENT_READ,
            TENANT_ISSUANCE_READ,
            TENANT_ISSUANCE_WRITE,
            TENANT_ESCROW_READ,
            TENANT_ESCROW_WRITE,
            TENANT_RECEIPT_READ,
            TENANT_RECEIPT_WRITE,
            TENANT_AUDIT_READ,
        ],
    },
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class AuthService:
    def __init__(self, session: Session, *, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def ensure_system_roles(self) -> list[Role]:
        roles: list[Role] = []
        changed = False
        for definition in SYSTEM_ROLE_DEFINITIONS:
            role_key = self._role_key(
                scope=definition["scope"],
                name=definition["name"],
                tenant_id=None,
            )
            role = self.session.scalar(select(Role).where(Role.role_key == role_key))
            if role is None:
                role = Role(
                    role_id=uuid4().hex,
                    role_key=role_key,
                    tenant_id=None,
                    scope=definition["scope"],
                    name=definition["name"],
                    description=definition["description"],
                    permissions=list(definition["permissions"]),
                    is_system=True,
                )
                self.session.add(role)
                changed = True
            roles.append(role)
        if changed:
            self.session.commit()
            roles = list(
                self.session.scalars(
                    select(Role).where(Role.is_system.is_(True)).order_by(Role.name.asc())
                )
            )
        return roles

    def bootstrap_platform_admin(
        self,
        *,
        bootstrap_token: str,
        email: str,
        display_name: str,
    ) -> tuple[User, IssuedToken]:
        self._ensure_development_auth_enabled()
        self.ensure_system_roles()
        if bootstrap_token != self.settings.bootstrap_admin_token:
            raise AuthenticationError("bootstrap token is invalid")

        platform_admin_role = self._get_system_role(RoleScope.platform, "platform_admin")
        requested_email = self._normalize_email(email)
        existing_platform_admins = [
            user
            for user in self.list_users()
            if platform_admin_role.role_id in user.platform_role_ids
            and user.status == UserStatus.active
        ]
        for admin in existing_platform_admins:
            if admin.email != requested_email:
                raise AuthConflictError("platform admin bootstrap has already been completed")

        user = self.session.scalar(select(User).where(User.email == requested_email))
        if user is None:
            user = User(
                user_id=uuid4().hex,
                email=requested_email,
                display_name=display_name.strip(),
                platform_role_ids=[platform_admin_role.role_id],
                status=UserStatus.active,
                auth_metadata={"bootstrap_created": True},
            )
            self.session.add(user)
        elif platform_admin_role.role_id not in user.platform_role_ids:
            user.platform_role_ids = list(user.platform_role_ids) + [platform_admin_role.role_id]
            user.status = UserStatus.active
            self.session.add(user)

        self.session.commit()
        self.session.refresh(user)
        token = self.issue_operator_token(user.user_id)
        return user, token

    def authenticate_bearer_token(self, bearer_token: str) -> AuthenticatedSession:
        self.ensure_system_roles()
        if self.settings.auth_mode == AUTH_MODE_EXTERNAL_MANAGED_BEARER:
            return self._authenticate_external_managed_bearer(bearer_token)
        if self.settings.auth_mode != AUTH_MODE_DEVELOPMENT_SIGNED_BEARER:
            raise AuthenticationError(f"unsupported auth mode '{self.settings.auth_mode}'")
        # B6: the development signed-bearer path is a pilot/test-only
        # convenience. It must NEVER authenticate in production, even if the
        # config validator is bypassed (defense in depth).
        if self.settings.environment == "production":
            raise AuthenticationError(
                "development signed bearer authentication is refused in production"
            )

        payload = self._decode_development_token(bearer_token)
        issued_at = datetime.fromtimestamp(payload["iat"], tz=UTC)
        expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
        principal_type = payload["principal_type"]
        principal_id = payload["principal_id"]
        token_kind = payload["token_kind"]
        if principal_type == "user":
            if token_kind != TOKEN_KIND_OPERATOR:
                raise AuthenticationError("user token kind is invalid")
            return self._session_for_user(
                user_id=principal_id,
                issued_at=issued_at,
                expires_at=expires_at,
            )
        if principal_type == "service_principal":
            if token_kind != TOKEN_KIND_SERVICE:
                raise AuthenticationError("service token kind is invalid")
            return self._session_for_service_principal(
                service_principal_id=principal_id,
                issued_at=issued_at,
                expires_at=expires_at,
            )
        raise AuthenticationError("token principal type is unsupported")

    def issue_operator_token(
        self,
        user_id: str,
        *,
        expires_in_seconds: int | None = None,
    ) -> IssuedToken:
        self._ensure_development_auth_enabled()
        user = self._get_user(user_id)
        if user.status != UserStatus.active:
            raise AuthorizationError("operator tokens may only be issued for active users")
        return self._issue_token(
            principal_type="user",
            principal_id=user.user_id,
            token_kind=TOKEN_KIND_OPERATOR,
            expires_in_seconds=expires_in_seconds or self.settings.auth_operator_token_ttl_seconds,
        )

    def issue_service_token(
        self,
        service_principal_id: str,
        *,
        expires_in_seconds: int | None = None,
    ) -> IssuedToken:
        self._ensure_development_auth_enabled()
        principal = self._get_service_principal(service_principal_id)
        if principal.status != ServicePrincipalStatus.active:
            raise AuthorizationError(
                "service tokens may only be issued for active service principals"
            )
        return self._issue_token(
            principal_type="service_principal",
            principal_id=principal.service_principal_id,
            token_kind=TOKEN_KIND_SERVICE,
            expires_in_seconds=expires_in_seconds or self.settings.auth_service_token_ttl_seconds,
        )

    def create_user(
        self,
        *,
        email: str,
        display_name: str,
        platform_role_ids: list[str] | None = None,
        identity_provider_subject: str | None = None,
        auth_metadata: dict[str, object] | None = None,
    ) -> User:
        self.ensure_system_roles()
        normalized_email = self._normalize_email(email)
        existing = self.session.scalar(select(User).where(User.email == normalized_email))
        if existing is not None:
            raise AuthConflictError(f"user '{normalized_email}' already exists")

        validated_role_ids = self._validate_platform_role_ids(platform_role_ids or [])
        user = User(
            user_id=uuid4().hex,
            email=normalized_email,
            display_name=display_name.strip(),
            identity_provider_subject=identity_provider_subject,
            platform_role_ids=validated_role_ids,
            auth_metadata=dict(auth_metadata or {}),
            status=UserStatus.active,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def list_users(self) -> list[User]:
        return list(self.session.scalars(select(User).order_by(User.created_at.asc())))

    def create_role(
        self,
        *,
        name: str,
        scope: RoleScope,
        permissions: list[str],
        description: str | None,
        tenant_id: str | None,
    ) -> Role:
        self.ensure_system_roles()
        if scope == RoleScope.platform and tenant_id is not None:
            raise AuthValidationError("platform roles must not be bound to a tenant")
        if scope == RoleScope.tenant and tenant_id is None:
            raise AuthValidationError("custom tenant roles must specify tenant_id")
        if tenant_id is not None:
            self._get_tenant(tenant_id)

        role_key = self._role_key(scope=scope, name=name, tenant_id=tenant_id)
        existing = self.session.scalar(select(Role).where(Role.role_key == role_key))
        if existing is not None:
            raise AuthConflictError(f"role '{name}' already exists for the requested scope")

        role = Role(
            role_id=uuid4().hex,
            role_key=role_key,
            tenant_id=tenant_id,
            scope=scope,
            name=name.strip(),
            description=description,
            permissions=sorted(set(permissions)),
            is_system=False,
        )
        self.session.add(role)
        self.session.commit()
        self.session.refresh(role)
        return role

    def list_roles(
        self,
        *,
        scope: RoleScope | None = None,
        tenant_id: str | None = None,
    ) -> list[Role]:
        self.ensure_system_roles()
        query = select(Role).order_by(Role.scope.asc(), Role.name.asc(), Role.created_at.asc())
        if scope is not None:
            query = query.where(Role.scope == scope)
        if tenant_id is not None:
            query = query.where((Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)))
        return list(self.session.scalars(query))

    def create_membership(
        self,
        *,
        tenant_id: str,
        user_id: str,
        role_ids: list[str],
    ) -> TenantMembership:
        self.ensure_system_roles()
        self._get_tenant(tenant_id)
        self._get_user(user_id)
        validated_role_ids = self._validate_tenant_role_ids(tenant_id, role_ids)

        membership = self.session.scalar(
            select(TenantMembership).where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.user_id == user_id,
            )
        )
        if membership is None:
            membership = TenantMembership(
                membership_id=uuid4().hex,
                tenant_id=tenant_id,
                user_id=user_id,
                role_ids=validated_role_ids,
                status=MembershipStatus.active,
            )
            self.session.add(membership)
        else:
            membership.role_ids = validated_role_ids
            membership.status = MembershipStatus.active
            self.session.add(membership)

        self.session.commit()
        self.session.refresh(membership)
        return membership

    def list_memberships(self, tenant_id: str) -> list[TenantMembership]:
        self._get_tenant(tenant_id)
        return list(
            self.session.scalars(
                select(TenantMembership)
                .where(TenantMembership.tenant_id == tenant_id)
                .order_by(TenantMembership.created_at.asc())
            )
        )

    def create_service_principal(
        self,
        *,
        tenant_id: str | None,
        display_name: str,
        description: str | None,
        role_ids: list[str],
        auth_metadata: dict[str, object] | None = None,
    ) -> ServicePrincipal:
        self.ensure_system_roles()
        normalized_name = display_name.strip()
        if tenant_id is not None:
            self._get_tenant(tenant_id)
            validated_role_ids = self._validate_tenant_role_ids(tenant_id, role_ids)
        else:
            validated_role_ids = self._validate_platform_role_ids(role_ids)

        principal_key = self._service_principal_key(
            tenant_id=tenant_id,
            display_name=normalized_name,
        )
        existing = self.session.scalar(
            select(ServicePrincipal).where(ServicePrincipal.principal_key == principal_key)
        )
        if existing is not None:
            raise AuthConflictError(
                f"service principal '{normalized_name}' already exists for the requested scope"
            )

        principal = ServicePrincipal(
            service_principal_id=uuid4().hex,
            principal_key=principal_key,
            tenant_id=tenant_id,
            display_name=normalized_name,
            description=description,
            role_ids=validated_role_ids,
            auth_mode=self.settings.auth_mode,
            status=ServicePrincipalStatus.active,
            auth_metadata=dict(auth_metadata or {}),
        )
        self.session.add(principal)
        self.session.commit()
        self.session.refresh(principal)
        return principal

    def list_service_principals(self, *, tenant_id: str | None = None) -> list[ServicePrincipal]:
        query = select(ServicePrincipal).order_by(ServicePrincipal.created_at.asc())
        if tenant_id is not None:
            query = query.where(ServicePrincipal.tenant_id == tenant_id)
        return list(self.session.scalars(query))

    def require_platform_permission(
        self,
        auth_session: AuthenticatedSession,
        permission: str,
    ) -> None:
        if not auth_session.has_platform_permission(permission):
            raise AuthorizationError(f"principal lacks required platform permission '{permission}'")

    def require_tenant_access(
        self,
        auth_session: AuthenticatedSession,
        tenant_id: str,
    ) -> None:
        if not auth_session.has_any_tenant_access(tenant_id):
            raise AuthorizationError(f"principal has no access to tenant '{tenant_id}'")

    def require_tenant_permission(
        self,
        auth_session: AuthenticatedSession,
        *,
        tenant_id: str,
        permission: str,
    ) -> None:
        if not auth_session.has_tenant_permission(tenant_id, permission):
            raise AuthorizationError(
                "principal lacks required tenant permission "
                f"'{permission}' for tenant '{tenant_id}'"
            )

    def require_tenant_query_scope(
        self,
        auth_session: AuthenticatedSession,
        *,
        tenant_id: str | None,
        permission: str,
    ) -> str | None:
        if auth_session.is_platform_admin:
            return tenant_id
        if tenant_id is None:
            if len(auth_session.tenant_ids) == 1:
                tenant_id = auth_session.tenant_ids[0]
            else:
                raise AuthorizationError("tenant_id is required for non-platform queries")
        self.require_tenant_permission(auth_session, tenant_id=tenant_id, permission=permission)
        return tenant_id

    def tenant_role_ids_for_session(
        self,
        auth_session: AuthenticatedSession,
        *,
        tenant_id: str,
    ) -> list[str]:
        if auth_session.principal_type == "user":
            membership = self.session.scalar(
                select(TenantMembership).where(
                    TenantMembership.tenant_id == tenant_id,
                    TenantMembership.user_id == auth_session.principal_id,
                    TenantMembership.status == MembershipStatus.active,
                )
            )
            if membership is None:
                return []
            role_map = self._resolve_role_map(membership.role_ids)
            return [
                role_id
                for role_id in membership.role_ids
                if role_map[role_id].scope == RoleScope.tenant
                and role_map[role_id].tenant_id in (None, tenant_id)
            ]

        if auth_session.principal_type == "service_principal":
            principal = self._get_service_principal(auth_session.principal_id)
            if (
                principal.status != ServicePrincipalStatus.active
                or principal.tenant_id != tenant_id
            ):
                return []
            role_map = self._resolve_role_map(principal.role_ids)
            return [
                role_id
                for role_id in principal.role_ids
                if role_map[role_id].scope == RoleScope.tenant
                and role_map[role_id].tenant_id in (None, tenant_id)
            ]

        raise AuthValidationError(
            f"principal type '{auth_session.principal_type}' is not supported"
        )

    def tenant_id_for(self, resource: object) -> str:
        tenant_id = getattr(resource, "tenant_id", None)
        if not isinstance(tenant_id, str) or not tenant_id:
            raise AuthValidationError("resource is missing tenant context")
        return tenant_id

    def get_platform_admin_role(self) -> Role:
        self.ensure_system_roles()
        return self._get_system_role(RoleScope.platform, "platform_admin")

    def _session_for_user(
        self,
        *,
        user_id: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> AuthenticatedSession:
        user = self._get_user(user_id)
        if user.status != UserStatus.active:
            raise AuthenticationError("user is not active")

        platform_roles = self._resolve_role_map(user.platform_role_ids)
        platform_permissions = self._permissions_from_roles(
            roles=platform_roles.values(),
            expected_scope=RoleScope.platform,
            tenant_id=None,
        )
        tenant_role_names: dict[str, tuple[str, ...]] = {}
        tenant_permissions: dict[str, frozenset[str]] = {}
        memberships = list(
            self.session.scalars(
                select(TenantMembership).where(
                    TenantMembership.user_id == user_id,
                    TenantMembership.status == MembershipStatus.active,
                )
            )
        )
        for membership in memberships:
            roles = self._resolve_role_map(membership.role_ids)
            tenant_permissions[membership.tenant_id] = self._permissions_from_roles(
                roles=roles.values(),
                expected_scope=RoleScope.tenant,
                tenant_id=membership.tenant_id,
            )
            tenant_role_names[membership.tenant_id] = tuple(
                sorted(role.name for role in roles.values())
            )

        return AuthenticatedSession(
            principal_type="user",
            principal_id=user.user_id,
            display_name=user.display_name,
            token_kind=TOKEN_KIND_OPERATOR,
            auth_mode=self.settings.auth_mode,
            issued_at=issued_at,
            expires_at=expires_at,
            platform_roles=tuple(sorted(role.name for role in platform_roles.values())),
            platform_permissions=platform_permissions,
            tenant_roles=tenant_role_names,
            tenant_permissions=tenant_permissions,
        )

    def _session_for_service_principal(
        self,
        *,
        service_principal_id: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> AuthenticatedSession:
        principal = self._get_service_principal(service_principal_id)
        if principal.status != ServicePrincipalStatus.active:
            raise AuthenticationError("service principal is not active")

        role_map = self._resolve_role_map(principal.role_ids)
        platform_permissions = frozenset()
        platform_roles: tuple[str, ...] = ()
        tenant_permissions: dict[str, frozenset[str]] = {}
        tenant_roles: dict[str, tuple[str, ...]] = {}

        platform_role_map = {
            role_id: role for role_id, role in role_map.items() if role.scope == RoleScope.platform
        }
        if platform_role_map:
            platform_permissions = self._permissions_from_roles(
                roles=platform_role_map.values(),
                expected_scope=RoleScope.platform,
                tenant_id=None,
            )
            platform_roles = tuple(sorted(role.name for role in platform_role_map.values()))

        if principal.tenant_id is not None:
            tenant_role_map = {
                role_id: role
                for role_id, role in role_map.items()
                if role.scope == RoleScope.tenant
            }
            tenant_permissions[principal.tenant_id] = self._permissions_from_roles(
                roles=tenant_role_map.values(),
                expected_scope=RoleScope.tenant,
                tenant_id=principal.tenant_id,
            )
            tenant_roles[principal.tenant_id] = tuple(
                sorted(role.name for role in tenant_role_map.values())
            )

        return AuthenticatedSession(
            principal_type="service_principal",
            principal_id=principal.service_principal_id,
            display_name=principal.display_name,
            token_kind=TOKEN_KIND_SERVICE,
            auth_mode=principal.auth_mode,
            issued_at=issued_at,
            expires_at=expires_at,
            platform_roles=platform_roles,
            platform_permissions=platform_permissions,
            tenant_roles=tenant_roles,
            tenant_permissions=tenant_permissions,
        )

    def _permissions_from_roles(
        self,
        *,
        roles: object,
        expected_scope: RoleScope,
        tenant_id: str | None,
    ) -> frozenset[str]:
        permissions: set[str] = set()
        for role in roles:
            if role.scope != expected_scope:
                raise AuthenticationError(f"role '{role.name}' has unexpected scope")
            if expected_scope == RoleScope.tenant and role.tenant_id not in (None, tenant_id):
                raise AuthenticationError(f"role '{role.name}' is bound to a different tenant")
            permissions.update(role.permissions)
        return frozenset(permissions)

    def _resolve_role_map(self, role_ids: list[str]) -> dict[str, Role]:
        if not role_ids:
            return {}
        roles = list(self.session.scalars(select(Role).where(Role.role_id.in_(role_ids))))
        role_map = {role.role_id: role for role in roles}
        missing = [role_id for role_id in role_ids if role_id not in role_map]
        if missing:
            raise AuthenticationError(f"unknown role ids in principal assignment: {missing}")
        return role_map

    def _validate_platform_role_ids(self, role_ids: list[str]) -> list[str]:
        role_map = self._resolve_role_map(role_ids)
        for role in role_map.values():
            if role.scope != RoleScope.platform:
                raise AuthValidationError(
                    f"role '{role.name}' is not a platform-scoped role assignment"
                )
        return list(role_ids)

    def _validate_tenant_role_ids(self, tenant_id: str, role_ids: list[str]) -> list[str]:
        role_map = self._resolve_role_map(role_ids)
        for role in role_map.values():
            if role.scope != RoleScope.tenant:
                raise AuthValidationError(f"role '{role.name}' is not a tenant-scoped role")
            if role.tenant_id not in (None, tenant_id):
                raise AuthValidationError(
                    f"role '{role.name}' belongs to a different tenant scope"
                )
        return list(role_ids)

    def _get_user(self, user_id: str) -> User:
        user = self.session.get(User, user_id)
        if user is None:
            raise AuthValidationError(f"user '{user_id}' was not found")
        return user

    def _get_tenant(self, tenant_id: str) -> Tenant:
        tenant = self.session.get(Tenant, tenant_id)
        if tenant is None:
            raise AuthValidationError(f"tenant '{tenant_id}' was not found")
        return tenant

    def _get_service_principal(self, service_principal_id: str) -> ServicePrincipal:
        principal = self.session.get(ServicePrincipal, service_principal_id)
        if principal is None:
            raise AuthValidationError(f"service principal '{service_principal_id}' was not found")
        return principal

    def _get_system_role(self, scope: RoleScope, name: str) -> Role:
        role = self.session.scalar(
            select(Role).where(
                Role.scope == scope,
                Role.name == name,
                Role.is_system.is_(True),
            )
        )
        if role is None:
            raise AuthValidationError(f"system role '{scope.value}:{name}' is missing")
        return role

    def _issue_token(
        self,
        *,
        principal_type: Literal["user", "service_principal"],
        principal_id: str,
        token_kind: Literal["operator", "service"],
        expires_in_seconds: int,
    ) -> IssuedToken:
        issued_at = utc_now()
        expires_at = issued_at + timedelta(seconds=expires_in_seconds)
        payload = {
            "v": 1,
            "principal_type": principal_type,
            "principal_id": principal_id,
            "token_kind": token_kind,
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        access_token = self._encode_development_token(payload)
        return IssuedToken(
            access_token=access_token,
            token_type=TOKEN_TYPE_BEARER,
            expires_at=expires_at,
        )

    def _encode_development_token(self, payload: dict[str, object]) -> str:
        payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        payload_part = self._b64_encode(payload_bytes)
        signature = hmac.new(
            self.settings.dev_signing_secret.encode("utf-8"),
            payload_part.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature_part = self._b64_encode(signature)
        return f"acp1.{payload_part}.{signature_part}"

    def _decode_development_token(self, token: str) -> dict[str, object]:
        parts = token.split(".")
        if len(parts) != 3 or parts[0] != "acp1":
            raise AuthenticationError("bearer token format is invalid")

        payload_part = parts[1]
        signature_part = parts[2]
        expected_signature = hmac.new(
            self.settings.dev_signing_secret.encode("utf-8"),
            payload_part.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        provided_signature = self._b64_decode(signature_part)
        if not hmac.compare_digest(expected_signature, provided_signature):
            raise AuthenticationError("bearer token signature is invalid")

        try:
            payload = json.loads(self._b64_decode(payload_part).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AuthenticationError("bearer token payload is invalid") from exc

        if not isinstance(payload, dict):
            raise AuthenticationError("bearer token payload is invalid")
        if payload.get("exp") is None or payload.get("iat") is None:
            raise AuthenticationError("bearer token is missing expiry metadata")
        if utc_now().timestamp() >= int(payload["exp"]):
            raise AuthenticationError("bearer token has expired")
        return payload

    def verify_oidc_token(self, bearer_token: str) -> dict[str, object]:
        """Verify a JWT bearer token against the configured OIDC issuer's JWKS.

        This is the B6 production identity path. The token must be a JWT
        signed by the issuer referenced by ``settings.oidc_issuer_url``. The
        signature is verified against the issuer's published JWKS, and the
        ``iss``, ``aud``, and ``exp`` claims are validated.

        Returns the decoded JWT payload (claims) on success and raises
        ``AuthenticationError`` on any verification failure.

        This method is safe to call in any environment, but production
        deployments MUST configure ``oidc_issuer_url``/``oidc_client_id``
        (enforced by ``app.config.Settings``).
        """
        if not self.settings.oidc_issuer_url.strip():
            raise AuthenticationError(
                "OIDC token verification requires oidc_issuer_url to be configured"
            )
        return _verify_oidc_jwt(
            bearer_token,
            issuer=self.settings.oidc_issuer_url,
            audience=self.settings.oidc_client_id,
        )

    def _authenticate_external_managed_bearer(
        self,
        bearer_token: str,
    ) -> AuthenticatedSession:
        # B6: route external_managed_bearer through the OIDC verifier. The
        # JWT's signature is checked against the issuer's JWKS, and iss/aud/exp
        # are validated. The principal is then resolved from the ``sub`` claim.
        claims = self.verify_oidc_token(bearer_token)
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise AuthenticationError("OIDC token is missing a subject claim")

        issued_at_raw = claims.get("iat")
        expires_at_raw = claims.get("exp")
        issued_at = (
            datetime.fromtimestamp(int(issued_at_raw), tz=UTC)
            if isinstance(issued_at_raw, (int, float))
            else utc_now()
        )
        expires_at = (
            datetime.fromtimestamp(int(expires_at_raw), tz=UTC)
            if isinstance(expires_at_raw, (int, float))
            else issued_at + timedelta(seconds=self.settings.auth_operator_token_ttl_seconds)
        )

        # Resolve a local principal that matches the OIDC subject. The cloud
        # schema stores the OIDC subject on User.identity_provider_subject.
        user = self.session.scalar(
            select(User).where(User.identity_provider_subject == subject)
        )
        if user is not None and user.status == UserStatus.active:
            return self._session_for_user(
                user_id=user.user_id,
                issued_at=issued_at,
                expires_at=expires_at,
            )
        # Fall back to a service principal keyed on the same subject.
        principal = self.session.scalar(
            select(ServicePrincipal).where(
                ServicePrincipal.auth_metadata.op("->>")("oidc_sub") == subject
            )
        )
        if principal is not None and principal.status == ServicePrincipalStatus.active:
            return self._session_for_service_principal(
                service_principal_id=principal.service_principal_id,
                issued_at=issued_at,
                expires_at=expires_at,
            )
        raise AuthenticationError(
            f"OIDC subject '{subject}' is not mapped to an active cloud principal"
        )

    def _ensure_development_auth_enabled(self) -> None:
        if self.settings.auth_mode != AUTH_MODE_DEVELOPMENT_SIGNED_BEARER:
            raise AuthValidationError(
                "development token issuance endpoints are unavailable when "
                f"auth_mode={self.settings.auth_mode}; "
                f"{self._external_managed_bearer_upgrade_hint()}"
            )
        if self.settings.environment not in {"local", "test"}:
            raise AuthValidationError(
                "development bearer token issuance is only enabled in local and test"
            )

    @staticmethod
    def _external_managed_bearer_upgrade_hint() -> str:
        return (
            "integrate managed operator and service bearer validation before using "
            "this mode in a hosted environment"
        )

    @staticmethod
    def _role_key(*, scope: RoleScope, name: str, tenant_id: str | None) -> str:
        normalized_name = name.strip().lower().replace(" ", "_")
        tenant_segment = tenant_id or "_global"
        return f"{scope.value}:{tenant_segment}:{normalized_name}"

    @staticmethod
    def _service_principal_key(*, tenant_id: str | None, display_name: str) -> str:
        normalized_name = display_name.strip().lower().replace(" ", "_")
        scope_segment = tenant_id or "_platform"
        return f"{scope_segment}:{normalized_name}"

    @staticmethod
    def _normalize_email(email: str) -> str:
        normalized = email.strip().lower()
        if not normalized or "@" not in normalized:
            raise AuthValidationError("email must be a valid-looking address")
        return normalized

    @staticmethod
    def _b64_encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")

    @staticmethod
    def _b64_decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)


def tenant_id_from_policy(policy: Policy) -> str:
    return policy.tenant_id


def tenant_id_from_action_intent(record: ActionIntentRecord) -> str:
    return record.tenant_id


def tenant_id_from_receipt(record: ReceiptRecord) -> str:
    return record.tenant_id


def tenant_id_from_audit_event(event: AuditEvent) -> str:
    return event.tenant_id


def tenant_id_from_reconciliation(record: ReconciliationRecord) -> str:
    return record.tenant_id


def tenant_id_from_evidence(record: EvidenceObject) -> str:
    return record.tenant_id


def tenant_id_from_issued_proof(record: IssuedProof) -> str:
    return record.tenant_id


def tenant_id_from_escrow_record(record: EscrowRecord) -> str:
    return record.tenant_id


def tenant_id_from_signing_key(record: SigningKeyReference) -> str:
    return record.tenant_id


# ---------------------------------------------------------------------------
# B6: OIDC token verification (production identity path)
# ---------------------------------------------------------------------------

OIDC_JWKS_CACHE_TTL_SECONDS = 300


@dataclass
class _CachedJwks:
    keys_by_kid: dict[str, dict[str, Any]]
    fetched_at: datetime
    ttl_seconds: int = OIDC_JWKS_CACHE_TTL_SECONDS


_jwks_cache: dict[str, _CachedJwks] = {}
_jwks_cache_lock = threading.Lock()


def _oidc_b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def reset_oidc_jwks_cache() -> None:
    """Clear the in-memory JWKS cache. Exposed for tests and operational reset."""
    with _jwks_cache_lock:
        _jwks_cache.clear()


def _fetch_oidc_jwks(issuer_url: str) -> dict[str, dict[str, Any]]:
    """Fetch and cache the OIDC issuer's JWKS, keyed by ``kid``.

    Discovery follows the standard OIDC well-known path
    ``{issuer}/.well-known/openid-configuration`` to resolve ``jwks_uri``.
    The fetched key set is cached in-memory for ``OIDC_JWKS_CACHE_TTL_SECONDS``
    seconds to avoid re-fetching on every request.
    """
    now = utc_now()
    with _jwks_cache_lock:
        cached = _jwks_cache.get(issuer_url)
        if cached is not None and (now - cached.fetched_at).total_seconds() < cached.ttl_seconds:
            return cached.keys_by_kid

    import httpx

    config_url = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"
    config_response = httpx.get(config_url, timeout=10.0)
    config_response.raise_for_status()
    config_doc = config_response.json()
    jwks_uri = config_doc.get("jwks_uri")
    if not isinstance(jwks_uri, str) or not jwks_uri:
        raise AuthenticationError(
            f"OIDC issuer '{issuer_url}' did not advertise a jwks_uri"
        )
    jwks_response = httpx.get(jwks_uri, timeout=10.0)
    jwks_response.raise_for_status()
    jwks_doc = jwks_response.json()
    keys_list = jwks_doc.get("keys") or []
    if not isinstance(keys_list, list):
        raise AuthenticationError(
            f"OIDC issuer '{issuer_url}' returned a malformed JWKS document"
        )
    keys_by_kid: dict[str, dict[str, Any]] = {}
    for key in keys_list:
        if not isinstance(key, dict):
            continue
        kid = key.get("kid")
        if isinstance(kid, str) and kid:
            keys_by_kid[kid] = key
    with _jwks_cache_lock:
        _jwks_cache[issuer_url] = _CachedJwks(
            keys_by_kid=keys_by_kid,
            fetched_at=now,
        )
    return keys_by_kid


def _jwk_to_public_key(jwk: dict[str, Any]):
    """Materialize a cryptography public key from a JWK dict."""
    from cryptography.hazmat.primitives.asymmetric import ed25519, rsa

    kty = jwk.get("kty")
    if kty == "RSA":
        n = int.from_bytes(_oidc_b64url_decode(jwk["n"]), "big")
        e = int.from_bytes(_oidc_b64url_decode(jwk["e"]), "big")
        return rsa.RSAPublicNumbers(e=e, n=n).public_key()
    if kty == "OKP" and jwk.get("crv") == "Ed25519":
        x = _oidc_b64url_decode(jwk["x"])
        return ed25519.Ed25519PublicKey.from_public_bytes(x)
    raise AuthenticationError(
        f"unsupported OIDC JWK kty/crv: {kty}/{jwk.get('crv')}"
    )


def _verify_oidc_jwt(
    token: str,
    *,
    issuer: str,
    audience: str,
) -> dict[str, object]:
    """Verify a JWT against the OIDC issuer's JWKS and validate its claims.

    Returns the decoded payload on success; raises ``AuthenticationError`` on
    any signature, issuer, audience, or expiry failure.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthenticationError("OIDC token must be a JWT with three segments")
    header_b64, payload_b64, signature_b64 = parts
    try:
        header = json.loads(_oidc_b64url_decode(header_b64))
        payload = json.loads(_oidc_b64url_decode(payload_b64))
        signature = _oidc_b64url_decode(signature_b64)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise AuthenticationError("OIDC token segments are malformed") from exc
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise AuthenticationError("OIDC token segments must be JSON objects")

    alg = header.get("alg")
    kid = header.get("kid")
    if not isinstance(alg, str) or not isinstance(kid, str) or not alg or not kid:
        raise AuthenticationError("OIDC token header must declare alg and kid")

    keys = _fetch_oidc_jwks(issuer)
    jwk = keys.get(kid)
    if jwk is None:
        raise AuthenticationError(
            f"OIDC token kid '{kid}' not found in issuer JWKS"
        )
    public_key = _jwk_to_public_key(jwk)

    signing_input = f"{header_b64}.{payload_b64}".encode()
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec, padding

        if alg == "RS256":
            public_key.verify(
                signature, signing_input, padding.PKCS1v15(), hashes.SHA256()
            )
        elif alg == "EdDSA":
            public_key.verify(signature, signing_input)
        elif alg == "ES256":
            public_key.verify(signature, signing_input, ec.ECDSA(hashes.SHA256()))
        else:
            raise AuthenticationError(f"unsupported OIDC token alg '{alg}'")
    except InvalidSignature as exc:
        raise AuthenticationError("OIDC token signature is invalid") from exc

    if payload.get("iss") != issuer:
        raise AuthenticationError(
            "OIDC token iss claim does not match the configured issuer"
        )
    aud_claim = payload.get("aud")
    aud_match = (
        aud_claim == audience
        or (isinstance(aud_claim, list) and audience in aud_claim)
    )
    if audience and not aud_match:
        raise AuthenticationError(
            "OIDC token aud claim does not include the configured client id"
        )
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)) or utc_now().timestamp() >= int(exp):
        raise AuthenticationError("OIDC token has expired or is missing exp")
    return payload
