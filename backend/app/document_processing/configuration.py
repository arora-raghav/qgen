"""
Configuration module for enhanced processing features.
Maintains compatibility with CLI evolution agents.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Configuration compatible with CLI evolution agents
CONFIGURATION = {
    "rows_per_context": int(os.getenv("ROWS_PER_CONTEXT", "5")),
    "evolution_depth": int(os.getenv("EVOLUTION_DEPTH", "1")),
}

def get_configuration():
    """Get the current configuration."""
    return CONFIGURATION

def update_configuration(key: str, value):
    """Update configuration value."""
    CONFIGURATION[key] = value