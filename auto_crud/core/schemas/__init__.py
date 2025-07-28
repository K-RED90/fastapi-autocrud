"""
FastAPI-AutoCRUD Schema Module

This module contains schema definitions for pagination, filtering,
and other data structures used by FastAPI-AutoCRUD.
"""

from .pagination import BulkResponse, FilterParam, PaginatedResponse

__all__ = [
    "BulkResponse",
    "FilterParam", 
    "PaginatedResponse",
] 