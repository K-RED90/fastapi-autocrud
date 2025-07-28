"""
Custom action decorator for FastAPI-AutoCRUD routers.

This module provides the @action decorator that allows creating custom endpoints
beyond the standard CRUD operations, similar to Django REST Framework's @action.
"""

from enum import Enum
from typing import Any, Callable, List, Literal, Optional, ParamSpec, Type, TypeVar

from pydantic import BaseModel

P = ParamSpec("P")
T = TypeVar("T")


class ActionMetadata:
    """
    Metadata class for custom action endpoints.

    This class stores all the configuration for a custom action,
    including HTTP method, URL path, dependencies, and response settings.
    """

    def __init__(
        self,
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
        detail: bool = False,
        url_path: Optional[str] = None,
        dependencies: Optional[List[Callable[..., Any]]] = None,
        response_model: Optional[Type[BaseModel]] = None,
        response_model_by_alias: bool = True,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str | Enum]] = None,
        deprecated: bool = False,
        status_code: int | None = None,
        **kwargs: Any,
    ):
        """
        Initialize ActionMetadata with action configuration.

        Args:
            method: HTTP method for the action
            detail: True for single item endpoints, False for collection endpoints
            url_path: Custom URL path segment
            dependencies: Additional FastAPI dependencies
            response_model: Pydantic response model
            response_model_by_alias: Whether to use model aliases in response
            summary: Short description for OpenAPI docs
            description: Detailed description for OpenAPI docs
            tags: OpenAPI tags for grouping endpoints
            deprecated: Whether the endpoint is deprecated
            status_code: HTTP status code for the response
            **kwargs: Additional keyword arguments
        """
        self.method = method
        self.detail = detail
        self.url_path = url_path
        self.dependencies = dependencies or []
        self.response_model = response_model
        self.response_model_by_alias = response_model_by_alias
        self.status_code = (
            status_code
            if status_code is not None
            else 200
            if method == "GET"
            else 201
            if method == "POST"
            else 204
            if method == "DELETE"
            else 200
            if method == "PUT"
            else 200
            if method == "PATCH"
            else 200
        )
        self.summary = summary
        self.description = description
        self.tags = tags
        self.deprecated = deprecated
        self.kwargs = kwargs


def action(
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET",
    detail: bool = False,
    url_path: Optional[str] = None,
    dependencies: Optional[List[Callable[..., Any]]] = None,
    response_model: Optional[Type[BaseModel] | Type] = None,
    response_model_by_alias: bool = True,
    status_code: int | None = None,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str | Enum]] = None,
    deprecated: bool = False,
    **kwargs: Any,
):
    """
    Decorator for custom endpoints similar to Django REST Framework's @action.

    This decorator allows you to create custom endpoints beyond the standard
    CRUD operations. It can be used to add business logic, custom workflows,
    or specialized endpoints for your models.

    Args:
        method: HTTP method for the action (GET, POST, PUT, PATCH, DELETE)
        detail: True for single item endpoints (e.g., /users/{id}/activate),
                False for collection endpoints (e.g., /users/verified)
        url_path: Custom URL path segment. If None, uses the function name
        dependencies: Additional FastAPI dependencies (e.g., authentication)
        response_model: Pydantic model for response serialization
        response_model_by_alias: Whether to use model aliases in response
        status_code: HTTP status code for the response
        summary: Short description for OpenAPI documentation
        description: Detailed description for OpenAPI documentation
        tags: OpenAPI tags for grouping endpoints
        deprecated: Whether the endpoint is deprecated
        **kwargs: Additional keyword arguments passed to FastAPI

    Returns:
        Decorated function with action metadata attached

    Example:
        ```python
        class UserRouterFactory(RouterFactory[User, int, UserCreate, UserUpdate]):
            @action(method="POST", detail=True, url_path="activate")
            async def activate_user(self, user_id: int, db: AsyncSession):
                user = await self.get_by_id(db, user_id)
                if not user:
                    raise HTTPException(404, "User not found")
                return await self.update(db, user, {"is_active": True})

            @action(method="GET", detail=False, url_path="verified")
            async def get_verified_users(self, db: AsyncSession):
                filters = [FilterParam(field="is_verified", operator="eq", value=True)]
                return await self.get_multi(db, filters=filters)
        ```
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Attach metadata to the function
        func._action_metadata = ActionMetadata(  # type: ignore
            method=method,
            detail=detail,
            url_path=url_path,
            dependencies=dependencies,
            response_model=response_model,
            response_model_by_alias=response_model_by_alias,
            summary=summary,
            description=description,
            tags=tags,
            deprecated=deprecated,
            status_code=status_code
            if status_code is not None
            else 200
            if method == "GET"
            else 201
            if method == "POST"
            else 204
            if method == "DELETE"
            else 200
            if method == "PUT"
            else 200
            if method == "PATCH"
            else 200,
            **kwargs,
        )
        return func

    return decorator
