import datetime
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, validator


# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    AUTHOR = "author"
    READER = "reader"


class PostStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"


# Base schemas with common configurations
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# User schemas
class UserBase(BaseSchema):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: str = Field(..., max_length=100, pattern=r"^[^@]+@[^@]+\.[^@]+$")
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=255)
    role: UserRole = UserRole.READER
    is_active: bool = True
    is_verified: bool = False


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseSchema):
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: Optional[str] = Field(None, max_length=100, pattern=r"^[^@]+@[^@]+\.[^@]+$")
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserResponse(UserBase):
    id: uuid.UUID
    last_login: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    @computed_field
    @property
    def display_name(self) -> str:
        return self.full_name or self.username

    @computed_field
    @property
    def is_online(self) -> bool:
        if not self.last_login:
            return False
        return (datetime.datetime.utcnow() - self.last_login).total_seconds() < 300  # 5 minutes


class UserDetailResponse(UserResponse):
    posts_count: int = 0
    followers_count: int = 0
    following_count: int = 0
    total_likes_received: int = 0


# Category schemas
class CategoryBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    is_active: bool = True
    parent_id: Optional[uuid.UUID] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    is_active: Optional[bool] = None
    parent_id: Optional[uuid.UUID] = None


class CategoryResponse(CategoryBase):
    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    @computed_field
    @property
    def posts_count(self) -> int:
        # This will be populated by the service layer
        return getattr(self, "_posts_count", 0)


class CategoryDetailResponse(CategoryResponse):
    children: List["CategoryResponse"] = []
    total_posts: int = 0


# Tag schemas
class TagBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=50)
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=200)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagCreate(TagBase):
    pass


class TagUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    slug: Optional[str] = Field(None, min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=200)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagResponse(TagBase):
    id: uuid.UUID
    usage_count: int
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None


# Post schemas
class PostBase(BaseSchema):
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=200, pattern=r"^[a-z0-9-]+$")
    excerpt: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=10)
    featured_image: Optional[str] = Field(None, max_length=255)
    status: PostStatus = PostStatus.DRAFT
    reading_time: Optional[int] = Field(None, ge=1, le=480)  # 1-8 hours
    seo_title: Optional[str] = Field(None, max_length=60)
    seo_description: Optional[str] = Field(None, max_length=160)


class PostCreate(PostBase):
    author_id: uuid.UUID
    category_ids: List[uuid.UUID] = Field(default_factory=list)
    tag_ids: List[uuid.UUID] = Field(default_factory=list)

    @validator("content")
    def validate_content_length(cls, v):
        if len(v.strip()) < 100:
            raise ValueError("Post content must be at least 100 characters long")
        return v

    @validator("reading_time", always=True)
    def calculate_reading_time(cls, v, values):
        if v is None and "content" in values:
            # Estimate reading time: 200 words per minute
            word_count = len(values["content"].split())
            return max(1, word_count // 200)
        return v


class PostUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, min_length=1, max_length=200, pattern=r"^[a-z0-9-]+$")
    excerpt: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = Field(None, min_length=10)
    featured_image: Optional[str] = Field(None, max_length=255)
    status: Optional[PostStatus] = None
    reading_time: Optional[int] = Field(None, ge=1, le=480)
    seo_title: Optional[str] = Field(None, max_length=60)
    seo_description: Optional[str] = Field(None, max_length=160)
    category_ids: Optional[List[uuid.UUID]] = None
    tag_ids: Optional[List[uuid.UUID]] = None


class PostResponse(PostBase):
    id: uuid.UUID
    author_id: uuid.UUID
    view_count: int
    like_count: int
    comment_count: int
    published_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    @computed_field
    @property
    def is_published(self) -> bool:
        return self.status == PostStatus.PUBLISHED

    @computed_field
    @property
    def engagement_rate(self) -> float:
        if self.view_count == 0:
            return 0.0
        return round((self.like_count + self.comment_count) / self.view_count * 100, 2)


class PostDetailResponse(PostResponse):
    author: UserResponse | None = None
    categories: List[CategoryResponse] = []
    tags: List[TagResponse] = []


# Comment schemas
class CommentBase(BaseSchema):
    content: str = Field(..., min_length=1, max_length=1000)
    parent_id: Optional[uuid.UUID] = None


class CommentCreate(CommentBase):
    post_id: uuid.UUID
    author_id: uuid.UUID


class CommentUpdate(BaseSchema):
    content: str = Field(..., min_length=1, max_length=1000)


class CommentResponse(CommentBase):
    id: uuid.UUID
    post_id: uuid.UUID
    author_id: uuid.UUID
    is_approved: bool
    is_spam: bool
    like_count: int
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None


class CommentDetailResponse(CommentResponse):
    author: UserResponse
    replies: List["CommentDetailResponse"] = []


# Like schemas
class LikeBase(BaseSchema):
    user_id: uuid.UUID
    post_id: uuid.UUID


class LikeCreate(LikeBase):
    pass


class LikeResponse(LikeBase):
    id: uuid.UUID
    created_at: datetime.datetime


# Analytics schemas
class AnalyticsBase(BaseSchema):
    event_type: str = Field(..., max_length=50)
    entity_type: str = Field(..., max_length=50)
    entity_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    ip_address: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = None
    metadata_json: Optional[str] = None


class AnalyticsCreate(AnalyticsBase):
    pass


class AnalyticsResponse(AnalyticsBase):
    id: uuid.UUID
    created_at: datetime.datetime


# Search and filter schemas
class SearchParams(BaseSchema):
    query: str = Field(..., min_length=1, max_length=100)
    fields: Optional[List[str]] = None
    relations: Optional[List[str]] = None


class BulkOperationResponse(BaseSchema):
    success_count: int
    error_count: int
    errors: List[Dict[str, Any]] = []


# Update forward references
CategoryResponse.model_rebuild()
CategoryDetailResponse.model_rebuild()
CommentDetailResponse.model_rebuild()
