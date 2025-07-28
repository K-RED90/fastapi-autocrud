"""
Pagination and query parameter schemas for FastAPI-AutoCRUD.

This module provides Pydantic models for handling pagination, sorting,
filtering, and bulk operations in FastAPI-AutoCRUD.
"""

from __future__ import annotations

from typing import (
    Any,
    Generic,
    Iterator,
    List,
    Literal,
    Optional,
    Self,
    TypedDict,
    TypeVar,
    Union,
)

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Response model for paginated results.

    This model provides a standardized structure for paginated responses,
    including metadata about the pagination state and the actual items.

    Attributes:
        items: List of items for the current page
        total: Total number of items across all pages
        page: Current page number
        size: Number of items per page
        pages: Total number of pages
        has_next: Whether there is a next page
        has_prev: Whether there is a previous page
    """

    items: List[T]
    total: int
    page: int
    size: int
    pages: int
    has_next: bool
    has_prev: bool

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    def __iter__(self) -> Iterator[T]:  # type: ignore[override]
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> T:
        return self.items[index]


# Type alias for all supported filter operators
OPERATORS = Literal[
    "eq",  # Equal
    "ne",  # Not equal
    "gt",  # Greater than
    "ge",  # Greater than or equal
    "lt",  # Less than
    "le",  # Less than or equal
    "like",  # Case-sensitive LIKE
    "ilike",  # Case-insensitive LIKE
    "in",  # In list
    "not_in",  # Not in list
    "is_null",  # Is null
    "is_not_null",  # Is not null
    "between",  # Between two values
    "contains",  # Contains substring
    "startswith",  # Starts with
    "endswith",  # Ends with
    "and",  # Logical AND
    "or",  # Logical OR
    "not",  # Logical NOT
]


class FilterParam(BaseModel):
    """
    Parameters for filtering configuration.

    This model defines how to filter results, including
    the field, operator, and value to filter by.

    Attributes:
        field: Name of the field to filter on (optional for logical operators)
        operator: The filter operator to use
        value: The value to filter by (can be a list for logical operators)
    """

    field: Optional[str] = Field(default=None, description="Field to filter on")
    operator: OPERATORS
    value: Optional[Union[Any, List["FilterParam"]]] = Field(
        default=None,
        description="""Value to filter on. For logical operators, this is a list of 
        FilterParam objects.""",
    )

    # Dynamic validation against a developer-provided filter specification.
    # The specification should be supplied via the `context` argument of
    # `model_validate`, using the key ``filter_spec`` with a mapping of
    # field-name -> tuple of allowed operators. This keeps validation at the API
    # layer only – manual instantiation of FilterParam objects in lower layers
    # remains unaffected when no context is provided.

    @model_validator(mode="after")
    def _validate_allowed_operator(self, info: ValidationInfo) -> Self:
        spec = info.context.get("filter_spec") if info.context else None

        if spec:
            # Logical operators are always allowed to enable complex expressions.
            if self.operator in {"and", "or", "not"}:
                return self

            if self.field is None:
                raise ValueError("Field must be specified for non-logical operators")

            allowed_ops = spec.get(self.field)
            if allowed_ops is None:
                raise ValueError(f"Filtering by field '{self.field}' is not permitted")

            if self.operator not in allowed_ops:
                raise ValueError(
                    f"Operator '{self.operator}' not allowed for field '{self.field}'. "
                    f"Allowed operators: {allowed_ops}"
                )

        return self


class Filter(TypedDict):
    field: str | None
    operator: OPERATORS
    value: Union[Any, List[Self], None]


class BulkResponse(BaseModel, Generic[T]):
    """
    Response model for bulk operations.

    This model provides a standardized structure for bulk operation
    responses, including counts of affected items and any errors.
    """

    created: int = 0
    updated: int = 0
    deleted: int = 0

    items: Optional[List[T]] = Field(default=None)

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class Pagination(TypedDict):
    page: int
    size: int
