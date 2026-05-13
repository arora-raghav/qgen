"""
No-auth document user for QGen OSS (local mode).
Returns a fixed 'local' user — no JWT, no Supabase.
"""

from typing import Optional
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


class DocumentUser:
    """Document workspace user (local/no-auth mode)."""

    def __init__(self):
        self.user_id           = "local"
        self.email             = "local@qgen.app"
        self.is_invited        = True           # full access in local mode
        self.subscription_tier = "enterprise"   # no limits locally
        self.user_metadata     = {}


_LOCAL_USER = DocumentUser()


async def get_document_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> DocumentUser:
    """Always returns the local user — no authentication required."""
    return _LOCAL_USER


async def check_document_limits(user: DocumentUser, pages: int = 0, mb: float = 0.0) -> dict:
    """No limits in local mode."""
    return {
        "within_limits": True,
        "pages_remaining": 99999,
        "mb_remaining": 99999.0,
        "user_tier": user.subscription_tier,
    }
