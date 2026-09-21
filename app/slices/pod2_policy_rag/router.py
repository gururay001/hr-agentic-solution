"""Isolated FastAPI Router for pod2_policy_rag — auto-mounted by app/fast_api_app.py."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.contracts import EmployeeContext, get_employee_context
from app.slices.pod2_policy_rag.sub_agent import search_hr_policy
from app.slices.pod2_policy_rag.webhook_ingest import (
    PolicyPublishPayload,
    ingest_published_policy,
)

router = APIRouter(tags=["pod2_policy_rag"])


class PolicySearchRequest(BaseModel):
    """Request payload for `POST /api/v1/pod2_policy_rag/search`."""

    query: str


@router.get("/api/v1/pod2_policy_rag/status")
async def pod_status() -> dict[str, str]:
    """Independent health check for pod2_policy_rag."""
    return {"pod": "pod2_policy_rag", "status": "READY"}


@router.post("/api/v1/pod2_policy_rag/search")
async def search_policy_endpoint(
    request: PolicySearchRequest,
    ctx: EmployeeContext = Depends(get_employee_context),  # noqa: B008
) -> dict[str, Any]:
    """Executes `<2ms` entitlement-filtered hybrid Policy RAG for the authenticated employee."""
    return await search_hr_policy(
        query=request.query,
        country_code=ctx.country_code,
        role=ctx.role,
    )


@router.post("/api/v1/webhooks/policy-publish")
@router.post("/api/v1/pod2_policy_rag/webhooks/policy-publish")
async def policy_publish_webhook(payload: PolicyPublishPayload) -> dict[str, Any]:
    """SLA-01: `<= 60 Seconds` HR policy incremental chunking and Redis cache eviction webhook."""
    return await ingest_published_policy(payload)
