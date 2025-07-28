from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Type,
)

from sqlalchemy import delete, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect as inspect_model
from sqlalchemy.orm import load_only, selectinload
from sqlalchemy.sql import Select

from ..errors import ValidationError
from ..schemas.pagination import (
    FilterParam,
    PaginatedResponse,
    Pagination,
)
from .filter import QueryFilter
from .types import (
    CreateSchemaType,
    ModelType,
    PrimaryKeyType,
    UpdateSchemaType,
)

if TYPE_CHECKING:
    from sqlalchemy.sql import Select


class CRUDHooks(
    Generic[
        ModelType,
        PrimaryKeyType,
        CreateSchemaType,
        UpdateSchemaType,
    ]
):
    """Base class for CRUD lifecycle hooks.

    This class provides hooks for different stages of CRUD operations,
    allowing you to implement custom business logic, validation, and
    side effects.

    Example:
        ```python
        class UserHooks(CRUDHooks[User, int, UserCreate, UserUpdate]):
            async def pre_create(self, db: AsyncSession, obj_in: UserCreate):
                # Validate before creation
                return obj_in

            async def post_create(self, db: AsyncSession, obj: User):
                # Actions after creation
                return obj
        ```
    """

    async def pre_create(
        self, db_session: AsyncSession, obj_in: CreateSchemaType, *args, **kwargs
    ) -> CreateSchemaType:
        """Called before creating an object.

        Args:
            db_session: Database session
            obj_in: Input data for creation
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Modified input data (can be the same or modified)

        Example:
            ```python
            async def pre_create(self, db: AsyncSession, obj_in: UserCreate):
                # Hash password before creation
                obj_in.password = hash_password(obj_in.password)
                return obj_in
            ```
        """
        return obj_in

    async def post_create(
        self, db_session: AsyncSession, obj: ModelType, *args, **kwargs
    ) -> ModelType:
        """Called after creating an object.

        Args:
            db_session: Database session
            obj: Created model instance
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Modified model instance (can be the same or modified)

        Example:
            ```python
            async def post_create(self, db: AsyncSession, obj: User):
                # Send welcome email after creation
                await send_welcome_email(obj.email)
                return obj
            ```
        """
        return obj

    async def pre_update(
        self,
        db_session: AsyncSession,
        obj: ModelType,
        obj_in: UpdateSchemaType,
        user: Optional[Any] = None,
    ) -> ModelType:
        """Called before updating an object.

        Args:
            db_session: Database session
            obj: Existing model instance
            obj_in: Update data
            user: Current user (if available)

        Returns:
            Modified model instance (can be the same or modified)

        Example:
            ```python
            async def pre_update(self, db: AsyncSession, obj: User, obj_in: UserUpdate):
                # Validate permissions
                if obj_in.role == "admin" and not user.is_admin:
                    raise PermissionError("Cannot assign admin role")
                return obj
            ```
        """
        return obj

    async def post_update(
        self, db_session: AsyncSession, obj: ModelType, *args, **kwargs
    ) -> ModelType:
        """Called after updating an object.

        Args:
            db_session: Database session
            obj: Updated model instance
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Modified model instance (can be the same or modified)

        Example:
            ```python
            async def post_update(self, db: AsyncSession, obj: User):
                # Log the update
                await log_user_update(obj.id, obj.updated_at)
                return obj
            ```
        """
        return obj

    async def pre_delete(self, db_session: AsyncSession, obj: ModelType, *args, **kwargs) -> bool:
        """Called before deleting an object.

        Args:
            db_session: Database session
            obj: Model instance to be deleted
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            True to allow deletion, False to prevent it

        Example:
            ```python
            async def pre_delete(self, db: AsyncSession, obj: User):
                # Prevent deletion of admin users
                if obj.role == "admin":
                    return False
                return True
            ```
        """
        return True

    async def post_delete(
        self, db_session: AsyncSession, obj: ModelType, *args, **kwargs
    ) -> ModelType:
        """Called after deleting an object.

        Args:
            db_session: Database session
            obj: Deleted model instance
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Deleted model instance

        Example:
            ```python
            async def post_delete(self, db: AsyncSession, obj: User):
                # Clean up related data
                await cleanup_user_data(obj.id)
                return obj
            ```
        """
        return obj

    async def pre_read(
        self, db_session: AsyncSession, obj_id: PrimaryKeyType, *args, **kwargs
    ) -> Any:
        """Called before reading an object.

        Args:
            db_session: Database session
            obj_id: Primary key value(s)
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Modified primary key value(s) (can be the same or modified)

        Example:
            ```python
            async def pre_read(self, db: AsyncSession, obj_id: int):
                # Log read access
                await log_read_access(obj_id)
                return obj_id
            ```
        """
        return obj_id

    async def post_read(
        self, db_session: AsyncSession, obj: Optional[ModelType], *args, **kwargs
    ) -> Optional[ModelType]:
        """Called after reading an object.

        Args:
            db_session: Database session
            obj: Retrieved model instance (None if not found)
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Modified model instance (can be the same, modified, or None)

        Example:
            ```python
            async def post_read(self, db: AsyncSession, obj: Optional[User]):
                if obj:
                    # Update last access time
                    obj.last_accessed = datetime.utcnow()
                    await db.commit()
                return obj
            ```
        """
        return obj


class BaseCRUD(Generic[ModelType, PrimaryKeyType, CreateSchemaType, UpdateSchemaType]):
    """Base CRUD class providing core database operations.

    This class provides the foundation for all CRUD operations including create,
    read, update, delete, and query operations. It supports filtering, pagination,
    searching, and sorting.

    Args:
        model: SQLAlchemy model class
        hooks: Optional CRUDHooks instance for lifecycle callbacks

    Example:
        ```python
        class UserCRUD(BaseCRUD[User, int, UserCreate, UserUpdate]):
            def __init__(self):
                super().__init__(User, UserHooks())
        ```
    """

    def __init__(
        self,
        model: Type[ModelType],
        hooks: Optional[CRUDHooks] = None,
    ):
        """Initialize the BaseCRUD instance.

        Args:
            model: SQLAlchemy model class to operate on
            hooks: Optional CRUDHooks instance for lifecycle callbacks
        """
        self.model = model
        self.hooks = hooks or CRUDHooks()
        self.query_filter = QueryFilter(model)

    @property
    def pk(self) -> List[str]:
        """Get the primary key column names for the model.

        Returns:
            List of primary key column names
        """
        return [column.name for column in self.model.__table__.primary_key]

    async def get_by_id(
        self,
        session: AsyncSession,
        id: PrimaryKeyType,
        prefetch: Optional[List[str]] = None,
    ) -> Optional[ModelType]:
        """Get a single item by its primary key.

        Args:
            session: Database session
            id: Primary key value(s)
            prefetch: List of relations to include in the query

        Returns:
            Model instance if found, None otherwise

        Example:
            ```python
            user = await user_crud.get_by_id(db, 1, include=["posts", "profile"])
            ```
        """
        pk_values = id if isinstance(id, tuple) else (id,)
        pk_conditions = [
            getattr(self.model, pk_col) == val
            for pk_col, val in zip(self.pk, pk_values, strict=False)
        ]  # TODO: Check order of pk_values
        query = select(self.model).where(*pk_conditions)

        if prefetch:
            query = self._apply_prefetch(query, prefetch)

        obj = await self.hooks.pre_read(session, id)
        result = await session.execute(query)
        obj = await self.hooks.post_read(session, result.scalar_one_or_none())
        return obj

    async def get_one(
        self,
        session: AsyncSession,
        filters: List[FilterParam],
        prefetch: List[str] | None = None,
    ) -> ModelType | None:
        """Get a single item using filters.

        Args:
            session: Database session
            filters: List of filter parameters
            prefetch: List of relations to include in the query

        Returns:
            Model instance if found, None otherwise

        Raises:
            FilterError: If filter validation fails

        Example:
            ```python
            filters = [FilterParam(field="email", operator="eq", value="user@example.com")]
            user = await user_crud.get_one(db, filters)
            ```
        """
        query = select(self.model)
        if prefetch:
            query = self._apply_prefetch(query, prefetch)

        if filters:
            query = self.query_filter.apply_filters(query, filters=filters)

        obj = await self.hooks.pre_read(session, filters)
        result = await session.execute(query)
        obj = await self.hooks.post_read(session, result.scalar_one_or_none())
        return obj

    async def apply_pagination(
        self,
        db: AsyncSession,
        query: Select,
        pagination: Pagination,
    ) -> PaginatedResponse:
        page = pagination["page"]
        size = pagination["size"]

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0
        total_pages = max(
            (total + size - 1) // size,
            1,
        )

        offset = (page - 1) * size

        query = query.offset(offset).limit(size)

        result = await db.execute(query)
        items = list(result.scalars().unique().all())
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

    async def list_objects(
        self,
        session: AsyncSession,
        *,
        search: Optional[str] = None,
        search_fields: Optional[List[str]] = None,
        sorting: str | None = None,
        filters: List[FilterParam] | None = None,
        prefetch: List[str] | None = None,
        pagination: Pagination | None = None,
    ) -> List[ModelType] | PaginatedResponse[ModelType]:
        """Generic pagination function with sorting, filtering, and search.

        Args:
            session: Database session
            search: Search term
            search_fields: List of fields to search in
            sorting: Sorting field
            filters: List of filters to apply to the query
            prefetch: List of relations to include in the query
            pagination: A dictionary containing the page and size

        Returns:
            PaginatedResponse[]: Paginated response containing the items, total count, current page,
            page size, total pages, next/previous flags, applied filters, search term, and sort options.
        """
        query = select(self.model)
        if prefetch:
            query = self._apply_prefetch(query, prefetch)

        if search:
            query = self.query_filter.apply_search(query, search, search_fields or [])

        if filters:
            query = self.query_filter.apply_filters(query, filters)

        if sorting:
            query = self.query_filter.apply_sorting(query, sorting)

        if pagination:
            return await self.apply_pagination(session, query, pagination=pagination)

        result = await session.execute(query)
        return list(result.scalars().unique().all())

    async def create(
        self,
        session: AsyncSession,
        obj_in: CreateSchemaType | Dict[str, Any],
        commit: bool = True,
        prefetch: List[str] | None = None,
        **kwargs,
    ) -> ModelType:
        obj_data = obj_in.model_dump() if not isinstance(obj_in, dict) else obj_in

        db_obj = self.model(**obj_data, **kwargs)
        db_obj = await self.hooks.pre_create(session, db_obj, obj_in)
        session.add(db_obj)
        if commit:
            await session.commit()
            await session.refresh(db_obj, attribute_names=prefetch)

        db_obj = await self.hooks.post_create(session, db_obj)
        return db_obj

    async def update(
        self,
        session: AsyncSession,
        obj: ModelType,
        obj_in: UpdateSchemaType | Dict[str, Any],
        commit: bool = True,
        **kwargs,
    ) -> ModelType:
        obj_data = obj_in.model_dump(exclude_unset=True) if not isinstance(obj_in, dict) else obj_in
        obj_data = {**obj_data, **kwargs}

        for field, value in obj_data.items():
            setattr(obj, field, value)

        obj = await self.hooks.pre_update(session, obj, obj_in)
        session.add(obj)
        if commit:
            await session.commit()
            await session.refresh(obj)
        obj = await self.hooks.post_update(session, obj)
        return obj

    async def delete(self, session: AsyncSession, obj: ModelType) -> ModelType:
        if not await self.hooks.pre_delete(session, obj):
            raise ValidationError("Delete operation cancelled by pre-delete hook")
        await session.delete(obj)
        await session.commit()
        obj = await self.hooks.post_delete(session, obj)
        return obj

    async def delete_by_id(self, session: AsyncSession, id: PrimaryKeyType) -> int:
        if len(self.pk) == 1:
            pk_column = getattr(self.model, self.pk[0])
            stmt = delete(self.model).where(pk_column == id)
        else:
            raise NotImplementedError("Composite primary keys are not supported for delete_by_id")

        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount

    async def get_or_create(
        self,
        session: AsyncSession,
        id: PrimaryKeyType,
        defaults: Dict[str, Any],
    ) -> tuple[ModelType, bool]:
        query = select(self.model).where(getattr(self.model, self.pk[0]) == id)

        result = await session.execute(query)
        db_obj = result.scalar_one_or_none()

        if db_obj:
            return db_obj, False

        if self.pk[0] not in defaults:
            defaults[self.pk[0]] = id

        db_obj = self.model(**defaults)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj, True

    async def search(
        self,
        session: AsyncSession,
        query: str,
        fields: List[str] | None = None,
        prefetch: List[str] | None = None,
    ) -> List[ModelType]:
        search_conditions = []
        for field in fields or []:
            if hasattr(self.model, field):
                attr = getattr(self.model, field)
                search_conditions.append(attr.ilike(f"%{query}%"))

        if not search_conditions:
            return []

        db_query = select(self.model).where(or_(*search_conditions))
        if prefetch:
            db_query = self._apply_prefetch(db_query, prefetch)
        result = await session.execute(db_query)
        return list(result.scalars().unique().all())

    async def count(
        self, session: AsyncSession, filters: Optional[List[FilterParam]] = None
    ) -> int:
        query = select(func.count()).select_from(self.model)
        if filters:
            query = self.query_filter.apply_filters(query, filters=filters)

        result = await session.execute(query)
        return result.scalar() or 0

    async def exists(self, session: AsyncSession, id: PrimaryKeyType) -> bool:
        query = select(exists().where(getattr(self.model, self.pk[0]) == id))
        result = await session.execute(query)
        return result.scalar() or False

    async def bulk_create(
        self,
        session: AsyncSession,
        objects: List[CreateSchemaType | Dict[str, Any]],
        commit: bool = True,
        **kwargs,
    ) -> List[ModelType]:
        db_objects = []
        for obj_in in objects:
            obj_data = obj_in.model_dump() if not isinstance(obj_in, dict) else obj_in
            db_obj = self.model(**obj_data, **kwargs)
            db_objects.append(db_obj)

        session.add_all(db_objects)
        if commit:
            await session.commit()
            for db_obj in db_objects:
                await session.refresh(db_obj)

        return db_objects

    async def bulk_update(
        self,
        session: AsyncSession,
        updates: List[UpdateSchemaType | Dict[str, Any]],
        commit: bool = True,
    ) -> int:
        if not updates:
            return 0

        updated_count = 0
        for update_data in updates:
            data_dict = (
                update_data.model_dump(exclude_unset=True)
                if not isinstance(update_data, dict)
                else update_data
            )

            # Extract ID for the update
            if self.pk[0] in data_dict:
                obj_id = data_dict.pop(self.pk[0])
                stmt = (
                    update(self.model)
                    .where(getattr(self.model, self.pk[0]) == obj_id)
                    .values(**data_dict)
                )
                result = await session.execute(stmt)
                updated_count += result.rowcount
            else:
                raise ValidationError("No ID provided for update")

        if commit:
            await session.commit()
        return updated_count

    async def bulk_delete(
        self, session: AsyncSession, ids: List[PrimaryKeyType], commit: bool = True
    ) -> int:
        if not ids:
            return 0
        stmt = delete(self.model).where(getattr(self.model, self.pk[0]).in_(ids))

        result = await session.execute(stmt)
        if commit:
            await session.commit()
        return result.rowcount

    def _apply_prefetch(self, query: Select, prefetch: List[str]) -> Select:
        relations = self._get_model_relations(prefetch)
        if not relations:
            return query
        loaders = self._build_relation_loaders(relations)
        return query.options(*loaders)

    def _get_model_relations(self, relations: List[str] | None = None) -> List[str]:
        if relations is None:
            # Return all available relations
            mapper = inspect_model(self.model)
            return [rel.key for rel in mapper.relationships]

        # Validate and return the provided relations
        for path in relations:
            segments = path.split(".")
            current_model = self.model
            for i, seg in enumerate(segments):
                mapper = inspect_model(current_model)
                valid_relations = {rel.key for rel in mapper.relationships}
                valid_columns = {col.name for col in mapper.columns}

                if i == len(segments) - 1:
                    if seg not in valid_relations and seg not in valid_columns:
                        raise ValidationError(
                            f"Invalid relation or column '{path}' for model {self.model.__name__}"
                        )
                    if seg in valid_columns:
                        break
                else:
                    if seg not in valid_relations:
                        raise ValidationError(
                            f"Invalid relation '{path}' for model {self.model.__name__}"
                        )

                if seg in valid_relations:
                    current_model = getattr(current_model, seg).property.mapper.class_
        return relations

    def _build_relation_loaders(self, relations: List[str]) -> List:
        loaders = []
        for path in relations:
            segments = path.split(".")

            current_model = self.model
            is_column_path = False

            for _, seg in enumerate(segments[:-1]):
                current_model = getattr(current_model, seg).property.mapper.class_

            if len(segments) > 1:
                last_seg = segments[-1]
                mapper = inspect_model(current_model)
                valid_columns = {col.name for col in mapper.columns}
                is_column_path = last_seg in valid_columns

            if is_column_path:
                if len(segments) > 2:
                    loader = selectinload(getattr(self.model, segments[0]))
                    current_model = getattr(self.model, segments[0]).property.mapper.class_

                    for seg in segments[1:-2]:
                        loader = loader.selectinload(getattr(current_model, seg))
                        current_model = getattr(current_model, seg).property.mapper.class_

                    final_rel = segments[-2]
                    final_rel_attr = getattr(current_model, final_rel)
                    loader = loader.selectinload(final_rel_attr)

                    final_model = final_rel_attr.property.mapper.class_
                    final_col_attr = getattr(final_model, segments[-1])
                    loaders.extend([loader, load_only(final_col_attr)])
                else:
                    loader = selectinload(getattr(self.model, segments[0]))
                    final_col_attr = getattr(current_model, segments[-1])
                    loaders.extend([loader, load_only(final_col_attr)])
            else:
                loader = selectinload(getattr(self.model, segments[0]))
                current_model = getattr(self.model, segments[0]).property.mapper.class_
                for seg in segments[1:]:
                    loader = loader.selectinload(getattr(current_model, seg))
                    current_model = getattr(current_model, seg).property.mapper.class_
                loaders.append(loader)

        return loaders
