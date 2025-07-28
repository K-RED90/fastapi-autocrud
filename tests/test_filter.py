import random
import uuid
from datetime import datetime

import pytest
from sqlalchemy import delete, select

from auto_crud.core.crud.filter import QueryFilter
from auto_crud.core.errors import FilterError
from auto_crud.core.schemas.pagination import FilterParam
from tests.conftest import (
    User,
    create_test_user,
)


def unique_name(base):
    return f"{base}_{random.randint(100000, 999999)}"


@pytest.fixture(autouse=True)
async def clear_users_table(db_session):
    await db_session.execute(delete(User))
    await db_session.commit()


class TestQueryFilter:
    """Test suite for QueryFilter class."""

    @pytest.mark.asyncio
    async def test_get_column_type_category(self, query_filter):
        """Test column type category detection."""
        # Test string columns
        username_col = User.username
        assert query_filter._get_column_type_category(username_col) == "string"

        # Test numeric columns
        age_col = User.age
        assert query_filter._get_column_type_category(age_col) == "numeric"

        # Test boolean columns
        is_active_col = User.is_active
        assert query_filter._get_column_type_category(is_active_col) == "boolean"

        # Test datetime columns
        created_at_col = User.created_at
        assert query_filter._get_column_type_category(created_at_col) == "datetime"

        # Test UUID columns
        id_col = User.id
        assert query_filter._get_column_type_category(id_col) == "uuid"

    @pytest.mark.asyncio
    async def test_validate_operator_for_field_success(self, query_filter):
        """Test successful operator validation."""
        # Test valid string operators
        assert query_filter._validate_operator_for_field("username", "eq") is True
        assert query_filter._validate_operator_for_field("username", "like") is True
        assert query_filter._validate_operator_for_field("username", "contains") is True

        # Test valid numeric operators
        assert query_filter._validate_operator_for_field("age", "gt") is True
        assert query_filter._validate_operator_for_field("age", "between") is True

        # Test valid boolean operators
        assert query_filter._validate_operator_for_field("is_active", "eq") is True

        # Test valid datetime operators
        assert query_filter._validate_operator_for_field("created_at", "ge") is True

        # Test logical operators
        assert query_filter._validate_operator_for_field("username", "and") is True
        assert query_filter._validate_operator_for_field("username", "or") is True
        assert query_filter._validate_operator_for_field("username", "not") is True

    @pytest.mark.asyncio
    async def test_validate_operator_for_field_invalid_field(self, query_filter):
        """Test operator validation with invalid field."""
        with pytest.raises(FilterError, match="Field 'non_existent' not found"):
            query_filter._validate_operator_for_field("non_existent", "eq")

    @pytest.mark.asyncio
    async def test_validate_operator_for_field_invalid_operator(self, query_filter):
        """Test operator validation with invalid operator."""
        with pytest.raises(FilterError, match="Operator 'invalid_op' is not allowed"):
            query_filter._validate_operator_for_field("username", "invalid_op")

    @pytest.mark.asyncio
    async def test_safe_cast_value(self, query_filter):
        """Test safe value casting."""
        # Test string values
        username_col = User.username
        assert query_filter._safe_cast_value(username_col, "test") == "test"
        assert query_filter._safe_cast_value(username_col, 123) == "123"

        # Test numeric values
        age_col = User.age
        assert query_filter._safe_cast_value(age_col, "25") == 25
        assert query_filter._safe_cast_value(age_col, 25) == 25

        # Test boolean values
        is_active_col = User.is_active
        assert query_filter._safe_cast_value(is_active_col, "true") is True
        assert query_filter._safe_cast_value(is_active_col, True) is True

        # Test datetime values
        created_at_col = User.created_at
        dt = datetime.now()
        assert query_filter._safe_cast_value(created_at_col, dt) == dt

        # Test UUID values
        id_col = User.id
        test_uuid = uuid.uuid4()
        assert query_filter._safe_cast_value(id_col, str(test_uuid)) == test_uuid

    @pytest.mark.asyncio
    async def test_validate_filter_value(self, query_filter):
        """Test filter value validation."""
        # Test valid string values
        username_col = User.username
        assert query_filter._validate_filter_value(username_col, "eq", "test") == "test"

        # Test valid numeric values
        age_col = User.age
        assert query_filter._validate_filter_value(age_col, "eq", 25) == 25

        # Test valid boolean values
        is_active_col = User.is_active
        assert query_filter._validate_filter_value(is_active_col, "eq", True) is True

        # Test valid datetime values
        created_at_col = User.created_at
        dt = datetime.now()
        assert query_filter._validate_filter_value(created_at_col, "eq", dt) == dt

    @pytest.mark.asyncio
    async def test_build_simple_filter_condition(self, query_filter: QueryFilter):
        """Test building simple filter conditions."""
        # Test equality filter
        filter_param = FilterParam(field="username", operator="eq", value="test")
        condition = query_filter._build_simple_filter_condition(filter_param)
        assert condition is not None

        # Test greater than filter
        filter_param = FilterParam(field="age", operator="gt", value=25)
        condition = query_filter._build_simple_filter_condition(filter_param)
        assert condition is not None

        # Test like filter
        filter_param = FilterParam(field="username", operator="like", value="%test%")
        condition = query_filter._build_simple_filter_condition(filter_param)
        assert condition is not None

    @pytest.mark.asyncio
    async def test_build_logical_condition(self, query_filter: QueryFilter):
        """Test building logical filter conditions (AND/OR/NOT)."""
        # Test AND condition
        nested_filters = [
            FilterParam(field="username", operator="eq", value="test"),
            FilterParam(field="age", operator="gt", value=25),
        ]
        filter_param = FilterParam(field=None, operator="and", value=nested_filters)
        condition = query_filter._build_logical_condition(filter_param)
        assert condition is not None

        # Test OR condition
        filter_param = FilterParam(field=None, operator="or", value=nested_filters)
        condition = query_filter._build_logical_condition(filter_param)
        assert condition is not None

        # Test NOT condition
        not_filter = FilterParam(
            field=None, operator="not", value=[FilterParam(field="age", operator="eq", value=25)]
        )
        condition = query_filter._build_logical_condition(not_filter)
        assert condition is not None

    @pytest.mark.asyncio
    async def test_build_nested_filter_condition(self, query_filter: QueryFilter):
        """Test building nested relationship filter conditions."""
        filter_param = FilterParam(field=None, operator="eq", value="test")
        with pytest.raises(FilterError, match="Field cannot be None for nested filtering"):
            query_filter._build_nested_filter_condition(filter_param)

    @pytest.mark.asyncio
    async def test_apply_operator_to_column(self, query_filter):
        """Test applying operators to columns."""
        # Test equality
        username_col = User.username
        condition = query_filter._apply_operator_to_column(username_col, "eq", "test")
        assert condition is not None

        # Test greater than
        age_col = User.age
        condition = query_filter._apply_operator_to_column(age_col, "gt", 25)
        assert condition is not None

        # Test like
        condition = query_filter._apply_operator_to_column(username_col, "like", "%test%")
        assert condition is not None

        # Test in
        condition = query_filter._apply_operator_to_column(username_col, "in", ["test1", "test2"])
        assert condition is not None

        # Test between
        condition = query_filter._apply_operator_to_column(age_col, "between", [20, 30])
        assert condition is not None

        # Test is_null
        condition = query_filter._apply_operator_to_column(username_col, "is_null", True)
        assert condition is not None

    @pytest.mark.asyncio
    async def test_apply_filters_success(self, query_filter, db_session):
        """Test successful filter application."""
        # Create test users with explicit ages
        users_data = [
            create_test_user(age=25),
            create_test_user(age=30),
            create_test_user(age=35),
        ]
        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Test single filter
        query = select(User)
        filters = [FilterParam(field="age", operator="ge", value=30)]
        filtered_query = query_filter.apply_filters(query, filters)
        result = await db_session.execute(filtered_query)
        users = result.scalars().all()
        assert len(users) == 2
        assert all(user.age >= 30 for user in users)

    @pytest.mark.asyncio
    async def test_apply_filters_multiple(self, query_filter, db_session):
        """Test multiple filter application."""
        users_data = [
            create_test_user(age=25, is_active=True),
            create_test_user(age=30, is_active=True),
            create_test_user(age=35, is_active=True),
        ]
        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()
        query = select(User)
        filters = [
            FilterParam(field="age", operator="ge", value=30),
            FilterParam(field="is_active", operator="eq", value=True),
        ]
        filtered_query = query_filter.apply_filters(query, filters)
        result = await db_session.execute(filtered_query)
        users = result.scalars().all()
        assert len(users) == 2
        assert all(user.age >= 30 and user.is_active is True for user in users)

    @pytest.mark.asyncio
    async def test_apply_filters_nested(self, query_filter, db_session):
        """Test nested filter application."""
        # Create test users with explicit ages
        users_data = [
            create_test_user(age=25),
            create_test_user(age=30),
            create_test_user(age=35),
        ]
        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Test nested filters (OR condition)
        query = select(User)
        filters = [
            FilterParam(
                field=None,
                operator="or",
                value=[
                    FilterParam(field="age", operator="eq", value=25),
                    FilterParam(field="age", operator="eq", value=35),
                ],
            )
        ]
        filtered_query = query_filter.apply_filters(query, filters)
        result = await db_session.execute(filtered_query)
        users = result.scalars().all()
        ages = [user.age for user in users]
        assert len(users) == 2
        assert 25 in ages and 35 in ages

    @pytest.mark.asyncio
    async def test_apply_filters_string_operators(self, query_filter, db_session):
        """Test string filter operators."""
        # Create test users with explicit usernames and full_names
        users_data = [
            create_test_user(username=unique_name("john_doe"), full_name="John Doe"),
            create_test_user(username=unique_name("jane_smith"), full_name="Jane Smith"),
            create_test_user(username=unique_name("bob_wilson"), full_name="Bob Wilson"),
        ]
        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Test like operator
        query = select(User)
        filters = [FilterParam(field="username", operator="like", value="%john%")]
        filtered_query = query_filter.apply_filters(query, filters)
        result = await db_session.execute(filtered_query)
        users = result.scalars().all()
        assert len(users) == 1
        assert "john" in users[0].username.lower()

        # Test contains operator
        filters = [FilterParam(field="full_name", operator="contains", value="John")]
        filtered_query = query_filter.apply_filters(query, filters)
        result = await db_session.execute(filtered_query)
        users = result.scalars().all()
        assert len(users) == 1
        assert "John" in users[0].full_name

    @pytest.mark.asyncio
    async def test_apply_filters_numeric_operators(self, query_filter, db_session):
        """Test numeric filter operators."""
        # Create test users with explicit ages
        users_data = [
            create_test_user(age=25),
            create_test_user(age=30),
            create_test_user(age=35),
        ]
        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Test between operator
        query = select(User)
        filters = [FilterParam(field="age", operator="between", value=[25, 30])]
        filtered_query = query_filter.apply_filters(query, filters)
        result = await db_session.execute(filtered_query)
        users = result.scalars().all()
        ages = [user.age for user in users]
        assert len(users) == 2
        assert all(25 <= age <= 30 for age in ages)

        # Test in operator
        filters = [FilterParam(field="age", operator="in", value=[25, 35])]
        filtered_query = query_filter.apply_filters(query, filters)
        result = await db_session.execute(filtered_query)
        users = result.scalars().all()
        ages = [user.age for user in users]
        assert len(users) == 2
        assert all(age in [25, 35] for age in ages)

    @pytest.mark.asyncio
    async def test_apply_filters_boolean_operators(self, query_filter, db_session):
        """Test boolean filter operators."""
        # Create test users with explicit is_active values
        users_data = [
            create_test_user(is_active=True),
            create_test_user(is_active=False),
            create_test_user(is_active=True),
        ]
        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Test is_null operator
        query = select(User)
        filters = [FilterParam(field="last_login", operator="is_null", value=True)]
        filtered_query = query_filter.apply_filters(query, filters)
        result = await db_session.execute(filtered_query)
        users = result.scalars().all()
        assert all(user.last_login is None for user in users)

        # Test is_not_null operator
        # Set last_login for one user
        user = users[0]
        user.last_login = datetime.now()
        await db_session.commit()

        filters = [FilterParam(field="last_login", operator="is_not_null", value=True)]
        filtered_query = query_filter.apply_filters(query, filters)
        result = await db_session.execute(filtered_query)
        users = result.scalars().all()
        assert all(user.last_login is not None for user in users)

    @pytest.mark.asyncio
    async def test_apply_search_success(self, query_filter, db_session):
        """Test successful search application."""
        # Create test users with explicit usernames
        john_username = unique_name("john_doe")
        users_data = [
            create_test_user(username=john_username),
            create_test_user(username=unique_name("jane_smith")),
            create_test_user(username=unique_name("bob_wilson")),
        ]
        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Test search in username
        query = select(User)
        search_fields = ["username"]
        search_query = query_filter.apply_search(query, john_username, search_fields)
        result = await db_session.execute(search_query)
        users = result.scalars().all()
        assert len(users) == 1
        assert users[0].username == john_username

    @pytest.mark.asyncio
    async def test_apply_search_multiple_fields(self, query_filter, db_session):
        """Test search in multiple fields."""
        # Create test users with explicit usernames and full_names
        john_username = unique_name("john_doe")
        users_data = [
            create_test_user(username=john_username, full_name="John Doe"),
            create_test_user(username=unique_name("jane_smith"), full_name="Jane Smith"),
            create_test_user(username=unique_name("bob_wilson"), full_name="Bob Wilson"),
        ]
        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Test search in username and full_name
        query = select(User)
        search_fields = ["username", "full_name"]
        search_query = query_filter.apply_search(query, "John", search_fields)
        result = await db_session.execute(search_query)
        users = result.scalars().all()
        # Should find at least one user with full_name 'John Doe'
        assert any(user.full_name == "John Doe" for user in users)

    @pytest.mark.asyncio
    async def test_apply_sorting_success(self, query_filter, db_session):
        """Test successful sorting application."""
        # Create test users with explicit ages
        users_data = [
            create_test_user(age=35),
            create_test_user(age=25),
            create_test_user(age=30),
        ]
        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()

        # Test ascending sort
        query = select(User)
        sorting = "age"
        sorted_query = query_filter.apply_sorting(query, sorting)
        result = await db_session.execute(sorted_query)
        users = result.scalars().all()
        ages = [user.age for user in users]
        assert ages == sorted(ages)

        # Test descending sort
        sorting = "-age"
        sorted_query = query_filter.apply_sorting(query, sorting)
        result = await db_session.execute(sorted_query)
        users = result.scalars().all()
        ages = [user.age for user in users]
        assert ages == sorted(ages, reverse=True)

    @pytest.mark.asyncio
    async def test_get_search_fields(self, query_filter):
        """Test getting search fields."""
        search_fields = query_filter._get_search_fields()

        # Should include string fields
        assert "username" in search_fields
        assert "email" in search_fields
        assert "full_name" in search_fields
        assert "bio" in search_fields

        # Should not include non-string fields
        assert "age" not in search_fields
        assert "is_active" not in search_fields
        assert "created_at" not in search_fields

    @pytest.mark.asyncio
    async def test_get_model_columns(self, query_filter):
        """Test getting model columns."""
        columns = query_filter.get_model_columns(User)

        assert "id" in columns
        assert "username" in columns
        assert "email" in columns
        assert "age" in columns
        assert "is_active" in columns
        assert "created_at" in columns

    @pytest.mark.asyncio
    async def test_cast_value_to_column_type(self, query_filter: QueryFilter):
        """Test casting values to column types."""
        # Test string casting
        username_col = User.username
        assert query_filter._safe_cast_value(username_col, "test") == "test"
        assert query_filter._safe_cast_value(username_col, 123) == "123"

        # Test integer casting
        age_col = User.age
        assert query_filter._safe_cast_value(age_col, "25") == 25
        assert query_filter._safe_cast_value(age_col, 25) == 25

        # Test boolean casting
        is_active_col = User.is_active
        assert query_filter._safe_cast_value(is_active_col, "true") is True
        assert query_filter._safe_cast_value(is_active_col, True) is True

        # Test datetime casting
        created_at_col = User.created_at
        dt = datetime.now()
        assert query_filter._safe_cast_value(created_at_col, dt) == dt

        # Test UUID casting
        id_col = User.id
        test_uuid = uuid.uuid4()
        assert query_filter._safe_cast_value(id_col, str(test_uuid)) == test_uuid


class TestQueryFilterEdgeCases:
    """Test suite for QueryFilter edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_filter_with_invalid_field(self, query_filter, db_session):
        """Test filter with invalid field."""
        query = select(User)
        filters = [FilterParam(field="non_existent", operator="eq", value="test")]

        with pytest.raises(FilterError, match="Field 'non_existent' not found"):
            query_filter.apply_filters(query, filters)

    @pytest.mark.asyncio
    async def test_filter_with_invalid_operator(self, query_filter, db_session):
        """Test filter with invalid operator."""
        from pydantic import ValidationError

        query = select(User)
        with pytest.raises(ValidationError):
            filters = [FilterParam(field="username", operator="invalid_op", value="test")]  # type: ignore
            query_filter.apply_filters(query, filters)

    @pytest.mark.asyncio
    async def test_filter_with_invalid_value_type(self, query_filter, db_session):
        """Test filter with invalid value type."""
        query = select(User)
        filters = [FilterParam(field="age", operator="eq", value="not_a_number")]

        with pytest.raises(FilterError):  # Should raise type conversion error
            query_filter.apply_filters(query, filters)

    @pytest.mark.asyncio
    async def test_search_with_empty_fields(self, query_filter, db_session):
        """Test search with empty search fields."""
        query = select(User)
        search_query = query_filter.apply_search(query, "test", [])

        # Should return original query when no search fields
        result = await db_session.execute(search_query)
        users = result.scalars().all()
        assert len(users) == 0  # No users in database

    @pytest.mark.asyncio
    async def test_search_with_invalid_fields(self, query_filter, db_session):
        """Test search with invalid search fields."""
        query = select(User)
        search_query = query_filter.apply_search(query, "test", ["non_existent"])
        result = await db_session.execute(search_query)
        users = result.scalars().all()
        assert users == []

    @pytest.mark.asyncio
    async def test_sorting_with_invalid_field(self, query_filter, db_session):
        """Test sorting with invalid field."""
        query = select(User)
        sorting = "non_existent"
        with pytest.raises(FilterError, match="Field 'non_existent' not found"):
            query_filter.apply_sorting(query, sorting)

    @pytest.mark.asyncio
    async def test_filter_with_empty_filters(self, query_filter, db_session):
        """Test filter application with empty filters list."""
        query = select(User)
        filtered_query = query_filter.apply_filters(query, [])

        # Should return original query
        result = await db_session.execute(filtered_query)
        users = result.scalars().all()
        assert len(users) == 0  # No users in database

    @pytest.mark.asyncio
    async def test_filter_with_none_value(self, query_filter, db_session):
        """Test filter with None value."""
        query = select(User)
        filters = [FilterParam(field="username", operator="eq", value=None)]

        # Should handle None values gracefully
        filtered_query = query_filter.apply_filters(query, filters)
        assert filtered_query is not None

    @pytest.mark.asyncio
    async def test_filter_with_complex_nested_conditions(self, query_filter, db_session):
        """Test complex nested filter conditions."""
        users_data = [
            create_test_user(age=25, is_active=True),
            create_test_user(age=30, is_active=True),
            create_test_user(age=35, is_active=True),
        ]
        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()
        query = select(User)
        filters = [
            FilterParam(
                field=None,
                operator="or",
                value=[
                    FilterParam(
                        field=None,
                        operator="and",
                        value=[
                            FilterParam(field="age", operator="ge", value=30),
                            FilterParam(field="is_active", operator="eq", value=True),
                        ],
                    ),
                    FilterParam(field="age", operator="lt", value=30),
                ],
            )
        ]
        filtered_query = query_filter.apply_filters(query, filters)
        result = await db_session.execute(filtered_query)
        users = result.scalars().all()
        print("test_filter_with_complex_nested_conditions users:", users)
        assert len(users) == 3

    @pytest.mark.asyncio
    async def test_filter_with_different_data_types(self, query_filter, db_session):
        """Test filters with different data types."""
        users_data = [
            create_test_user(age=None),
            create_test_user(age=30),
            create_test_user(age=35),
        ]
        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()
        query = select(User)
        filters = [FilterParam(field="age", operator="is_null", value=True)]
        filtered_query = query_filter.apply_filters(query, filters)
        result = await db_session.execute(filtered_query)
        users = result.scalars().all()

        assert len(users) == 1
        assert users[0].age is None

    @pytest.mark.asyncio
    async def test_filter_performance_with_large_dataset(self, query_filter, db_session):
        """Test filter performance with larger dataset."""
        import uuid

        # Ensure at least 10 users match the filter
        users_data = [
            create_test_user(email=f"test_{uuid.uuid4()}@example.com", age=35, is_active=True)
            for _ in range(10)
        ] + [create_test_user(email=f"test_{uuid.uuid4()}@example.com") for _ in range(90)]
        for user_data in users_data:
            user = User(**user_data.model_dump())
            db_session.add(user)
        await db_session.commit()
        query = select(User)
        filters = [
            FilterParam(field="age", operator="ge", value=30),
            FilterParam(field="is_active", operator="eq", value=True),
        ]
        import time

        start_time = time.time()
        filtered_query = query_filter.apply_filters(query, filters)
        result = await db_session.execute(filtered_query)
        users = result.scalars().all()
        end_time = time.time()
        assert end_time - start_time < 1.0  # Less than 1 second
        assert len(users) >= 10  # Should return at least the 10 matching users


class TestQueryFilterCustomization:
    """Test suite for QueryFilter customization options."""

    @pytest.mark.asyncio
    async def test_custom_allowed_operators(self):
        """Test custom allowed operators configuration."""
        # Create custom allowed operators
        custom_operators = {
            "string": {"eq", "ne", "like"},  # Reduced set
            "numeric": {"eq", "ne", "gt", "lt"},  # Reduced set
            "boolean": {"eq", "ne"},  # Reduced set
            "default": {"eq"},  # Add default key to avoid KeyError
        }

        query_filter = QueryFilter(User, allowed_operators=custom_operators)

        # Test that custom operators work
        assert query_filter._validate_operator_for_field("username", "like") is True
        assert query_filter._validate_operator_for_field("age", "gt") is True

        # Test that non-allowed operators are rejected
        with pytest.raises(FilterError):
            query_filter._validate_operator_for_field("username", "contains")

        with pytest.raises(FilterError):
            query_filter._validate_operator_for_field("age", "between")

    @pytest.mark.asyncio
    async def test_filter_with_custom_model(self):
        """Test QueryFilter with a custom model."""

        from sqlalchemy import Integer, String
        from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

        class CustomBase(DeclarativeBase):
            pass

        class CustomModel(CustomBase):
            __tablename__ = "custom_model"

            id: Mapped[int] = mapped_column(Integer, primary_key=True)
            name: Mapped[str] = mapped_column(String(50))
            value: Mapped[int] = mapped_column(Integer)

        # Test QueryFilter with custom model
        query_filter = QueryFilter(CustomModel)

        assert query_filter.model == CustomModel
        assert query_filter._validate_operator_for_field("name", "eq") is True
        assert query_filter._validate_operator_for_field("value", "gt") is True
