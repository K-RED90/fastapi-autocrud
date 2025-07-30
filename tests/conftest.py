import asyncio
import uuid
from datetime import datetime
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from pydantic import BaseModel, EmailStr
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.pool import StaticPool

from auto_crud.core.crud.base import BaseCRUD, CRUDHooks
from auto_crud.core.crud.filter import QueryFilter
from auto_crud.core.crud.router import RouterFactory


# Test Models
class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(100))
    full_name: Mapped[Optional[str]] = mapped_column(String(100))
    bio: Mapped[Optional[str]] = mapped_column(Text)
    age: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=datetime.utcnow, default=datetime.utcnow
    )

    # Relationships
    posts: Mapped[List["Post"]] = relationship(
        "Post", back_populates="author", cascade="all, delete-orphan"
    )


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), index=True)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=datetime.utcnow, default=datetime.utcnow
    )

    # Relationships
    author: Mapped["User"] = relationship("User", back_populates="posts")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# Test Schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    age: Optional[int] = None


class UserUpdate(BaseModel):
    id: Optional[uuid.UUID] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    age: Optional[int] = None
    is_active: Optional[bool] = None


class PostCreate(BaseModel):
    title: str
    content: str
    status: str = "draft"
    author_id: uuid.UUID


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None


class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None


# Test Hooks
class TestHooks(CRUDHooks[User, uuid.UUID, UserCreate, UserUpdate]):
    async def pre_create(
        self, db_session: AsyncSession, obj_in: UserCreate, *args, **kwargs
    ) -> UserCreate:
        # Add a prefix to username for testing
        obj_in.username = f"test_{obj_in.username}"
        return obj_in

    async def post_create(self, db_session: AsyncSession, obj: User, *args, **kwargs) -> User:
        # Set is_verified to True for testing
        obj.is_verified = True
        return obj

    async def pre_delete(self, db_session: AsyncSession, obj: User, *args, **kwargs) -> bool:
        # Prevent deletion of active users
        return not obj.is_active


# Database setup
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def database_url():
    """Return the database URL for testing."""
    return "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def async_engine(database_url):
    """Create an async engine for testing."""
    engine = create_async_engine(
        database_url,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def async_session_maker(async_engine):
    """Create an async session maker for testing."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    return session_maker


@pytest_asyncio.fixture
async def db_session(async_session_maker):
    """Create a database session for testing."""
    async with async_session_maker() as session:
        yield session
        # Rollback will happen automatically when the context exits


# CRUD fixtures
@pytest.fixture
def user_crud():
    """Create a User CRUD instance."""
    return BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User)


@pytest.fixture
def post_crud():
    """Create a Post CRUD instance."""
    return BaseCRUD[Post, uuid.UUID, PostCreate, PostUpdate](model=Post)


@pytest.fixture
def category_crud():
    """Create a Category CRUD instance."""
    return BaseCRUD[Category, int, CategoryCreate, CategoryUpdate](model=Category)


@pytest.fixture
def user_crud_with_hooks():
    """Create a User CRUD instance with hooks."""
    return BaseCRUD[User, uuid.UUID, UserCreate, UserUpdate](model=User, hooks=TestHooks())


@pytest.fixture
def query_filter():
    """Create a QueryFilter instance for User model."""
    return QueryFilter(User)


# Router fixtures
@pytest.fixture
def session_factory(async_session_maker):
    """Create a session factory for router testing."""

    async def get_session():
        async with async_session_maker() as session:
            yield session

    return get_session


@pytest.fixture
def user_router(session_factory, user_crud):
    """Create a User RouterFactory instance."""
    return RouterFactory(
        crud=user_crud,
        session_factory=session_factory,
        create_schema=UserCreate,
        update_schema=UserUpdate,
        prefix="/users",
        tags=["users"],
    )


@pytest.fixture
def post_router(session_factory, post_crud):
    """Create a Post RouterFactory instance."""
    return RouterFactory(
        crud=post_crud,
        session_factory=session_factory,
        create_schema=PostCreate,
        update_schema=PostUpdate,
        prefix="/posts",
        tags=["posts"],
    )


@pytest.fixture
def category_router(session_factory, category_crud):
    """Create a Category RouterFactory instance."""
    return RouterFactory(
        crud=category_crud,
        session_factory=session_factory,
        create_schema=CategoryCreate,
        update_schema=CategoryUpdate,
        prefix="/categories",
        tags=["categories"],
    )


# Test data fixtures
@pytest.fixture
def sample_users():
    """Create sample user data for testing."""
    import random

    def unique_user(base):
        suffix = random.randint(100000, 999999)
        return {
            "username": f"{base}_{suffix}",
            "email": f"{base}_{suffix}@example.com",
            "password": "password123",
            "full_name": base.replace("_", " ").title(),
            "bio": "Test bio",
            "age": 25 + (suffix % 10),
        }

    return [
        unique_user("john_doe"),
        unique_user("jane_smith"),
        unique_user("bob_wilson"),
    ]


@pytest.fixture
def sample_posts():
    """Create sample post data for testing."""
    import random
    import time

    timestamp = int(time.time() * 1000)

    def unique_post(base):
        suffix = random.randint(1000, 9999)
        return {
            "title": f"{base} {timestamp} {suffix}",
            "content": f"This is the {base.lower()} content",
            "status": "published" if suffix % 2 == 0 else "draft",
        }

    return [
        unique_post("First Post"),
        unique_post("Second Post"),
        unique_post("Third Post"),
    ]


@pytest.fixture
def sample_categories():
    """Create sample category data for testing."""
    import random
    import time

    timestamp = int(time.time() * 1000)

    def unique_cat(base):
        suffix = random.randint(1000, 9999)
        return {
            "name": f"{base} {timestamp} {suffix}",
            "slug": f"{base.lower().replace(' ', '-')}-{timestamp}-{suffix}",
            "description": f"{base} related posts",
        }

    return [
        unique_cat("Technology"),
        unique_cat("Science"),
        unique_cat("Business"),
    ]


# FastAPI app fixture
@pytest.fixture
def app():
    """Create a FastAPI app for testing."""
    return FastAPI(title="Test API", version="1.0.0")


# Mock fixtures
@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_query_result():
    """Create a mock query result."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value.unique.return_value.all.return_value = []
    result.scalar.return_value = 0
    return result


# Utility functions
def create_test_user(**kwargs) -> UserCreate:
    """Create a test user with default values."""
    import random
    import time
    import uuid

    # Use UUID for uniqueness to avoid collisions in fast test loops
    unique_id = uuid.uuid4().hex
    defaults = {
        "username": f"testuser_{unique_id}",
        "email": f"test_{unique_id}@example.com",
        "password": "password123",
        "full_name": "Test User",
        "bio": "Test bio",
        "age": 25,
    }
    defaults.update(kwargs)
    return UserCreate(**defaults)


def create_test_post(author_id: uuid.UUID, **kwargs) -> PostCreate:
    """Create a test post with default values."""
    import time

    timestamp = int(time.time() * 1000)  # Use timestamp for uniqueness
    defaults = {
        "title": f"Test Post {timestamp}",
        "content": "Test content",
        "status": "draft",
        "author_id": author_id,
    }
    defaults.update(kwargs)
    return PostCreate(**defaults)


def create_test_category(**kwargs) -> CategoryCreate:
    """Create a test category with default values."""
    import time

    timestamp = int(time.time() * 1000)  # Use timestamp for uniqueness
    defaults = {
        "name": f"Test Category {timestamp}",
        "slug": f"test-category-{timestamp}",
        "description": "Test description",
    }
    defaults.update(kwargs)
    return CategoryCreate(**defaults)
