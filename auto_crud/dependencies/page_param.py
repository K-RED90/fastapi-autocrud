"""
Page parameter dependency for FastAPI-AutoCRUD.

This module provides the PageParams class that handles query parameters
for pagination, sorting, filtering, and search operations in FastAPI-AutoCRUD.
"""

import re
import uuid as _uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import Query

from ..core.errors import FilterError
from ..core.schemas.pagination import (
    FilterParam,
    # QueryParams,
)


class PageParams:
    """
    FastAPI dependency for handling page parameters in CRUD operations.

    This class provides a convenient way to parse and validate query parameters
    for pagination, sorting, filtering, and search operations. It automatically
    parses filter strings and converts them into structured filter objects.

    Attributes:
        page: Page number (1-based)
        size: Number of items per page
        sort_by: Sort field with optional direction prefix
        search: Global search term
        search_fields: List of fields to search in
        filters: Parsed filter parameters
    """

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(10, ge=1, le=100, description="Items per page"),
        sort_by: Optional[str] = Query(
            None,
            description="Sort by field (e.g., 'created_at', '-updated_at' for desc)",
        ),
        search: Optional[str] = Query(None, description="Global search term"),
        filters: Optional[str] = Query(
            None,
            description="""Filters in format. Operators: eq, ne, gt, ge, lt, le, in, 
            not_in, is_null, is_not_null, between, contains, startswith, endswith
            """,
            examples=[
                "status__eq=active",
                "status__in=active,pending",
                "created_at__gte=2024-01-01",
                "created_at__lte=2024-01-01",
                "created_at__between=2024-01-01,2024-01-02",
                "created_at__startswith=2024-01-01",
                "created_at__endswith=2024-01-01",
                "created_at__is_null=true",
                "created_at__is_not_null=false",
            ],
        ),
        allowed_filters: Any = Query(None, include_in_schema=False),
    ):
        """
        Initialize PageParams with query parameters.

        Args:
            page: Page number (1-based, minimum 1)
            size: Number of items per page (1-100)
            sort_by: Sort field with optional direction prefix
            search: Global search term
            search_fields: List of fields to search in
            filters: Filter string in format 'field__operator=value'

        Example:
            Client usage examples:
            GET /users?page=1&size=20
            GET /users?page=1&size=20&sort_by=created_at
            GET /users?page=1&size=20&sort_by=-created_at  (descending)
            GET /users?page=1&size=20&search=%john%
            GET /users?page=1&size=20&filters=status__eq=active,age__gte=18
            GET /users?page=1&size=20&filters=status__in=active,pending&sort_by=-created_at
            GET /users?page=1&size=20&filters=name__ilike=%john%,created_at__gte=2024-01-01
        """
        self.allowed_filters = allowed_filters

        self.page = page
        self.size = size
        self.sort_by = sort_by
        self.search = search
        self.filters = self._parse_filters(filters) if filters else []
        # Developer supplied filter specification for API-level enforcement.

    @property
    def offset(self) -> int:
        """
        Calculate the offset for database queries.

        Returns:
            The offset value for the current page and size
        """
        return (self.page - 1) * self.size

    def _parse_filters(self, filters_str: str) -> List[FilterParam]:
        """
        Parse filter string into structured filter objects.

        This method parses filter strings in the format 'field__operator=value'
        and converts them into structured filter objects that can be used
        for database queries.

        Args:
            filters_str: Filter string to parse

        Returns:
            Dictionary of parsed filters

        Raises:
            FilterError: If filter string is malformed or contains invalid operators

        Example:
            >>> params = PageParams()
            >>> filters = params._parse_filters("status__eq=active,age__gte=18")
            >>> print(filters)
            {'status': {'operator': 'eq', 'value': 'active'}, 'age': {'operator': 'ge', 'value': 18}}
        """
        if not filters_str:
            return []

        # Define canonical operators and aliases
        canonical_ops = {
            "eq",
            "ne",
            "gt",
            "ge",
            "lt",
            "le",
            "in",
            "not_in",
            "is_null",
            "is_not_null",
            "between",
            "contains",
            "startswith",
            "endswith",
        }

        alias_map = {
            "gte": "ge",
            "lte": "le",
            "==": "eq",
            "!=": "ne",
        }

        def _coerce_scalar(raw: str) -> Any:
            """
            Coerce a string value to the appropriate Python type.

            This function attempts to convert string values to appropriate
            Python types (int, float, bool, date, datetime, UUID) based
            on the string content.

            Args:
                raw: Raw string value to coerce

            Returns:
                Coerced value of appropriate type
            """
            raw_l = raw.lower()
            if raw_l == "null":
                return None
            if raw_l in {"true", "false"}:
                return raw_l == "true"
            if re.fullmatch(r"^-?\d+$", raw):
                return int(raw)
            if re.fullmatch(r"^-?\d+\.\d+$", raw):
                return float(raw)

            try:
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
                    return date.fromisoformat(raw)
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}T[\d:]+(?:\.\d+)?Z?", raw):
                    return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                pass

            try:
                return _uuid.UUID(raw)
            except ValueError:
                pass
            return raw

        # Parse filter string into parts, handling quoted values
        filter_parts: list[str] = []
        in_quotes = False
        start = 0
        i = 0
        length = len(filters_str)
        while i < length:
            ch = filters_str[i]
            if ch == '"' and (i == 0 or filters_str[i - 1] != "\\"):
                in_quotes = not in_quotes

            if ch == "," and not in_quotes:
                j = i + 1
                while j < length and filters_str[j] == " ":
                    j += 1

                next_eq = filters_str.find("=", j)
                next_comma = filters_str.find(",", j)

                if next_eq != -1 and (next_comma == -1 or next_eq < next_comma):
                    segment = filters_str[start:i].strip()
                    if segment:
                        filter_parts.append(segment)
                    start = i + 1
            i += 1

        last_seg = filters_str[start:].strip()
        if last_seg:
            filter_parts.append(last_seg)

        filters: Dict[str, Dict[str, Any]] = {}

        # Process each filter part
        for part in filter_parts:
            if "=" not in part:
                raise FilterError(f"Invalid filter segment '{part}'. Expected 'field__op=value'.")

            key, raw_value = part.split("=", 1)
            key = key.strip()
            raw_value = raw_value.strip()

            # Handle quoted values
            if raw_value.startswith('"') and raw_value.endswith('"'):
                raw_value = raw_value[1:-1]

            # Parse field and operator
            if "__" in key:
                field, op = key.rsplit("__", 1)
            else:
                field, op = key, "eq"

            op = alias_map.get(op.lower(), op.lower())

            if op not in canonical_ops:
                raise FilterError(f"Unsupported operator '{op}' in filter '{part}'.")

            if field in filters:
                raise FilterError(f"Duplicate filter for field '{field}'. Only one allowed.")

            # Process value based on operator type
            if op in {"in", "not_in"}:
                items = [v.strip() for v in raw_value.split(",") if v.strip()]
                value: Any = [_coerce_scalar(v) for v in items]
            elif op == "between":
                bounds = [v.strip() for v in raw_value.split(",") if v.strip()]
                if len(bounds) != 2:
                    raise FilterError(
                        "BETWEEN operator requires exactly two comma-separated values."
                    )
                value = [_coerce_scalar(bounds[0]), _coerce_scalar(bounds[1])]
            elif op in {"is_null", "is_not_null"}:
                value = raw_value.lower() in {"true", "1", "yes", "on"}
            else:
                value = _coerce_scalar(raw_value)

            filters[field] = {"field": field, "operator": op, "value": value}

        return [
            FilterParam.model_validate(x, context={"filter_spec": self.allowed_filters})
            for x in filters.values()
        ]
