import inspect
from enum import Enum
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
)

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from fastapi.responses import Response
from loguru import logger
from pydantic import BaseModel, create_model
from sqlalchemy.ext.asyncio import AsyncSession

from ...dependencies.page_param import PageParams
from ..errors import NotFoundError, ValidationError
from ..schemas.pagination import (
    OPERATORS,
    BulkResponse,
    PaginatedResponse,
)
from .base import BaseCRUD
from .decorators import ActionMetadata
from .types import (
    CreateSchemaType,
    ModelType,
    PrimaryKeyType,
    UpdateSchemaType,
)


class RouterFactory(Generic[ModelType, PrimaryKeyType, CreateSchemaType, UpdateSchemaType]):
    """
    Factory for creating CRUD Routers.
    """

    def __init__(
        self,
        crud: BaseCRUD[ModelType, PrimaryKeyType, CreateSchemaType, UpdateSchemaType],
        session_factory: Callable[[], AsyncGenerator[AsyncSession, None]],
        create_schema: Type[CreateSchemaType],
        update_schema: Type[UpdateSchemaType],
        prefix: str = "",
        tags: Optional[List[Union[str, Enum]]] = None,
        dependencies: Optional[List[Callable[..., Any]]] = None,
        # Feature toggles
        enable_create: bool = True,
        enable_read: bool = True,
        enable_update: bool = True,
        enable_delete: bool = True,
        enable_list: bool = True,
        enable_bulk_create: bool = True,
        enable_bulk_update: bool = True,
        enable_bulk_delete: bool = True,
        enable_pagination: bool = True,
        enable_search: bool = False,
        enable_sorting: bool = False,
        enable_filters: bool = False,
        # Pagination settings
        page_size: int = 20,
        max_page_size: int = 100,
        # Search and sort configuration
        search_fields: Optional[List[str]] = None,
        sort_fields: Optional[List[str]] = None,
        sort_default: str = "id",
        # Response configuration
        prefetch: Optional[List[str]] = None,
        response_schemas: Optional[
            Dict[
                Literal[
                    "create",
                    "update",
                    "read",
                    "list",
                    "bulk_create",
                    "bulk_update",
                    "bulk_delete",
                ],
                Type[BaseModel],
            ]
        ] = None,
        filter_spec: Optional[
            Dict[str, Tuple[OPERATORS, ...]]
        ] = None,  # Example: {"name": ("eq", "in", "contains")}
        router_kwargs: Optional[Dict[str, Any]] = None,
    ):
        if prefix and not prefix.startswith("/"):
            prefix = f"/{prefix}"
        self.crud = crud
        self.prefix = prefix
        self.tags = tags or []
        self.dependencies = dependencies or []

        self.enable_create = enable_create
        self.enable_read = enable_read
        self.enable_update = enable_update
        self.enable_delete = enable_delete
        self.enable_list = enable_list
        self.enable_bulk_create = enable_bulk_create
        self.enable_bulk_update = enable_bulk_update
        self.enable_bulk_delete = enable_bulk_delete
        self.enable_search = enable_search
        self.enable_sorting = enable_sorting
        self.enable_filters = enable_filters
        self.enable_pagination = enable_pagination

        self.page_size = page_size
        self.max_page_size = max_page_size

        self.search_fields = search_fields or []
        self.sort_fields = sort_fields or []
        self.sort_default = sort_default

        self.prefetch = prefetch or []

        self.create_schema = create_schema
        self.update_schema = update_schema
        self.response_schemas = response_schemas or {}

        self._resolved_types = self._resolve_generic_types()
        self.session_factory = session_factory
        self.filter_spec = filter_spec or {}

        self.router = APIRouter(
            prefix=self.prefix,
            tags=self.tags if self.tags else None,
            dependencies=[Depends(dep) for dep in self.dependencies],
            **(router_kwargs or {}),
        )

        self._register_custom_actions()
        self._register_endpoints()

    def _resolve_generic_types(self) -> Dict[str, Type]:
        return {
            "ModelType": self.crud.model,
            "PrimaryKeyType": self._detect_primary_key_type(),
            "CreateSchemaType": self.create_schema,
            "UpdateSchemaType": self.update_schema,
        }

    def _detect_primary_key_type(self) -> Type:
        import uuid
        from datetime import date, datetime
        from decimal import Decimal

        pk_columns = [col for col in self.crud.model.__table__.columns if col.primary_key]

        if not pk_columns:
            return int

        pk_column = pk_columns[0]

        sql_type_str = str(pk_column.type).split("(")[0].upper()

        type_mapping = {
            "INTEGER": int,
            "BIGINT": int,
            "SMALLINT": int,
            "UUID": uuid.UUID,
            "VARCHAR": str,
            "CHAR": str,
            "TEXT": str,
            "DATETIME": datetime,
            "TIMESTAMP": datetime,
            "DATE": date,
            "NUMERIC": Decimal,
            "DECIMAL": Decimal,
            "FLOAT": float,
            "REAL": float,
            "DOUBLE": float,
        }

        return type_mapping.get(sql_type_str, str)

    def _create_typed_endpoint(
        self,
        method_name: str,
    ) -> Callable:
        """Create a properly typed endpoint function."""

        pk_type = self._resolved_types["PrimaryKeyType"]
        create_type = self._resolved_types["CreateSchemaType"]
        update_type = self._resolved_types["UpdateSchemaType"]

        if method_name == "create":

            async def create_endpoint(
                session: AsyncSession = Depends(self.session_factory),
                item: create_type = Body(...),  # type: ignore[valid-type]
            ):
                return await self.perform_create(session, item)

            endpoint_func = create_endpoint

        elif method_name == "read":

            async def read_endpoint(
                session: AsyncSession = Depends(self.session_factory),
                id: pk_type = Path(..., description="Item ID"),  # type: ignore[valid-type]
            ):
                return await self.perform_read(session, id)

            endpoint_func = read_endpoint

        elif method_name == "update":

            async def update_endpoint(
                session: AsyncSession = Depends(self.session_factory),
                id: pk_type = Path(..., description="Item ID"),  # type: ignore[valid-type]
                item: update_type = Body(...),  # type: ignore[valid-type]
            ):
                return await self.perform_update(session, id=id, data=item)

            endpoint_func = update_endpoint

        elif method_name == "delete":

            async def delete_endpoint(
                session: AsyncSession = Depends(self.session_factory),
                id: pk_type = Path(..., description="Item ID"),  # type: ignore[valid-type]
            ):
                return await self.perform_delete(session, id=id)

            endpoint_func = delete_endpoint

        elif method_name == "list":
            endpoint_func = self._create_list_endpoint()

        elif method_name == "bulk_create":

            async def bulk_create_endpoint(
                session: AsyncSession = Depends(self.session_factory),
                items: List[create_type] = Body(...),  # type: ignore[valid-type]
            ):
                return await self.perform_bulk_create(session, items)

            endpoint_func = bulk_create_endpoint

        elif method_name == "bulk_update":
            bulk_update_schema = self._create_bulk_update_schema()

            async def bulk_update_endpoint(
                session: AsyncSession = Depends(self.session_factory),
                updates: List[bulk_update_schema] = Body(...),  # type: ignore[valid-type]
            ):
                return await self.perform_bulk_update(session, updates)

            endpoint_func = bulk_update_endpoint

        elif method_name == "bulk_delete":

            async def bulk_delete_endpoint(
                session: AsyncSession = Depends(self.session_factory),
                ids: List[pk_type] = Body(...),  # type: ignore[valid-type]
            ):
                return await self.perform_bulk_delete(session, ids)

            endpoint_func = bulk_delete_endpoint

        else:
            raise ValueError(f"Unknown endpoint method: {method_name}")

        # Set proper function metadata
        endpoint_func.__name__ = method_name
        endpoint_func.__doc__ = f"{method_name.title()} endpoint for {self.crud.model.__name__}"

        return endpoint_func

    def _create_list_endpoint(self) -> Callable:
        """Create the list endpoint, dynamically including only the query parameters
        that are enabled via feature flags (pagination, search, sorting, filters).

        We build the function once and then patch its ``__signature__`` so that
        FastAPI/​Pydantic (and the generated OpenAPI docs) are aware of the exact
        parameters that are accepted by the endpoint. This keeps the public API
        surface clean and avoids exposing unused parameters when a feature is
        disabled.
        """

        async def list_endpoint(session: AsyncSession = Depends(self.session_factory), **kwargs):  # type: ignore[valid-type]
            """Dynamically generated list endpoint – the actual accepted query
            parameters are injected via ``__signature__`` below. The **kwargs
            container lets us accept whatever parameters we add to the signature
            without explicitly naming them in the function definition.
            """

            page = kwargs.pop("page", 1)
            size = kwargs.pop("size", self.page_size)

            search = kwargs.pop("search", None) if self.enable_search else None
            sort_by = kwargs.pop("sort_by", self.sort_default) if self.enable_sorting else None
            filters = kwargs.pop("filters", None) if self.enable_filters else None

            page_params = PageParams(
                page=page,
                size=size,
                search=search,
                sort_by=sort_by,
                filters=filters,
                allowed_filters=self.filter_spec
                if self.enable_filters and self.filter_spec
                else None,
            )

            return await self.perform_list(session, page_params)

        parameters: list[inspect.Parameter] = [
            inspect.Parameter(
                "session",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=Depends(self.session_factory),
                annotation=AsyncSession,
            )
        ]

        if self.enable_pagination:
            parameters.extend(
                [
                    inspect.Parameter(
                        "page",
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        default=Query(1, ge=1, description="Page number"),
                        annotation=int,
                    ),
                    inspect.Parameter(
                        "size",
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        default=Query(
                            self.page_size,
                            ge=1,
                            le=self.max_page_size,
                            description="Page size",
                        ),
                        annotation=int,
                    ),
                ]
            )

        if self.enable_search:
            parameters.append(
                inspect.Parameter(
                    "search",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=Query(None, description="Search query"),
                    annotation=Optional[str],
                )
            )

        if self.enable_sorting:
            parameters.append(
                inspect.Parameter(
                    "sort_by",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=Query(
                        self.sort_default,
                        description="(e.g., 'created_at', '-updated_at' for desc)",
                    ),
                    annotation=Optional[str],
                )
            )

        if self.enable_filters:
            parameters.append(
                inspect.Parameter(
                    "filters",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=Query(
                        None,
                        description="""
                        Filters in format: field__operator=value,field2__operator=value2.
                        Operators: eq, ne, gt, ge, lt, le, in, not_in, is_null, is_not_null,
                          between, contains, startswith, endswith.
                        Examples:
                        status__eq=active,created_at__gte=2024-01-01
                        status__in=active,pending,created_at__between=2024-01-01,2024-01-02
                        name__contains=john
                        name__startswith=j
                        name__endswith=son
                        email__is_null=true
                        age__gt=18
                        age__between=20,30
                        tags__in=featured,promoted
                        updated_at__gte=2024-01-01
                        """,
                    ),
                    annotation=Optional[str],
                )
            )

        # Apply the crafted signature to our endpoint function so FastAPI picks it up
        list_endpoint.__signature__ = inspect.Signature(parameters)  # type: ignore[attr-defined]

        return list_endpoint

    def _is_method_overridden(self, method_name: str) -> bool:
        """
        Check if a perform_* method has been overridden in a subclass.

        Args:
            method_name: The name of the method to check (e.g., 'create', 'update')

        Returns:
            True if the method is overridden, False otherwise
        """
        perform_method_name = f"perform_{method_name}"

        # Get the method from the current class
        current_method = getattr(self, perform_method_name, None)
        if current_method is None:
            return False

        # Get the method from the parent class (RouterFactory)
        parent_method = getattr(RouterFactory, perform_method_name, None)
        if parent_method is None:
            return False

        # Check if the method is overridden by comparing the function objects
        return current_method.__code__ is not parent_method.__code__

    def _get_endpoint_function(self, method_name: str) -> Callable:
        """
        Get the appropriate endpoint function for a given method.

        Args:
            method_name: The name of the method (e.g., 'create', 'update')

        Returns:
            The endpoint function to use
        """
        if self._is_method_overridden(method_name):
            return getattr(self, f"perform_{method_name}")
        else:
            return self._create_typed_endpoint(method_name)

    def _register_endpoints(self):
        """Register endpoints, using overridden methods when available."""

        endpoint_configs = [
            {
                "method": "create",
                "enabled": self.enable_create,
                "path": "/",
                "http_methods": ["POST"],
                "status_code": status.HTTP_201_CREATED,
                "response_description": "Item created successfully",
            },
            {
                "method": "list",
                "enabled": self.enable_list,
                "path": "/",
                "http_methods": ["GET"],
                "wrapper": "paginated" if self.enable_pagination else "list",
            },
            # Bulk operations must come before individual operations to avoid path conflicts
            {
                "method": "bulk_create",
                "enabled": self.enable_bulk_create,
                "path": "/bulk",
                "http_methods": ["POST"],
                "status_code": status.HTTP_201_CREATED,
                "wrapper": "bulk",
            },
            {
                "method": "bulk_update",
                "enabled": self.enable_bulk_update,
                "path": "/bulk",
                "http_methods": ["PUT"],
                "wrapper": "bulk",
            },
            {
                "method": "bulk_delete",
                "enabled": self.enable_bulk_delete,
                "path": "/bulk",
                "http_methods": ["DELETE"],
                "status_code": status.HTTP_200_OK,
                "wrapper": "bulk",
            },
            # Individual operations come after bulk operations
            {
                "method": "read",
                "enabled": self.enable_read,
                "path": "/{id}",
                "http_methods": ["GET"],
                "responses": {404: {"description": "Item not found"}},
            },
            {
                "method": "update",
                "enabled": self.enable_update,
                "path": "/{id}",
                "http_methods": ["PUT", "PATCH"],
                "responses": {404: {"description": "Item not found"}},
            },
            {
                "method": "delete",
                "enabled": self.enable_delete,
                "path": "/{id}",
                "http_methods": ["DELETE"],
                "status_code": status.HTTP_204_NO_CONTENT,
                "responses": {404: {"description": "Item not found"}},
                "no_response_body": True,  # 204 responses cannot have a body
            },
        ]

        # Register each endpoint
        for config in endpoint_configs:
            if not config["enabled"]:
                continue

            method_name = config["method"]
            endpoint_func = self._get_endpoint_function(method_name)

            response_model = None
            if not config.get("no_response_body"):
                response_model = self._get_response_model(
                    method_name, wrapper=config.get("wrapper")
                )

            operation_id = f"{method_name}_{self.crud.model.__name__.lower()}_item"
            if method_name == "update":
                for http_method in config["http_methods"]:
                    method_suffix = "put" if http_method == "PUT" else "patch"
                    operation_id = f"{method_suffix}_update_{self.crud.model.__name__.lower()}_item"

                    self.router.add_api_route(
                        config["path"],
                        endpoint_func,
                        methods=[http_method],
                        response_model=response_model,
                        status_code=config.get("status_code"),
                        summary=f"Update {self.crud.model.__name__} ({http_method})",
                        responses=config.get("responses"),
                        operation_id=operation_id,
                    )
            else:
                summary = f"{method_name.title()} {self.crud.model.__name__}"
                if method_name == "list":
                    summary += "s" + (" with pagination" if self.enable_pagination else "")
                elif method_name.startswith("bulk_"):
                    summary = f"Bulk {method_name.replace('bulk_', '')} {self.crud.model.__name__}s"

                for http_method in config["http_methods"]:
                    self.router.add_api_route(
                        config["path"],
                        endpoint_func,
                        methods=[http_method],
                        response_model=response_model,
                        status_code=config.get("status_code"),
                        summary=summary,
                        response_description=config.get("response_description", ""),
                        responses=config.get("responses"),
                        operation_id=operation_id,
                    )

    async def perform_create(
        self, session: AsyncSession, data: CreateSchemaType = Body(...)
    ) -> ModelType:
        try:
            return await self.crud.create(session, obj_in=data, prefetch=self.prefetch)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            logger.error(f"Create error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error") from e

    async def perform_read(
        self, session: AsyncSession, id: PrimaryKeyType = Path(...)
    ) -> ModelType:
        try:
            item = await self.crud.get_by_id(session, id=id, prefetch=self.prefetch)
            if not item:
                raise HTTPException(status_code=404, detail="Item not found")
            return item
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail="Item not found") from e
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Read error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error") from e

    async def perform_update(
        self,
        session: AsyncSession,
        *,
        id: PrimaryKeyType,
        data: UpdateSchemaType = Body(...),
    ) -> ModelType:
        existing_item = await self.crud.get_by_id(session, id=id, prefetch=self.prefetch)
        if not existing_item:
            raise NotFoundError(f"Item with id {id} not found")
        return await self.crud.update(
            session, obj=existing_item, obj_in=data, prefetch=self.prefetch
        )

    async def perform_delete(
        self, session: AsyncSession, id: PrimaryKeyType = Path(...)
    ) -> Response:
        existing_item = await self.crud.get_by_id(session, id=id, prefetch=self.prefetch)
        if not existing_item:
            raise NotFoundError(f"Item with id {id} not found")
        await self.crud.delete(session, obj=existing_item)
        return Response(status_code=204)

    async def perform_list(
        self,
        session: AsyncSession,
        page_params: PageParams,
    ) -> List[ModelType] | PaginatedResponse[ModelType]:
        return await self.crud.list_objects(
            session,
            prefetch=self.prefetch,
            filters=page_params.filters,
            search=page_params.search,
            search_fields=self.search_fields,
            sorting=page_params.sort_by,
            pagination={
                "page": page_params.page,
                "size": page_params.size,
            }
            if self.enable_pagination
            else None,
        )

    async def perform_bulk_create(
        self,
        session: AsyncSession,
        data: Sequence[CreateSchemaType],
    ):
        created_items = await self.crud.bulk_create(
            session,
            cast(List[Dict[str, Any] | CreateSchemaType], list(data)),
        )
        return {"items": created_items, "created": len(created_items)}

    async def perform_bulk_update(self, session: AsyncSession, data: Sequence[UpdateSchemaType]):
        updated_count = await self.crud.bulk_update(
            session, cast(List[Dict[str, Any] | UpdateSchemaType], list(data))
        )
        return {"updated": updated_count}

    async def perform_bulk_delete(self, session: AsyncSession, ids: List[PrimaryKeyType]):
        deleted_count = await self.crud.bulk_delete(session, ids)
        return {"deleted": deleted_count}

    def _register_custom_actions(self):
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, "_action_metadata"):
                metadata: ActionMetadata = attr._action_metadata

                if metadata.detail:
                    path = f"/{{id}}/{metadata.url_path or attr_name}"
                else:
                    path = f"/{metadata.url_path or attr_name}"

                self.router.add_api_route(
                    path,
                    attr,
                    methods=[metadata.method],
                    response_model=metadata.response_model,
                    status_code=metadata.status_code,
                    dependencies=[Depends(dep) for dep in metadata.dependencies],
                    summary=metadata.kwargs.pop("summary", f"Custom action: {attr_name}"),
                    description=metadata.description,
                    tags=metadata.tags,
                    deprecated=metadata.deprecated,
                    **metadata.kwargs,
                )

    def _generate_response_schema(self) -> Type[BaseModel]:
        from typing import Optional

        model_fields = {}

        for column in self.crud.model.__table__.columns:
            field_type = self._get_python_type(column.type)
            if column.nullable or column.default is not None or column.server_default is not None:
                field_type = Optional[field_type]
                model_fields[column.name] = (field_type, None)
            else:
                model_fields[column.name] = (field_type, ...)

        return create_model(f"{self.crud.model.__name__}Response", **model_fields)

    def _get_python_type(self, sql_type: Any) -> Type:
        import datetime
        import uuid
        from decimal import Decimal

        type_name = str(sql_type).split("(")[0].upper()

        type_mapping: Dict[str, Type] = {
            # Numeric types
            "INTEGER": int,
            "BIGINT": int,
            "SMALLINT": int,
            "TINYINT": int,
            "NUMERIC": Decimal,
            "DECIMAL": Decimal,
            "FLOAT": float,
            "REAL": float,
            "DOUBLE": float,
            "DOUBLE PRECISION": float,
            # String types
            "VARCHAR": str,
            "CHAR": str,
            "TEXT": str,
            "NVARCHAR": str,
            "NCHAR": str,
            "NTEXT": str,
            "CLOB": str,
            # Boolean type
            "BOOLEAN": bool,
            "BOOL": bool,
            # Date/Time types
            "DATETIME": datetime.datetime,
            "TIMESTAMP": datetime.datetime,
            "DATE": datetime.date,
            "TIME": datetime.time,
            # Binary types
            "BINARY": bytes,
            "VARBINARY": bytes,
            "BLOB": bytes,
            # UUID type
            "UUID": uuid.UUID,
            # JSON types
            "JSON": dict,
            "JSONB": dict,
            # Array types
            "ARRAY": list,
        }

        return type_mapping.get(type_name, str)

    def get_router(self) -> APIRouter:
        return self.router

    def _get_response_model(
        self,
        key: Literal[
            "create",
            "update",
            "read",
            "list",
            "bulk_create",
            "bulk_update",
            "bulk_delete",
        ],
        wrapper: Optional[str] = None,
    ):
        schema = self.response_schemas.get(key, self._generate_response_schema())

        if wrapper == "paginated":
            return PaginatedResponse[schema]
        if wrapper == "bulk":
            return BulkResponse[schema]
        if wrapper == "list":
            return List[schema]
        return schema

    def _create_bulk_update_schema(self) -> Type[BaseModel]:
        from pydantic import create_model

        pk_field = self.crud.pk[0]
        pk_type = self._resolved_types["PrimaryKeyType"]

        update_fields = {}
        for field_name, field_info in self.update_schema.model_fields.items():
            update_fields[field_name] = (field_info.annotation, field_info.default)

        update_fields[pk_field] = (pk_type, ...)

        return create_model(f"{self.crud.model.__name__}BulkUpdate", **update_fields)
