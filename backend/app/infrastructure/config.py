"""Configuration management for the Design Assistant."""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class OnshapeConfig:
    """Configuration for Onshape API."""
    
    base_url: str = "https://cad.onshape.com"
    access_key: str = ""
    secret_key: str = ""
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_per_second: float = 10.0
    
    # Storage configuration
    structured_storage_element_id: str = ""
    blob_storage_element_id: str = ""
    
    @classmethod
    def from_env(cls) -> "OnshapeConfig":
        """Create configuration from environment variables."""
        return cls(
            base_url=os.getenv("ONSHAPE_BASE_URL", "https://cad.onshape.com"),
            access_key=os.getenv("ONSHAPE_ACCESS_KEY", ""),
            secret_key=os.getenv("ONSHAPE_SECRET_KEY", ""),
            timeout=int(os.getenv("ONSHAPE_TIMEOUT", "30")),
            max_retries=int(os.getenv("ONSHAPE_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("ONSHAPE_RETRY_DELAY", "1.0")),
            rate_limit_per_second=float(os.getenv("ONSHAPE_RATE_LIMIT", "10.0")),
            structured_storage_element_id=os.getenv("ONSHAPE_STRUCTURED_STORAGE_ID", ""),
            blob_storage_element_id=os.getenv("ONSHAPE_BLOB_STORAGE_ID", "")
        )


@dataclass
class CacheConfig:
    """Configuration for caching."""
    
    type: str = "memory"  # memory, redis, tiered
    redis_url: str = "redis://localhost:6379"
    redis_prefix: str = "design_assistant:"
    default_ttl: int = 3600
    max_memory_size: int = 1000
    max_redis_connections: int = 10
    
    @classmethod
    def from_env(cls) -> "CacheConfig":
        """Create configuration from environment variables."""
        return cls(
            type=os.getenv("CACHE_TYPE", "memory"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            redis_prefix=os.getenv("CACHE_PREFIX", "design_assistant:"),
            default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "3600")),
            max_memory_size=int(os.getenv("CACHE_MAX_MEMORY_SIZE", "1000")),
            max_redis_connections=int(os.getenv("CACHE_MAX_CONNECTIONS", "10"))
        )


@dataclass
class DatabaseConfig:
    """Configuration for database (if needed)."""
    
    url: str = "sqlite:///./design_assistant.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create configuration from environment variables."""
        return cls(
            url=os.getenv("DATABASE_URL", "sqlite:///./design_assistant.db"),
            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
            pool_size=int(os.getenv("DATABASE_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))
        )


@dataclass
class NotificationConfig:
    """Configuration for notifications."""
    
    enabled: bool = True
    webhook_urls: List[str] = field(default_factory=list)
    slack_webhook_url: str = ""
    slack_channel: str = "#general"
    email_enabled: bool = False
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str = ""
    to_emails: List[str] = field(default_factory=list)
    
    @classmethod
    def from_env(cls) -> "NotificationConfig":
        """Create configuration from environment variables."""
        webhook_urls = []
        webhook_urls_str = os.getenv("WEBHOOK_URLS", "")
        if webhook_urls_str:
            webhook_urls = [url.strip() for url in webhook_urls_str.split(",")]
        
        to_emails = []
        to_emails_str = os.getenv("NOTIFICATION_TO_EMAILS", "")
        if to_emails_str:
            to_emails = [email.strip() for email in to_emails_str.split(",")]
        
        return cls(
            enabled=os.getenv("NOTIFICATIONS_ENABLED", "true").lower() == "true",
            webhook_urls=webhook_urls,
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", ""),
            slack_channel=os.getenv("SLACK_CHANNEL", "#general"),
            email_enabled=os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "false").lower() == "true",
            smtp_server=os.getenv("SMTP_SERVER", ""),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            from_email=os.getenv("FROM_EMAIL", ""),
            to_emails=to_emails
        )


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_enabled: bool = True
    
    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """Create configuration from environment variables."""
        return cls(
            level=os.getenv("LOG_LEVEL", "INFO").upper(),
            format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            file=os.getenv("LOG_FILE"),
            max_bytes=int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024))),
            backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
            console_enabled=os.getenv("LOG_CONSOLE", "true").lower() == "true"
        )


@dataclass
class SecurityConfig:
    """Configuration for security settings."""
    
    api_key: str = ""
    jwt_secret: str = ""
    jwt_expiry_hours: int = 24
    cors_origins: List[str] = field(default_factory=list)
    allowed_hosts: List[str] = field(default_factory=list)
    rate_limit_per_minute: int = 60
    
    @classmethod
    def from_env(cls) -> "SecurityConfig":
        """Create configuration from environment variables."""
        cors_origins = []
        cors_origins_str = os.getenv("CORS_ORIGINS", "")
        if cors_origins_str:
            cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]
        
        allowed_hosts = []
        allowed_hosts_str = os.getenv("ALLOWED_HOSTS", "")
        if allowed_hosts_str:
            allowed_hosts = [host.strip() for host in allowed_hosts_str.split(",")]
        
        return cls(
            api_key=os.getenv("API_KEY", ""),
            jwt_secret=os.getenv("JWT_SECRET", ""),
            jwt_expiry_hours=int(os.getenv("JWT_EXPIRY_HOURS", "24")),
            cors_origins=cors_origins,
            allowed_hosts=allowed_hosts,
            rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        )


@dataclass
class DesignAssistantConfig:
    """Main configuration class for the Design Assistant."""
    
    # Environment
    environment: str = "development"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Sub-configurations
    onshape: OnshapeConfig = field(default_factory=OnshapeConfig)
    cache: CacheConfig = field(default_factory=CacheConfig) 
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    
    # Processing settings
    max_concurrent_operations: int = 5
    default_batch_size: int = 10
    thumbnail_cache_ttl: int = 86400  # 24 hours
    bom_cache_ttl: int = 3600  # 1 hour
    
    @classmethod
    def from_env(cls) -> "DesignAssistantConfig":
        """Create configuration from environment variables."""
        return cls(
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            onshape=OnshapeConfig.from_env(),
            cache=CacheConfig.from_env(),
            database=DatabaseConfig.from_env(),
            notifications=NotificationConfig.from_env(),
            logging=LoggingConfig.from_env(),
            security=SecurityConfig.from_env(),
            max_concurrent_operations=int(os.getenv("MAX_CONCURRENT_OPS", "5")),
            default_batch_size=int(os.getenv("DEFAULT_BATCH_SIZE", "10")),
            thumbnail_cache_ttl=int(os.getenv("THUMBNAIL_CACHE_TTL", "86400")),
            bom_cache_ttl=int(os.getenv("BOM_CACHE_TTL", "3600"))
        )
    
    @classmethod
    def from_file(cls, config_path: str) -> "DesignAssistantConfig":
        """Load configuration from JSON file."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Create config with nested dataclasses
        return cls(
            environment=config_data.get("environment", "development"),
            debug=config_data.get("debug", False),
            host=config_data.get("host", "0.0.0.0"),
            port=config_data.get("port", 8000),
            onshape=OnshapeConfig(**config_data.get("onshape", {})),
            cache=CacheConfig(**config_data.get("cache", {})),
            database=DatabaseConfig(**config_data.get("database", {})),
            notifications=NotificationConfig(**config_data.get("notifications", {})),
            logging=LoggingConfig(**config_data.get("logging", {})),
            security=SecurityConfig(**config_data.get("security", {})),
            max_concurrent_operations=config_data.get("max_concurrent_operations", 5),
            default_batch_size=config_data.get("default_batch_size", 10),
            thumbnail_cache_ttl=config_data.get("thumbnail_cache_ttl", 86400),
            bom_cache_ttl=config_data.get("bom_cache_ttl", 3600)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "environment": self.environment,
            "debug": self.debug,
            "host": self.host,
            "port": self.port,
            "onshape": {
                "base_url": self.onshape.base_url,
                "timeout": self.onshape.timeout,
                "max_retries": self.onshape.max_retries,
                "retry_delay": self.onshape.retry_delay,
                "rate_limit_per_second": self.onshape.rate_limit_per_second,
                # Don't include sensitive keys in dict representation
            },
            "cache": {
                "type": self.cache.type,
                "default_ttl": self.cache.default_ttl,
                "max_memory_size": self.cache.max_memory_size,
            },
            "notifications": {
                "enabled": self.notifications.enabled,
                "webhook_count": len(self.notifications.webhook_urls),
                "slack_enabled": bool(self.notifications.slack_webhook_url),
                "email_enabled": self.notifications.email_enabled,
            },
            "processing": {
                "max_concurrent_operations": self.max_concurrent_operations,
                "default_batch_size": self.default_batch_size,
                "thumbnail_cache_ttl": self.thumbnail_cache_ttl,
                "bom_cache_ttl": self.bom_cache_ttl,
            }
        }
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate Onshape configuration
        if not self.onshape.access_key:
            errors.append("Onshape access key is required")
        if not self.onshape.secret_key:
            errors.append("Onshape secret key is required")
        if not self.onshape.structured_storage_element_id:
            errors.append("Onshape structured storage element ID is required")
        if not self.onshape.blob_storage_element_id:
            errors.append("Onshape blob storage element ID is required")
        
        # Validate cache configuration
        if self.cache.type not in ("memory", "redis", "tiered"):
            errors.append("Cache type must be 'memory', 'redis', or 'tiered'")
        
        # Validate ports and timeouts
        if self.port < 1 or self.port > 65535:
            errors.append("Port must be between 1 and 65535")
        if self.onshape.timeout <= 0:
            errors.append("Onshape timeout must be positive")
        
        return errors
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


# Global configuration instance
_config: Optional[DesignAssistantConfig] = None


def get_config() -> DesignAssistantConfig:
    """Get the global configuration instance."""
    global _config
    
    if _config is None:
        # Try to load from file first, then environment
        config_file = os.getenv("CONFIG_FILE", "./config.json")
        
        if os.path.exists(config_file):
            _config = DesignAssistantConfig.from_file(config_file)
        else:
            _config = DesignAssistantConfig.from_env()
    
    return _config


def set_config(config: DesignAssistantConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


def reload_config() -> DesignAssistantConfig:
    """Reload configuration from environment/file."""
    global _config
    _config = None
    return get_config()