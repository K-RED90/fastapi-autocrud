import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auto_crud.core.crud.base import BaseCRUD, CRUDHooks
from auto_crud.core.schemas.pagination import (
    FilterParam,
    Pagination,
)
from tests.conftest import (
    Post,
    TestHooks,
    User,
    UserCreate,
    UserUpdate,
    create_test_post,
    create_test_user,
)


class TestBaseCRUD:
    """Test suite for BaseCRUD class."""

    @pytest.mark.asyncio
    async def test_crud_initialization(self, user_crud):
        """Test CRUD initialization."""
        assert user_crud.model == User
        assert user_crud.hooks is not None
        assert user_crud.query_filter is not None
        assert user_crud.pk == ["id"]

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, user_crud, db_session):
        """Test successful get_by_id operation."""
        # Create a user
        user_data = create_test_user()
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Get user by ID
        retrieved_user = await user_crud.get_by_id(db_session, user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.username == user.username
        assert retrieved_user.email == user.email

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, user_crud, db_session):
        """Test get_by_id with non-existent ID."""
        non_existent_id = uuid.uuid4()
        user = await user_crud.get_by_id(db_session, non_existent_id)
        assert user is None

    @pytest.mark.asyncio
    async def test_get_by_id_with_include(self, user_crud, db_session):
        """Test get_by_id with include parameter."""
        # Create a user with posts
        user_data = create_test_user()
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create a post for the user
        post_data = create_test_post(user.id)
        post = Post(**post_data.model_dump())
        db_session.add(post)
        await db_session.commit()

        # Get user with posts included
        retrieved_user = await user_crud.get_by_id(db_session, user.id, prefetch=["posts"])

        assert retrieved_user is not None
        assert len(retrieved_user.posts) == 1
        assert retrieved_user.posts[0].title == post.title

    @pytest.mark.asyncio
    async def test_get_one_success(self, user_crud, db_session):
        """Test successful get_one operation."""
        # Create a user
        user_data = create_test_user()
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Get user by username
        filters = [FilterParam(field="username", operator="eq", value=user.username)]
        retrieved_user = await user_crud.get_one(db_session, filters)

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.username == user.username

    @pytest.mark.asyncio
    async def test_get_one_not_found(self, user_crud, db_session):
        """Test get_one with non-existent filters."""
        filters = [FilterParam(field="username", operator="eq", value="non_existent")]
        user = await user_crud.get_one(db_session, filters)
        assert user is None

    @pytest.mark.asyncio
    async def test_create_success(self, user_crud, db_session):
        """Test successful create operation."""
        user_data = create_test_user()

        created_user = await user_crud.create(db_session, user_data)

        assert created_user is not None
        assert created_user.username == user_data.username
        assert created_user.email == user_data.email
        assert created_user.id is not None

    @pytest.mark.asyncio
    async def test_create_with_dict(self, user_crud, db_session):
        """Test create operation with dictionary input."""
        user_dict = {
            "username": "dictuser",
            "email": "dict@example.com",
            "password": "password123",
            "full_name": "Dict User",
        }

        created_user = await user_crud.create(db_session, user_dict)

        assert created_user is not None
        assert created_user.username == user_dict["username"]
        assert created_user.email == user_dict["email"]

    @pytest.mark.asyncio
    async def test_create_with_include(self, user_crud: BaseCRUD, db_session: AsyncSession):
        """Test create operation with include parameter."""
        user_data = create_test_user()

        created_user = await user_crud.create(db_session, user_data, prefetch=["posts"])

        assert created_user is not None
        assert hasattr(created_user, "posts")

    @pytest.mark.asyncio
    async def test_update_success(self, user_crud, db_session):
        """Test successful update operation."""
        # Create a user
        user_data = create_test_user()
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Update user
        update_data = UserUpdate(full_name="Updated Name", age=30)
        updated_user = await user_crud.update(db_session, user, update_data)

        assert updated_user is not None
        assert updated_user.full_name == "Updated Name"
        assert updated_user.age == 30
        assert updated_user.username == user.username  # Unchanged

    @pytest.mark.asyncio
    async def test_update_with_dict(self, user_crud, db_session):
        """Test update operation with dictionary input."""
        # Create a user
        user_data = create_test_user()
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Update user with dict
        update_dict = {"full_name": "Dict Updated Name", "age": 35}
        updated_user = await user_crud.update(db_session, user, update_dict)

        assert updated_user is not None
        assert updated_user.full_name == "Dict Updated Name"
        assert updated_user.age == 35

    @pytest.mark.asyncio
    async def test_delete_success(self, user_crud, db_session):
        """Test successful delete operation."""
        # Create a user
        user_data = create_test_user()
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        user_id = user.id

        # Delete user
        deleted_user = await user_crud.delete(db_session, user)

        assert deleted_user is not None
        assert deleted_user.id == user_id

        # Verify user is deleted
        result = await db_session.execute(select(User).where(User.id == user_id))
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_delete_by_id_success(self, user_crud, db_session):
        """Test successful delete_by_id operation."""
        # Create a user
        user_data = create_test_user()
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        user_id = user.id

        # Delete user by ID
        deleted_count = await user_crud.delete_by_id(db_session, user_id)

        assert deleted_count == 1

        # Verify user is deleted
        result = await db_session.execute(select(User).where(User.id == user_id))
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_delete_by_id_not_found(self, user_crud, db_session):
        """Test delete_by_id with non-existent ID."""
        non_existent_id = uuid.uuid4()
        deleted_count = await user_crud.delete_by_id(db_session, non_existent_id)
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_get_or_create_new(self, user_crud, db_session):
        """Test get_or_create with new user."""
        user_id = uuid.uuid4()
        defaults = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
        }

        user, created = await user_crud.get_or_create(db_session, user_id, defaults)

        assert created is True
        assert user is not None
        assert user.id == user_id
        assert user.username == defaults["username"]

    @pytest.mark.asyncio
    async def test_get_or_create_existing(self, user_crud, db_session):
        """Test get_or_create with existing user."""
        # Create a user
        user_data = create_test_user()
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        defaults = {"username": "different", "email": "different@example.com"}

        retrieved_user, created = await user_crud.get_or_create(db_session, user.id, defaults)

        assert created is False
        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.username == user.username  # Original username

    @pytest.mark.asyncio
    async def test_search_success(self, user_crud, db_session):
        """Test successful search operation."""
        # Create users with different names
        users_data = [
            create_test_user(username="john_doe"),
            create_test_user(username="jane_smith"),
            create_test_user(username="bob_wilson"),
        ]

        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Search for users with "john" in username
        results = await user_crud.search(db_session, "john", fields=["username"])

        assert len(results) == 1
        assert "john" in results[0].username.lower()

    @pytest.mark.asyncio
    async def test_search_with_relations(self, user_crud: BaseCRUD, db_session: AsyncSession):
        """Test search operation with relations."""
        # Create a user with posts
        user_data = create_test_user(username="testuser_unique")
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create a post
        post_data = create_test_post(user.id, title="Test Post")
        post = Post(**post_data.model_dump())
        db_session.add(post)
        await db_session.commit()

        # Search with relations
        results = await user_crud.search(
            db_session, "testuser_unique", fields=["username"], prefetch=["posts"]
        )

        assert len(results) == 1
        assert len(results[0].posts) == 1

    @pytest.mark.asyncio
    async def test_count_success(self, user_crud, db_session):
        """Test successful count operation."""
        # Create multiple users
        users_data = [
            create_test_user(username="count1_unique"),
            create_test_user(username="count2_unique"),
            create_test_user(username="count3_unique"),
        ]

        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Count users with specific usernames
        filters = [
            FilterParam(
                field="username",
                operator="in",
                value=["count1_unique", "count2_unique", "count3_unique"],
            )
        ]
        count = await user_crud.count(db_session, filters)
        assert count == 3

    @pytest.mark.asyncio
    async def test_count_with_filters(self, user_crud, db_session):
        """Test count operation with filters."""
        # Create users with different ages
        users_data = [
            create_test_user(),
            create_test_user(),
            create_test_user(),
        ]

        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Count users with age >= 30
        filters = [FilterParam(field="age", operator="ge", value=30)]
        count = await user_crud.count(db_session, filters)
        assert count == 2

    @pytest.mark.asyncio
    async def test_exists_success(self, user_crud, db_session):
        """Test successful exists operation."""
        # Create a user
        user_data = create_test_user()
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Check if user exists
        exists = await user_crud.exists(db_session, user.id)
        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_not_found(self, user_crud, db_session):
        """Test exists operation with non-existent ID."""
        non_existent_id = uuid.uuid4()
        exists = await user_crud.exists(db_session, non_existent_id)
        assert exists is False

    @pytest.mark.asyncio
    async def test_bulk_create_success(self, user_crud, db_session):
        """Test successful bulk_create operation."""
        users_data = [
            create_test_user(username="bulk1"),
            create_test_user(username="bulk2"),
            create_test_user(username="bulk3"),
        ]

        created_users = await user_crud.bulk_create(db_session, users_data)

        assert len(created_users) == 3
        assert all("bulk" in user.username for user in created_users)

    @pytest.mark.asyncio
    async def test_bulk_create_with_dicts(self, user_crud, db_session):
        """Test bulk_create operation with dictionaries."""
        users_dicts = [
            {
                "username": "dict1",
                "email": "dict1@example.com",
                "password": "password123",
            },
            {
                "username": "dict2",
                "email": "dict2@example.com",
                "password": "password456",
            },
        ]

        created_users = await user_crud.bulk_create(db_session, users_dicts)

        assert len(created_users) == 2
        assert all(user.username.startswith("dict") for user in created_users)

    @pytest.mark.asyncio
    async def test_bulk_update_success(self, user_crud, db_session):
        """Test successful bulk_update operation."""
        # Create users
        users_data = [
            create_test_user(username="update1"),
            create_test_user(username="update2"),
        ]

        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Get created users
        result = await db_session.execute(select(User).where(User.username.like("update%")))
        users = result.scalars().all()

        # Prepare updates
        updates = [
            {"id": users[0].id, "full_name": "Updated 1"},
            {"id": users[1].id, "full_name": "Updated 2"},
        ]

        updated_count = await user_crud.bulk_update(db_session, updates)
        assert updated_count == 2

    @pytest.mark.asyncio
    async def test_bulk_delete_success(self, user_crud, db_session):
        """Test successful bulk_delete operation."""
        # Create users
        users_data = [
            create_test_user(username="delete1"),
            create_test_user(username="delete2"),
            create_test_user(username="delete3"),
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
        deleted_count = await user_crud.bulk_delete(db_session, user_ids)
        assert deleted_count == 3

        # Verify users are deleted
        result = await db_session.execute(select(User).where(User.id.in_(user_ids)))
        assert len(result.scalars().all()) == 0

    @pytest.mark.asyncio
    async def test_get_multi_success(self, user_crud, db_session):
        """Test successful get_multi operation."""
        # Create users
        users_data = [
            create_test_user(username="multi1_unique"),
            create_test_user(username="multi2_unique"),
            create_test_user(username="multi3_unique"),
        ]

        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Get users with specific usernames
        filters = [
            FilterParam(
                field="username",
                operator="in",
                value=["multi1_unique", "multi2_unique", "multi3_unique"],
            )
        ]
        users = await user_crud.list_objects(db_session, filters=filters)
        assert len(users) == 3

    @pytest.mark.asyncio
    async def test_get_multi_with_filters(self, user_crud, db_session):
        """Test get_multi operation with filters."""
        # Create users with different ages
        users_data = [
            create_test_user(),
            create_test_user(),
            create_test_user(),
        ]

        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Get users with age >= 30
        filters = [FilterParam(field="age", operator="ge", value=30)]
        users = await user_crud.list_objects(db_session, filters=filters)
        assert len(users) == 2
        assert all(user.age >= 30 for user in users)

    @pytest.mark.asyncio
    async def test_get_multi_with_search(self, user_crud, db_session):
        """Test get_multi operation with search."""
        # Create users
        users_data = [
            create_test_user(username="search1"),
            create_test_user(username="search2"),
            create_test_user(username="other"),
        ]

        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Search for users with "search" in username
        users = await user_crud.list_objects(
            db_session, search="search", search_fields=["username"]
        )
        assert len(users) == 2
        assert all("search" in user.username for user in users)

    @pytest.mark.asyncio
    async def test_get_multi_with_sorting(self, user_crud, db_session):
        """Test get_multi operation with sorting."""
        # Create users with different ages
        users_data = [
            create_test_user(username="sort1_unique", age=25),
            create_test_user(username="sort2_unique", age=30),
            create_test_user(username="sort3_unique", age=35),
        ]

        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Sort by age ascending for specific users
        filters = [
            FilterParam(
                field="username",
                operator="in",
                value=["sort1_unique", "sort2_unique", "sort3_unique"],
            )
        ]
        sorting = "age"
        users = await user_crud.list_objects(db_session, filters=filters, sorting=sorting)
        assert len(users) == 3
        assert users[0].age <= users[1].age <= users[2].age

    @pytest.mark.asyncio
    async def test_apply_pagination_success(self, user_crud, db_session):
        """Test successful apply_pagination operation."""
        # Create users
        users_data = [
            create_test_user(username="page1_unique"),
            create_test_user(username="page2_unique"),
            create_test_user(username="page3_unique"),
            create_test_user(username="page4_unique"),
            create_test_user(username="page5_unique"),
        ]

        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Test pagination with specific filter
        query = select(User).where(
            User.username.in_(
                ["page1_unique", "page2_unique", "page3_unique", "page4_unique", "page5_unique"]
            )
        )
        pagination = Pagination(page=1, size=2)
        sorting = "username"

        result = await user_crud.apply_pagination(db_session, query, pagination)

        assert result.total == 5
        assert result.page == 1
        assert result.size == 2
        assert result.pages == 3
        assert result.has_next is True
        assert result.has_prev is False
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_apply_pagination_with_filters(
        self, user_crud: BaseCRUD, db_session: AsyncSession
    ):
        """Test apply_pagination operation with filters."""
        # Create users with different ages
        users_data = [
            create_test_user(username="filter1_unique", age=25),
            create_test_user(username="filter2_unique", age=30),
            create_test_user(username="filter3_unique", age=35),
            create_test_user(username="filter4_unique", age=40),
        ]

        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Test pagination with age filter for specific users
        query = select(User).where(
            User.username.in_(
                ["filter1_unique", "filter2_unique", "filter3_unique", "filter4_unique"]
            )
        )
        pagination = Pagination(page=1, size=2)
        filters = [FilterParam(field="age", operator="ge", value=30)]

        query = user_crud.query_filter.apply_filters(query, filters)

        result = await user_crud.apply_pagination(db_session, query, pagination)

        assert result.total == 3  # Only users with age >= 30
        assert len(result.items) == 2  # Page size is 2
        assert all(user.age >= 30 for user in result.items)

    @pytest.mark.asyncio
    async def test_apply_pagination_with_search(
        self, user_crud: BaseCRUD, db_session: AsyncSession
    ):
        """Test apply_pagination operation with search."""
        # Create users
        users_data = [
            create_test_user(username="search1_unique"),
            create_test_user(username="search2_unique"),
            create_test_user(username="other_unique"),
        ]

        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        search = "search"
        search_fields = ["username"]

        result = await user_crud.list_objects(
            db_session,
            filters=[
                FilterParam(
                    field="username",
                    operator="in",
                    value=["search1_unique", "search2_unique", "other_unique"],
                )
            ],
            pagination={
                "page": 1,
                "size": 10,
            },
            search=search,
            search_fields=search_fields,
        )

        assert not isinstance(result, list)

        assert result.total == 2
        assert len(result) == 2
        assert all("search" in user.username for user in result.items)

    @pytest.mark.asyncio
    async def test_get_multi_paginated_success(self, user_crud, db_session):
        """Test successful get_multi_paginated operation."""
        # Create users
        users_data = [
            create_test_user(username="paginated1_unique"),
            create_test_user(username="paginated2_unique"),
            create_test_user(username="paginated3_unique"),
        ]

        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Test paginated retrieval with specific filter
        pagination = Pagination(page=1, size=2)
        filters = [
            FilterParam(
                field="username",
                operator="in",
                value=["paginated1_unique", "paginated2_unique", "paginated3_unique"],
            )
        ]
        sorting = "username"

        result = await user_crud.list_objects(
            db_session, filters=filters, sorting=sorting, pagination=pagination
        )

        assert result.total == 3
        assert result.page == 1
        assert result.size == 2
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_get_multi_paginated_with_filters(self, user_crud, db_session):
        """Test get_multi_paginated operation with filters."""
        # Create users with different ages
        users_data = [
            create_test_user(username="filtered1_unique", age=25),
            create_test_user(username="filtered2_unique", age=30),
            create_test_user(username="filtered3_unique", age=35),
        ]

        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Test paginated retrieval with filters for specific users
        pagination = Pagination(page=1, size=10)
        filters = [
            FilterParam(
                field="username",
                operator="in",
                value=["filtered1_unique", "filtered2_unique", "filtered3_unique"],
            ),
            FilterParam(field="age", operator="ge", value=30),
        ]

        result = await user_crud.list_objects(db_session, filters=filters, pagination=pagination)

        assert result.total == 2
        assert len(result.items) == 2
        assert all(user.age >= 30 for user in result.items)

    @pytest.mark.asyncio
    async def test_primary_key_property(self, user_crud, category_crud):
        """Test primary key property."""
        # User has UUID primary key
        assert user_crud.pk == ["id"]

        # Category has integer primary key
        assert category_crud.pk == ["id"]

    @pytest.mark.asyncio
    async def test_apply_prefetch(self, user_crud, db_session):
        """Test _apply_prefetch method."""
        # Create a user with posts
        user_data = create_test_user(username="include_test")
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create a post
        post_data = create_test_post(user.id)
        post = Post(**post_data.model_dump())
        db_session.add(post)
        await db_session.commit()

        # Test applying prefetch
        query = select(User).where(User.username == "include_test")
        query_with_prefetch = user_crud._apply_prefetch(query, ["posts"])

        # Execute query
        result = await db_session.execute(query_with_prefetch)
        user_with_posts = result.scalar_one()

        assert user_with_posts is not None
        assert len(user_with_posts.posts) == 1
        assert user_with_posts.posts[0].title == post.title

    @pytest.mark.asyncio
    async def test_get_model_relations(self, user_crud):
        """Test _get_model_relations method."""
        # Test with no specific relations
        relations = user_crud._get_model_relations()
        assert "posts" in relations

        # Test with specific relations
        relations = user_crud._get_model_relations(["posts"])
        assert "posts" in relations

    @pytest.mark.asyncio
    async def test_build_relation_loaders(self, user_crud):
        """Test _build_relation_loaders method."""
        loaders = user_crud._build_relation_loaders(["posts"])
        assert len(loaders) == 1
        assert loaders[0] is not None


class TestCRUDHooks:
    """Test suite for CRUDHooks class."""

    @pytest.mark.asyncio
    async def test_hooks_initialization(self, user_crud_with_hooks):
        """Test hooks initialization."""
        assert user_crud_with_hooks.hooks is not None
        assert isinstance(user_crud_with_hooks.hooks, TestHooks)

    @pytest.mark.asyncio
    async def test_pre_create_hook(self, user_crud_with_hooks, db_session):
        """Test pre_create hook."""
        user_data = create_test_user(username="original")

        created_user = await user_crud_with_hooks.create(db_session, user_data)

        # Check that pre_create hook modified the username
        assert created_user.username == "test_original"

    @pytest.mark.asyncio
    async def test_post_create_hook(self, user_crud_with_hooks, db_session):
        """Test post_create hook."""
        user_data = create_test_user()

        created_user = await user_crud_with_hooks.create(db_session, user_data)

        # Check that post_create hook set is_verified to True
        assert created_user.is_verified is True

    @pytest.mark.asyncio
    async def test_pre_delete_hook_allow(self, user_crud_with_hooks, db_session):
        """Test pre_delete hook allowing deletion."""
        # Create an inactive user
        user_data = create_test_user()
        user = User(**user_data.model_dump(), is_active=False)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Delete should succeed for inactive user
        deleted_user = await user_crud_with_hooks.delete(db_session, user)
        assert deleted_user is not None

    @pytest.mark.asyncio
    async def test_pre_delete_hook_prevent(self, user_crud_with_hooks, db_session):
        """Test pre_delete hook preventing deletion."""
        # Create an active user
        user_data = create_test_user()
        user = User(**user_data.model_dump(), is_active=True)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Delete should fail for active user
        with pytest.raises(Exception):  # The exact exception depends on implementation
            await user_crud_with_hooks.delete(db_session, user)

    @pytest.mark.asyncio
    async def test_hooks_inheritance(self):
        """Test that hooks can be inherited and customized."""

        class CustomHooks(CRUDHooks[User, uuid.UUID, UserCreate, UserUpdate]):
            async def pre_create(
                self, db_session: AsyncSession, obj_in: UserCreate, *args, **kwargs
            ) -> UserCreate:
                obj_in.username = f"custom_{obj_in.username}"
                return obj_in

        crud = BaseCRUD(User, hooks=CustomHooks())
        assert isinstance(crud.hooks, CustomHooks)

    @pytest.mark.asyncio
    async def test_default_hooks_behavior(self, user_crud, db_session):
        """Test default hooks behavior (should not modify data)."""
        user_data = create_test_user(username="default")

        created_user = await user_crud.create(db_session, user_data)

        # Default hooks should not modify the username
        assert created_user.username == "default"
        assert created_user.is_verified is False  # Default value


class TestBaseCRUDEdgeCases:
    """Test suite for BaseCRUD edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_create_with_invalid_data(self, user_crud, db_session):
        """Test create with invalid data."""
        # Test with missing required fields
        invalid_data = {"username": "test"}  # Missing email and password

        with pytest.raises(Exception):  # Should raise validation error
            await user_crud.create(db_session, invalid_data)

    @pytest.mark.asyncio
    async def test_get_by_id_with_invalid_id_type(self, user_crud, db_session):
        """Test get_by_id with invalid ID type."""
        # Test with string ID instead of UUID
        with pytest.raises(Exception):  # Should raise type error
            await user_crud.get_by_id(db_session, "invalid-id")

    @pytest.mark.asyncio
    async def test_bulk_operations_with_empty_lists(self, user_crud, db_session):
        """Test bulk operations with empty lists."""
        # Test bulk_create with empty list
        created_users = await user_crud.bulk_create(db_session, [])
        assert len(created_users) == 0

        # Test bulk_update with empty list
        updated_count = await user_crud.bulk_update(db_session, [])
        assert updated_count == 0

        # Test bulk_delete with empty list
        deleted_count = await user_crud.bulk_delete(db_session, [])
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_pagination_edge_cases(self, user_crud, db_session):
        """Test pagination edge cases."""
        # Test pagination with no results
        query = select(User).where(User.username == "non_existent")
        pagination = Pagination(page=1, size=10)

        result = await user_crud.apply_pagination(db_session, query, pagination)

        assert result.total == 0
        assert result.page == 1
        assert result.size == 10
        assert result.pages == 1
        assert result.has_next is False
        assert result.has_prev is False
        assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_search_with_empty_fields(
        self, user_crud: BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate], db_session: AsyncSession
    ):
        """Test search with empty search fields."""
        # Create a user
        user_data = create_test_user(username="empty_search_test_unique")
        user = User(**user_data.model_dump())
        db_session.add(user)
        await db_session.commit()

        # Search with empty fields list
        results = await user_crud.search(db_session, "empty_search_test_unique", fields=[])
        assert len(results) == 0  # Should return empty when no fields specified

    @pytest.mark.asyncio
    async def test_get_multi_with_invalid_filters(self, user_crud, db_session):
        """Test get_multi with invalid filters."""
        # Test with non-existent field
        filters = [FilterParam(field="non_existent_field", operator="eq", value="test")]

        with pytest.raises(Exception):  # Should raise filter error
            await user_crud.list_objects(db_session, filters=filters)
