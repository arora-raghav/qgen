from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
import os
import logging

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

logger = logging.getLogger(__name__)

# Standard path for secret files on Render
RENDER_SECRET_FILE_PATH = "/etc/secrets/tokens.txt" 
# Path for local development (assuming tokens.txt is in the project root)
LOCAL_DEV_TOKEN_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tokens.txt")

def load_valid_tokens():
    """
    Loads valid API tokens.
    Prioritizes Render's secret file path, then falls back to local dev path.
    Parses tokens, ignoring comments starting with '#'.
    """
    tokens = set()
    paths_to_try = [RENDER_SECRET_FILE_PATH, LOCAL_DEV_TOKEN_FILE_PATH]
    loaded_path = None

    for path in paths_to_try:
        try:
            with open(path, "r") as f:
                for line in f:
                    token_part = line.split('#', 1)[0].strip() # Get part before first '#'
                    if token_part: # Ensure it's not an empty line or just a comment
                        tokens.add(token_part)
                loaded_path = path
                logger.info(f"Successfully loaded tokens from: {loaded_path}")
                break # Stop if tokens are loaded from a path
        except FileNotFoundError:
            logger.warning(f"Token file not found at: {path}. Trying next path if available.")
            continue
    if not tokens:
        logger.warning("No API tokens loaded from any specified path. API key authentication might not be active or configured.")
    return tokens

VALID_API_KEYS = load_valid_tokens()

async def get_api_key(api_key: str = Security(api_key_header)):
    if not VALID_API_KEYS: # If no tokens are loaded at all
        raise HTTPException(
            # Consider logging this as a server-side error as well if it occurs in production
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key authentication is not configured on the server."
        )
    if api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
    return api_key
