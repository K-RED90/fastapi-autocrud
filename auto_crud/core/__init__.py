"""
FastAPI-AutoCRUD Core Module

This module contains the core functionality of FastAPI-AutoCRUD including
CRUD operations, router factory, filters, and error handling.
"""

# Core CRUD functionality
from .crud import BaseCRUD, RouterFactory
from .crud.decorators import action

# Error handling
from .errors import (
    AutoCRUDException,
    ConfigurationError,
    FilterError,
    NotFoundError,
    PermissionError,
    ValidationError,
)

# Schema utilities
from .schemas.pagination import BulkResponse, FilterParam, PaginatedResponse

__all__ = [
    # CRUD
    "BaseCRUD",
    "RouterFactory", 
    "action",
    # Errors
    "AutoCRUDException",
    "ValidationError",
    "NotFoundError",
    "PermissionError",
    "ConfigurationError",
    "FilterError",
    # Schemas
    "PaginatedResponse",
    "BulkResponse",
    "FilterParam",
] 