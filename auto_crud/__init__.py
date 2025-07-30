"""
FastAPI-AutoCRUD - Sophisticated FastAPI CRUD Router Factory

A powerful, enterprise-level FastAPI CRUD router factory that automatically generates
REST endpoints with advanced features like filtering, pagination, searching, sorting,
bulk operations, and custom endpoint decorators.
"""

__version__ = "0.1.5"
__author__ = "FastAPI-AutoCRUD Contributors"

# Core imports
from .core.crud.base import BaseCRUD, CRUDHooks
from .core.crud.decorators import action
from .core.crud.router import RouterFactory
from .core.crud.types import CreateSchemaType, ModelType, UpdateSchemaType

# Error imports
from .core.errors import (
    AutoCRUDException,
    ConfigurationError,
    FilterError,
    NotFoundError,
    PermissionError,
    ValidationError,
)

# Schema imports
from .core.schemas.pagination import (
    BulkResponse,
    FilterParam,
    PaginatedResponse,
    # QueryParams,
)

# Dependencies
from .dependencies.page_param import PageParams

__all__ = [
    # Core classes
    "BaseCRUD",
    "RouterFactory",
    "CRUDHooks",
    "action",
    # Types
    "ModelType",
    "CreateSchemaType",
    "UpdateSchemaType",
    "FilterParam",
    # Schemas
    "PaginatedResponse",
    "BulkResponse",
    # Errors
    "AutoCRUDException",
    "ValidationError",
    "NotFoundError",
    "PermissionError",
    "ConfigurationError",
    "FilterError",
    # Dependencies
    "PageParams",
    # Metadata
    "__version__",
    "__author__",
]
