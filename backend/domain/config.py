"""Configuration settings for BOM processing and design assistant."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class BomConfig:
    """Configuration for BOM processing operations."""
    
    # Rate limiting
    refresh_cooldown_seconds: int = 30
    
    # Cache timeouts
    bom_cache_hours: int = 24
    thumbnail_cache_hours: int = 24
    
    # Processing limits
    max_retries: int = 3
    batch_size: int = 10
    max_parts_per_bom: int = 10000
    
    # Database cleanup
    cleanup_batch_size: int = 500
    
    @classmethod
    def from_env(cls) -> 'BomConfig':
        """Create configuration from environment variables with fallback to defaults."""
        return cls(
            refresh_cooldown_seconds=int(os.getenv('BOM_REFRESH_COOLDOWN_SECONDS', 30)),
            bom_cache_hours=int(os.getenv('BOM_CACHE_HOURS', 24)),
            thumbnail_cache_hours=int(os.getenv('THUMBNAIL_CACHE_HOURS', 24)),
            max_retries=int(os.getenv('BOM_MAX_RETRIES', 3)),
            batch_size=int(os.getenv('BOM_BATCH_SIZE', 10)),
            max_parts_per_bom=int(os.getenv('BOM_MAX_PARTS', 10000)),
            cleanup_batch_size=int(os.getenv('BOM_CLEANUP_BATCH_SIZE', 500))
        )
    
    def validate(self) -> list[str]:
        """Validate configuration values and return list of error messages."""
        errors = []
        
        if self.refresh_cooldown_seconds < 0:
            errors.append("refresh_cooldown_seconds must be non-negative")
        
        if self.bom_cache_hours <= 0:
            errors.append("bom_cache_hours must be positive")
            
        if self.thumbnail_cache_hours <= 0:
            errors.append("thumbnail_cache_hours must be positive")
            
        if self.max_retries < 0:
            errors.append("max_retries must be non-negative")
            
        if self.batch_size <= 0:
            errors.append("batch_size must be positive")
            
        if self.max_parts_per_bom <= 0:
            errors.append("max_parts_per_bom must be positive")
            
        if self.cleanup_batch_size <= 0:
            errors.append("cleanup_batch_size must be positive")
            
        return errors


# Global configuration instance
_config: Optional[BomConfig] = None


def get_config() -> BomConfig:
    """Get global configuration instance (singleton pattern)."""
    global _config
    if _config is None:
        _config = BomConfig.from_env()
        
        # Validate configuration on first access
        errors = _config.validate()
        if errors:
            raise ValueError(f"Invalid BOM configuration: {', '.join(errors)}")
    
    return _config


def set_config(config: BomConfig) -> None:
    """Set global configuration instance (mainly for testing)."""
    global _config
    _config = config


def reset_config() -> None:
    """Reset configuration to reload from environment (mainly for testing)."""
    global _config
    _config = None