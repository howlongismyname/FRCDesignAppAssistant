"""Design Assistant Application Package.

This package contains the complete Design Assistant application built using
Hexagonal Architecture (Ports and Adapters pattern).

The application is organized into the following layers:
- Domain: Business logic and domain models
- Application: Use cases, commands, and services
- Adapters: External system integrations
- Infrastructure: Cross-cutting concerns (config, auth, logging)
- Interfaces: API endpoints and web framework integration
"""

from .infrastructure.config import DesignAssistantConfig, get_config, set_config
from .infrastructure.logging import setup_logging, get_logger
from .interfaces.api import create_design_assistant_router

__version__ = "1.0.0"
__author__ = "Design Assistant Team"

__all__ = [
    "DesignAssistantConfig",
    "get_config", 
    "set_config",
    "setup_logging",
    "get_logger",
    "create_design_assistant_router"
]