"""Redirected to local_db.py — no Supabase in QGen OSS."""
from .local_db import (  # noqa: F401
    LocalClient as Client,
    LocalSupabaseService as SupabaseService,
    supabase_service,
    supabase,
    get_supabase_client,
)
import logging
logger = logging.getLogger(__name__)

SUPABASE_URL = None
SUPABASE_ANON_KEY = None
SUPABASE_SERVICE_ROLE_KEY = None
