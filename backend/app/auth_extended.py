"""Extended authentication supporting both API keys and Supabase JWT tokens."""

from typing import Optional, Dict, Any, Union
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.api_key import APIKeyHeader
import os
import logging
from .supabase_client import supabase_service

# Existing API key setup
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)  # Made optional

# New JWT bearer setup
security = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)

# Load existing API keys (from original auth.py)
RENDER_SECRET_FILE_PATH = "/etc/secrets/tokens.txt" 
LOCAL_DEV_TOKEN_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tokens.txt")

def load_valid_tokens():
    """Load valid API tokens from file."""
    tokens = set()
    paths_to_try = [RENDER_SECRET_FILE_PATH, LOCAL_DEV_TOKEN_FILE_PATH]
    loaded_path = None

    for path in paths_to_try:
        try:
            with open(path, "r") as f:
                for line in f:
                    token_part = line.split('#', 1)[0].strip()
                    if token_part:
                        tokens.add(token_part)
                loaded_path = path
                logger.info(f"Successfully loaded tokens from: {loaded_path}")
                break
        except FileNotFoundError:
            logger.warning(f"Token file not found at: {path}. Trying next path if available.")
            continue
    
    if not tokens:
        logger.warning("No API tokens loaded from any specified path.")
    return tokens

VALID_API_KEYS = load_valid_tokens()

class AuthUser:
    """Authenticated user information."""
    
    def __init__(self, user_id: str, email: str, auth_type: str, subscription_tier: str = "free", 
                 user_metadata: Optional[Dict] = None):
        self.user_id = user_id
        self.email = email
        self.auth_type = auth_type  # "api_key" or "jwt"
        self.subscription_tier = subscription_tier
        self.user_metadata = user_metadata or {}

async def verify_api_key(api_key: Optional[str]) -> Optional[AuthUser]:
    """Verify API key and return API key user."""
    if not api_key:
        return None
    
    if not VALID_API_KEYS:
        return None
    
    if api_key in VALID_API_KEYS:
        # For API key users, we'll use a special user with elevated privileges
        return AuthUser(
            user_id="00000000-0000-0000-0000-000000000001",  # Fixed: Use valid UUID for API key users
            email="api@internal.com",
            auth_type="api_key",
            subscription_tier="enterprise"  # API key users get enterprise access
        )
    
    return None

async def verify_jwt_token(credentials: Optional[HTTPAuthorizationCredentials]) -> Optional[AuthUser]:
    """Verify JWT token and return user info."""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        user_info = await supabase_service.verify_user_token(token)
        
        if not user_info:
            return None
        
        # SIMPLIFIED: Skip user profile database operations that are causing RLS issues
        logger.info(f"JWT authenticated user: {user_info['id']} ({user_info.get('email')})")
        
        return AuthUser(
            user_id=user_info["id"],
            email=user_info["email"],
            auth_type="jwt",
            subscription_tier="free",  # Default tier for all JWT users
            user_metadata={"simplified": True, "verified": True}
        )
        
    except Exception as e:
        logger.error(f"JWT verification failed: {e}")
        return None

async def get_current_user(
    api_key: Optional[str] = Security(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> AuthUser:
    """
    Get current authenticated user from either API key or JWT token.
    Tries API key first, then JWT token.
    """
    # Try API key authentication first
    api_user = await verify_api_key(api_key)
    if api_user:
        return api_user
    
    # Try JWT authentication
    jwt_user = await verify_jwt_token(credentials)
    if jwt_user:
        return jwt_user
    
    # No valid authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

async def get_current_user_optional(
    api_key: Optional[str] = Security(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[AuthUser]:
    """
    Get current authenticated user optionally.
    Returns None if no valid authentication is provided.
    """
    try:
        return await get_current_user(api_key, credentials)
    except HTTPException:
        return None

async def check_user_limits(
    current_user: AuthUser = Depends(get_current_user),
    pages_to_process: int = 0,
    mb_to_process: float = 0.0
) -> Dict[str, Any]:
    """
    Check if the current user can process the requested amount of data.
    
    Args:
        current_user: Current authenticated user
        pages_to_process: Number of pages to process
        mb_to_process: Amount of data in MB to process
        
    Returns:
        Dict with limit check results
    """
    # API key users have unlimited access
    if current_user.auth_type == "api_key":
        return {"allowed": True, "reason": "API key user - unlimited access"}
    
    # Check Supabase user limits
    return await supabase_service.check_user_limits(
        current_user.user_id, 
        pages_to_process, 
        mb_to_process
    )

# Backwards compatibility - keep the original get_api_key function
async def get_api_key(api_key: str = Security(api_key_header)):
    """Original API key authentication function for backwards compatibility."""
    if not VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key authentication is not configured on the server."
        )
    if api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
    return api_key
