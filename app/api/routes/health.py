from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.dependencies import get_container, get_settings
from app.config import Settings
from app.container import ApplicationContainer

router = APIRouter()


class LivenessResponse(BaseModel):
    status: Literal["ok"]
    service: str
    environment: str
    version: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    service: str
    environment: str
    checks: dict[str, Literal["ready", "not_ready"]]
    details: dict[str, str]


@router.get("/live", response_model=LivenessResponse)
def get_liveness(
    settings: Annotated[Settings, Depends(get_settings)],
) -> LivenessResponse:
    return LivenessResponse(
        status="ok",
        service=settings.service_slug,
        environment=settings.environment,
        version=settings.version,
    )


@router.get("/ready", response_model=ReadinessResponse)
def get_readiness(
    container: Annotated[ApplicationContainer, Depends(get_container)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    readiness_checks = container.readiness_checks()
    checks = {
        name: check.status
        for name, check in readiness_checks.items()
    }
    details = {
        name: check.detail
        for name, check in readiness_checks.items()
    }
    all_checks_ready = all(
        check.status == "ready"
        for check in readiness_checks.values()
    )
    overall_status: Literal["ready", "not_ready"] = "ready" if all_checks_ready else "not_ready"
    payload = ReadinessResponse(
        status=overall_status,
        service=settings.service_slug,
        environment=settings.environment,
        checks=checks,
        details=details,
    )
    status_code = (
        status.HTTP_200_OK
        if overall_status == "ready"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())
