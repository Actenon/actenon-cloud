from fastapi import APIRouter

from app.api.action_intents import router as action_intents_router
from app.api.admin import router as admin_router
from app.api.approvals import router as approvals_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.escrow import router as escrow_router
from app.api.evidence import router as evidence_router
from app.api.intents import router as intents_router
from app.api.issuance import router as issuance_router
from app.api.issuer_registry import router as issuer_registry_router
from app.api.policies import router as policies_router
from app.api.receipts import router as receipts_router
from app.api.routes.health import router as health_router
from app.api.tenants import router as tenants_router
from app.api.transparency import router as transparency_router
from app.api.usage import router as usage_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(tenants_router)
api_router.include_router(policies_router)
api_router.include_router(action_intents_router)
api_router.include_router(approvals_router)
api_router.include_router(evidence_router)
api_router.include_router(intents_router)
api_router.include_router(issuance_router)
api_router.include_router(escrow_router)
api_router.include_router(receipts_router)
api_router.include_router(transparency_router)
api_router.include_router(issuer_registry_router)
api_router.include_router(audit_router)
api_router.include_router(usage_router)
