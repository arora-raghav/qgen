"""
Admin routes — no-op stub for QGen OSS local mode.
The admin invite system is not needed when there is no auth.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/health")
async def admin_health():
    """Admin health check."""
    return {"status": "ok", "mode": "local"}
