import uuid
from datetime import datetime
from typing import Dict, Literal, Type

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import select

from auto_crud.core.crud.base import BaseCRUD
from auto_crud.core.crud.router import RouterFactory
from auto_crud.core.errors import NotFoundError
from tests.conftest import (
    Category,
    CategoryCreate,
    CategoryUpdate,
    User,
    UserCreate,
    UserUpdate,
    create_test_user,
)


class TestRouterFactory:
    """Test suite for RouterFactory class."""

    @pytest.mark.asyncio
    async def test_router_initialization(self, user_router):
        assert user_router.create_schema == UserCreate
        assert user_router.update_schema == UserUpdate
        assert user_router.prefix == "/users"
        assert user_router.tags == ["users"]
        assert user_router.enable_create is True
        assert user_router.enable_read is True
        assert user_router.enable_update is True
        assert user_router.enable_delete is True
        assert user_router.enable_list is True
        assert user_router.enable_bulk_create is True
        assert user_router.enable_bulk_update is True
        assert user_router.enable_bulk_delete is True
        assert user_router.enable_pagination is True

    @pytest.mark.asyncio
    async def test_router_with_custom_configuration(self, session_factory):
        """Test RouterFactory with custom configuration."""
        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            prefix="/custom-users",
            tags=["custom"],
            enable_create=False,
            enable_read=True,
            enable_update=False,
            enable_delete=True,
            enable_list=False,
            enable_bulk_create=False,
            enable_bulk_update=False,
            enable_bulk_delete=False,
            enable_pagination=False,
            page_size=50,
            max_page_size=200,
            search_fields=["username", "email"],
            sort_default="username",
        )

        assert router.prefix == "/custom-users"
        assert router.tags == ["custom"]
        assert router.enable_create is False
        assert router.enable_read is True
        assert router.enable_update is False
        assert router.enable_delete is True
        assert router.enable_list is False
        assert router.enable_bulk_create is False
        assert router.enable_bulk_update is False
        assert router.enable_bulk_delete is False
        assert router.enable_pagination is False
        assert router.page_size == 50
        assert router.max_page_size == 200
        assert router.search_fields == ["username", "email"]
        assert router.sort_default == "username"

    @pytest.mark.asyncio
    async def test_resolve_generic_types(self, user_router):
        """Test generic type resolution."""
        resolved_types = user_router._resolved_types

        assert resolved_types["ModelType"] == User
        assert resolved_types["CreateSchemaType"] == UserCreate
        assert resolved_types["UpdateSchemaType"] == UserUpdate
        assert resolved_types["PrimaryKeyType"] == uuid.UUID

    @pytest.mark.asyncio
    async def test_detect_primary_key_type(self, user_router, category_router):
        """Test primary key type detection."""
        user_pk_type = user_router._detect_primary_key_type()
        assert user_pk_type is uuid.UUID

        category_pk_type = category_router._detect_primary_key_type()
        assert category_pk_type is int

    @pytest.mark.asyncio
    async def test_register_endpoints(self, user_router):
        """Test endpoint registration."""
        router = user_router.get_router()

        # Check that endpoints are registered
        routes = [route.path for route in router.routes]

        if user_router.enable_create:
            assert "/users" in routes or any("/users" in route for route in routes)

        if user_router.enable_read:
            assert any("/users/{id}" in route for route in routes)

        if user_router.enable_update:
            assert any("/users/{id}" in route for route in routes)

        if user_router.enable_delete:
            assert any("/users/{id}" in route for route in routes)

        if user_router.enable_list:
            assert any("/users" in route for route in routes)

    @pytest.mark.asyncio
    async def test_perform_create_success(self, user_router, db_session):
        """Test successful create operation."""
        user_data = create_test_user()

        created_user = await user_router.perform_create(db_session, user_data)

        assert created_user is not None
        assert created_user.username == user_data.username
        assert created_user.email == user_data.email
        assert created_user.id is not None

    @pytest.mark.asyncio
    async def test_perform_read_success(self, user_router, db_session):
        """Test successful read operation."""
        # Create a user
        user_data = create_test_user()
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Read user
        retrieved_user = await user_router.perform_read(db_session, user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.username == user.username

    @pytest.mark.asyncio
    async def test_perform_read_not_found(self, user_router, db_session):
        """Test read operation with non-existent ID."""
        non_existent_id = uuid.uuid4()

        with pytest.raises(NotFoundError):
            await user_router.perform_read(db_session, non_existent_id)

    @pytest.mark.asyncio
    async def test_perform_update_success(self, user_router, db_session):
        """Test successful update operation."""
        # Create a user
        user_data = create_test_user()
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Update user
        update_data = UserUpdate(full_name="Updated Name", age=30)
        updated_user = await user_router.perform_update(db_session, id=user.id, data=update_data)

        assert updated_user is not None
        assert updated_user.full_name == "Updated Name"
        assert updated_user.age == 30

    @pytest.mark.asyncio
    async def test_perform_update_not_found(self, user_router, db_session):
        """Test update operation with non-existent ID."""
        non_existent_id = uuid.uuid4()
        update_data = UserUpdate(full_name="Updated Name")

        with pytest.raises(NotFoundError):
            await user_router.perform_update(db_session, id=non_existent_id, data=update_data)

    @pytest.mark.asyncio
    async def test_perform_delete_success(self, user_router, db_session):
        """Test successful delete operation."""
        user_data = create_test_user()
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        user_id = user.id

        response = await user_router.perform_delete(db_session, user_id)

        assert response.status_code == 204

        result = await db_session.execute(select(User).where(User.id == user_id))
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_perform_delete_not_found(self, user_router, db_session):
        """Test delete operation with non-existent ID."""
        non_existent_id = uuid.uuid4()

        with pytest.raises(NotFoundError):
            await user_router.perform_delete(db_session, non_existent_id)

    @pytest.mark.asyncio
    async def test_perform_bulk_create_success(self, user_router: RouterFactory, db_session):
        """Test successful bulk create operation."""
        users_data = [
            create_test_user(),
            create_test_user(),
            create_test_user(),
        ]

        result = await user_router.perform_bulk_create(db_session, users_data)

        assert result["created"] == 3
        assert result.get("updated", 0) == 0
        assert result.get("deleted", 0) == 0
        assert len(result.get("errors", [])) == 0
        assert result["items"] is not None
        assert len(result["items"]) == 3

    @pytest.mark.asyncio
    async def test_perform_bulk_update_success(self, user_router, db_session):
        """Test successful bulk update operation."""
        # Create users
        users_data = [
            create_test_user(username="bulk_update1"),
            create_test_user(username="bulk_update2"),
        ]

        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Get created users
        result = await db_session.execute(
            select(User).where(User.username.in_(["bulk_update1", "bulk_update2"]))
        )
        users = result.scalars().all()

        # Prepare updates with user IDs
        updates = [
            UserUpdate(id=users[0].id, full_name="Updated 1"),
            UserUpdate(id=users[1].id, full_name="Updated 2"),
        ]

        bulk_result = await user_router.perform_bulk_update(db_session, updates)

        assert bulk_result.get("created", 0) == 0
        assert bulk_result["updated"] == 2
        assert bulk_result.get("deleted", 0) == 0
        assert len(bulk_result.get("errors", [])) == 0

    @pytest.mark.asyncio
    async def test_perform_bulk_delete_success(self, user_router: RouterFactory, db_session):
        """Test successful bulk delete operation."""
        # Create users
        users_data = [
            create_test_user(),
            create_test_user(),
            create_test_user(),
        ]

        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Get created users
        result = await db_session.execute(select(User).where(User.username.like("delete%")))
        users = result.scalars().all()
        user_ids = [user.id for user in users]

        # Delete users
        _ = await user_router.perform_bulk_delete(db_session, user_ids)

        result = await db_session.execute(select(User).where(User.id.in_(user_ids)))
        assert len(result.scalars().all()) == 0

    @pytest.mark.asyncio
    async def test_generate_response_schema(self, user_router: RouterFactory):
        """Test response schema generation."""
        schema = user_router._generate_response_schema()
        assert schema is not None

    @pytest.mark.asyncio
    async def test_get_python_type(self, user_router):
        """Test Python type detection from SQL types."""
        # Test various SQL types
        from sqlalchemy import Boolean, DateTime, Integer, String

        assert user_router._get_python_type(String()) is str
        assert user_router._get_python_type(Integer()) is int
        assert user_router._get_python_type(Boolean()) is bool
        assert user_router._get_python_type(DateTime()) is datetime

    @pytest.mark.asyncio
    async def test_get_response_model(self, user_router):
        """Test response model retrieval."""
        # Test different response model types
        create_model = user_router._get_response_model("create")
        assert create_model is not None

        read_model = user_router._get_response_model("read")
        assert read_model is not None

        list_model = user_router._get_response_model("list")
        assert list_model is not None

    @pytest.mark.asyncio
    async def test_router_with_hooks(self, session_factory):
        """Test RouterFactory with custom hooks."""
        from tests.conftest import TestHooks

        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User, hooks=TestHooks()),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
        )

        assert router.crud.hooks is not None
        assert isinstance(router.crud.hooks, TestHooks)

    @pytest.mark.asyncio
    async def test_router_with_dependencies(self, session_factory):
        """Test RouterFactory with custom dependencies."""

        def custom_dependency():
            return "custom_value"

        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            dependencies=[custom_dependency],
        )

        assert len(router.dependencies) == 1
        assert router.dependencies[0] == custom_dependency

    @pytest.mark.asyncio
    async def test_router_with_response_schemas(self, session_factory):
        """Test RouterFactory with custom response schemas."""

        class CustomResponse(BaseModel):
            custom_field: str

        response_schemas: Dict[
            Literal[
                "create", "update", "read", "list", "bulk_create", "bulk_update", "bulk_delete"
            ],
            Type[BaseModel],
        ] = {
            "create": CustomResponse,
            "read": CustomResponse,
        }

        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            response_schemas=response_schemas,
        )

        assert router.response_schemas == response_schemas

    @pytest.mark.asyncio
    async def test_router_feature_toggles(self, session_factory):
        """Test RouterFactory with different feature toggles."""
        # Test with all features disabled
        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            enable_create=False,
            enable_read=False,
            enable_update=False,
            enable_delete=False,
            enable_list=False,
            enable_bulk_create=False,
            enable_bulk_update=False,
            enable_bulk_delete=False,
            enable_pagination=False,
        )

        assert router.enable_create is False
        assert router.enable_read is False
        assert router.enable_update is False
        assert router.enable_delete is False
        assert router.enable_list is False
        assert router.enable_bulk_create is False
        assert router.enable_bulk_update is False
        assert router.enable_bulk_delete is False
        assert router.enable_pagination is False

    @pytest.mark.asyncio
    async def test_router_pagination_settings(self, session_factory):
        """Test RouterFactory pagination settings."""
        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            page_size=50,
            max_page_size=200,
        )

        assert router.page_size == 50
        assert router.max_page_size == 200


class TestRouterFactoryIntegration:
    """Test suite for RouterFactory FastAPI integration."""

    @pytest.mark.asyncio
    async def test_router_integration_with_fastapi(self, user_router, app):
        app.include_router(user_router.get_router())

        _ = TestClient(app)

        assert len(app.routes) > 0

    @pytest.mark.asyncio
    async def test_router_endpoint_creation(self, user_router):
        """Test that router creates the expected endpoints."""
        router = user_router.get_router()

        # Get all route paths
        paths = []
        for route in router.routes:
            if hasattr(route, "path"):
                paths.append(route.path)

        # Check for expected endpoints
        expected_paths = []

        if user_router.enable_create:
            expected_paths.append("/users")

        if user_router.enable_read:
            expected_paths.append("/users/{id}")

        if user_router.enable_update:
            expected_paths.append("/users/{id}")

        if user_router.enable_delete:
            expected_paths.append("/users/{id}")

        if user_router.enable_list:
            expected_paths.append("/users")

        if (
            user_router.enable_bulk_create
            or user_router.enable_bulk_update
            or user_router.enable_bulk_delete
        ):
            expected_paths.extend(["/users/bulk", "/users/bulk/update", "/users/bulk/delete"])

        # Check that at least some expected paths are present
        assert any(path in paths for path in expected_paths)

    @pytest.mark.asyncio
    async def test_router_with_different_primary_key_types(self, session_factory):
        """Test router with different primary key types."""
        # Test with UUID primary key (User)
        user_router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
        )

        assert user_router._resolved_types["PrimaryKeyType"] == uuid.UUID

        # Test with integer primary key (Category)
        category_router = RouterFactory(
            crud=BaseCRUD[Category, int, CategoryCreate, CategoryUpdate](model=Category),
            session_factory=session_factory,
            create_schema=CategoryCreate,
            update_schema=CategoryUpdate,
        )

        assert category_router._resolved_types["PrimaryKeyType"] is int

    @pytest.mark.asyncio
    async def test_router_with_dynamic_list_endpoint(self, session_factory):
        """Test router with dynamic list endpoint parameters."""
        # Test with all features enabled
        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            enable_search=True,
            enable_sorting=True,
            enable_filters=True,
            search_fields=["username", "email"],
            sort_default="-created_at",
            filter_spec={"username": ("eq", "in", "contains")},
        )

        assert router.enable_search is True
        assert router.enable_sorting is True
        assert router.enable_filters is True

        # Test that the list endpoint function is created correctly
        list_endpoint = router._create_list_endpoint()
        assert callable(list_endpoint)

        # Test with only search enabled
        router_search_only = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            enable_search=True,
            enable_sorting=False,
            enable_filters=False,
        )

        assert router_search_only.enable_search is True
        assert router_search_only.enable_sorting is False
        assert router_search_only.enable_filters is False

        # Test with only sorting enabled
        router_sort_only = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            enable_search=False,
            enable_sorting=True,
            enable_filters=False,
        )

        assert router_sort_only.enable_search is False
        assert router_sort_only.enable_sorting is True
        assert router_sort_only.enable_filters is False

        # Test with only filters enabled
        router_filters_only = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            enable_search=False,
            enable_sorting=False,
            enable_filters=True,
        )

        assert router_filters_only.enable_search is False
        assert router_filters_only.enable_sorting is False
        assert router_filters_only.enable_filters is True

    @pytest.mark.asyncio
    async def test_router_with_custom_prefix(self, session_factory):
        """Test router with custom prefix."""
        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            prefix="custom-prefix",
        )

        assert router.prefix == "/custom-prefix"

    @pytest.mark.asyncio
    async def test_router_with_custom_tags(self, session_factory):
        """Test router with custom tags."""
        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            tags=["custom", "users"],
        )

        assert router.tags == ["custom", "users"]

    @pytest.mark.asyncio
    async def test_router_with_enum_tags(self, session_factory):
        """Test router with enum tags."""
        from enum import Enum

        class UserTags(Enum):
            USERS = "users"
            ADMIN = "admin"

        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            tags=[UserTags.USERS, UserTags.ADMIN],
        )

        assert len(router.tags) == 2
        assert UserTags.USERS in router.tags
        assert UserTags.ADMIN in router.tags


class TestRouterFactoryEdgeCases:
    """Test suite for RouterFactory edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_router_with_empty_prefix(self, session_factory):
        """Test router with empty prefix."""
        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            prefix="",
        )

        assert router.prefix == ""

    @pytest.mark.asyncio
    async def test_router_with_prefix_without_slash(self, session_factory):
        """Test router with prefix without leading slash."""
        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            prefix="users",
        )

        assert router.prefix == "/users"

    @pytest.mark.asyncio
    async def test_router_with_none_tags(self, session_factory):
        """Test router with None tags."""
        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            tags=None,
        )

        assert router.tags == []

    @pytest.mark.asyncio
    async def test_router_with_none_dependencies(self, session_factory):
        """Test router with None dependencies."""
        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            dependencies=None,
        )

        assert router.dependencies == []

    @pytest.mark.asyncio
    async def test_router_with_none_search_fields(self, session_factory):
        """Test router with None search fields."""
        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            search_fields=None,
        )

        assert router.search_fields == []

    @pytest.mark.asyncio
    async def test_router_with_none_prefetch(self, session_factory):
        """Test router with None prefetch."""
        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            prefetch=None,
        )

        assert router.prefetch == []

    @pytest.mark.asyncio
    async def test_router_bulk_operations_with_empty_data(self, user_router, db_session):
        """Test bulk operations with empty data."""
        # Test bulk create with empty list
        result = await user_router.perform_bulk_create(db_session, [])
        assert result.get("created", 0) == 0
        assert result.get("updated", 0) == 0
        assert result.get("deleted", 0) == 0
        assert len(result.get("errors", [])) == 0

        # Test bulk update with empty list
        result = await user_router.perform_bulk_update(db_session, [])
        assert result.get("created", 0) == 0
        assert result.get("updated", 0) == 0
        assert result.get("deleted", 0) == 0
        assert len(result.get("errors", [])) == 0

    @pytest.mark.asyncio
    async def test_router_with_mismatched_schemas(self, session_factory):
        """Test router with mismatched schemas."""

        class MismatchedSchema(BaseModel):
            field1: str

        # This should work but the schemas don't match the model
        router = RouterFactory(
            crud=BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User),
            session_factory=session_factory,
            create_schema=MismatchedSchema,
            update_schema=MismatchedSchema,
        )

        assert router.create_schema == MismatchedSchema
        assert router.update_schema == MismatchedSchema
