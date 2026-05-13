"""
Enhanced processing configuration module.
Handles feature flags and settings for RAG context and dataset evolution.
"""

import os
from typing import Optional
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class EnhancedConfig:
    """Configuration for enhanced processing features."""
    
    def __init__(self):
        self.enabled = self._get_bool_env('ENABLE_ENHANCED_PROCESSING', False)
        self.evolution_depth = self._get_int_env('EVOLUTION_DEPTH', 1)
        
        if self.enabled:
            logger.info("🚀 Enhanced processing features ENABLED")
            logger.info(f"   Evolution depth: {self.evolution_depth}")
        else:
            logger.info("📝 Enhanced processing features DISABLED - using standard workflow")
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean environment variable."""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def _get_int_env(self, key: str, default: int) -> int:
        """Get integer environment variable with validation."""
        try:
            value = int(os.getenv(key, str(default)))
            # Validate evolution depth range
            if key == 'EVOLUTION_DEPTH':
                value = max(1, min(5, value))  # Clamp between 1-5
            return value
        except ValueError:
            logger.warning(f"Invalid {key} value, using default: {default}")
            return default
    
    @property
    def is_enabled(self) -> bool:
        """Check if enhanced processing is enabled."""
        return self.enabled
    
    @property
    def should_use_rag(self) -> bool:
        """Check if RAG context assembly should be used."""
        return self.enabled
    
    @property
    def should_evolve_datasets(self) -> bool:
        """Check if dataset evolution should be applied."""
        return self.enabled and self.evolution_depth > 0

# Global configuration instance
enhanced_config = EnhancedConfig()

def get_enhanced_config() -> EnhancedConfig:
    """Get the global enhanced configuration instance."""
    return enhanced_config

def log_processing_mode(context: str = ""):
    """Log the current processing mode for debugging."""
    config = get_enhanced_config()
    if config.is_enabled:
        logger.info(f"🎯 {context} - Enhanced mode: RAG context + Evolution (depth: {config.evolution_depth})")
    else:
        logger.info(f"📝 {context} - Standard mode: No RAG context or evolution")

def log_rag_fallback(reason: str, context: str = ""):
    """Log when RAG processing falls back to standard mode."""
    logger.warning(f"⚠️  {context} - RAG context unavailable: {reason}")
    logger.warning(f"   Falling back to standard processing without semantic similarity")