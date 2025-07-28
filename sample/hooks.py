import datetime
import hashlib
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auto_crud.core.crud.base import CRUDHooks
from auto_crud.core.errors import ValidationError
from sample.models import Analytics, Category, Comment, Like, Post, Tag, User
from sample.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CommentCreate,
    CommentUpdate,
    PostCreate,
    PostStatus,
    PostUpdate,
    TagCreate,
    TagUpdate,
    UserCreate,
    UserUpdate,
)


class UserHooks(CRUDHooks[User, uuid.UUID, UserCreate, UserUpdate]):
    """Comprehensive hooks for User operations"""

    async def pre_create(
        self, db_session: AsyncSession, obj_in: UserCreate, *args, **kwargs
    ) -> UserCreate:
        """Pre-create hook for users"""
        # Hash password
        obj_in.password = hashlib.sha256(obj_in.password.encode()).hexdigest()

        # Set default username if not provided
        if not obj_in.username:
            obj_in.username = obj_in.email.split("@")[0]

        # Validate email domain (example business rule)
        if obj_in.email.endswith("@example.com"):
            raise ValidationError("Cannot use example.com domain for real users")

        print(f"Creating user: {obj_in.username} ({obj_in.email})")
        return obj_in

    async def post_create(self, db_session: AsyncSession, obj: User, *args, **kwargs) -> User:
        """Post-create hook for users"""

        analytics = Analytics(
            event_type="user_created",
            entity_type="user",
            entity_id=obj.id,
            user_id=obj.id,
        )
        db_session.add(analytics)
        await db_session.commit()

        return obj

    async def pre_update(
        self,
        db_session: AsyncSession,
        obj: User,
        obj_in: UserUpdate | Dict[str, Any],
        user: Optional[User] = None,
    ) -> User:
        if isinstance(obj_in, dict):
            obj_in = UserUpdate.model_validate(obj_in)

        if obj_in.role and obj_in.role.value in ["admin", "moderator"]:
            if not user or user.role.value not in ["admin"]:
                raise ValueError("Insufficient permissions to assign admin/moderator role")

        return obj

    async def post_update(self, db_session: AsyncSession, obj: User, *args, **kwargs) -> User:
        """Post-update hook for users"""
        print(f"User updated successfully: {obj.username}")

        # Create analytics entry
        analytics = Analytics(
            event_type="user_updated",
            entity_type="user",
            entity_id=obj.id,
            user_id=obj.id,
        )
        db_session.add(analytics)
        await db_session.commit()

        return obj

    async def pre_delete(self, db_session: AsyncSession, obj: User, *args, **kwargs) -> bool:
        """Pre-delete hook for users"""
        # Prevent deletion of admin users
        if obj.role.value == "admin":
            return False

        # Check if user has published posts
        published_posts = await db_session.execute(
            select(Post).where(and_(Post.author_id == obj.id, Post.status == PostStatus.PUBLISHED))
        )
        if published_posts.scalar():
            print(f"Cannot delete user with published posts: {obj.username}")
            return False

        print(f"Deleting user: {obj.username}")
        return True

    async def post_delete(self, db_session: AsyncSession, obj: User, *args, **kwargs) -> User:
        """Post-delete hook for users"""
        print(f"User deleted successfully: {obj.username}")

        # Create analytics entry
        analytics = Analytics(event_type="user_deleted", entity_type="user", entity_id=obj.id)
        db_session.add(analytics)
        await db_session.commit()

        return obj

    async def pre_read(self, db_session: AsyncSession, obj_id: uuid.UUID, *args, **kwargs) -> Any:
        """Pre-read hook for users"""
        print(f"Reading user: {obj_id}")
        return obj_id

    async def post_read(
        self, db_session: AsyncSession, obj: Optional[User], *args, **kwargs
    ) -> Optional[User]:
        """Post-read hook for users"""
        if obj:
            print(f"User read: {obj.username}")

            # Update last login if this is a login event
            if kwargs.get("is_login", False):
                obj.last_login = datetime.datetime.utcnow()
                await db_session.commit()

        return obj


class PostHooks(CRUDHooks[Post, uuid.UUID, PostCreate, PostUpdate]):
    """Comprehensive hooks for Post operations"""

    async def pre_create(
        self, db_session: AsyncSession, obj_in: PostCreate, *args, **kwargs
    ) -> PostCreate:
        """Pre-create hook for posts"""
        # Generate slug if not provided
        if not obj_in.slug:
            obj_in.slug = self._generate_slug(obj_in.title)

        # Calculate reading time if not provided
        if not obj_in.reading_time:
            word_count = len(obj_in.content.split())
            obj_in.reading_time = max(1, word_count // 200)

        # Validate content length
        if len(obj_in.content.strip()) < 100:
            raise ValueError("Post content must be at least 100 characters long")

        # Set SEO fields if not provided
        if not obj_in.seo_title:
            obj_in.seo_title = obj_in.title[:60]
        if not obj_in.seo_description:
            obj_in.seo_description = (
                obj_in.excerpt[:160] if obj_in.excerpt else obj_in.content[:160]
            )

        print(f"Creating post: {obj_in.title}")
        return obj_in

    async def post_create(self, db_session: AsyncSession, obj: Post, *args, **kwargs) -> Post:
        """Post-create hook for posts"""
        print(f"Post created successfully: {obj.title} (ID: {obj.id})")

        # Update tag usage counts
        if hasattr(obj, "tags") and obj.tags:
            for tag in obj.tags:
                tag.usage_count += 1
            await db_session.commit()

        # Create analytics entry
        analytics = Analytics(
            event_type="post_created",
            entity_type="post",
            entity_id=obj.id,
            user_id=obj.author_id,
        )
        db_session.add(analytics)
        await db_session.commit()

        return obj

    async def pre_update(
        self,
        db_session: AsyncSession,
        obj: Post,
        obj_in: PostUpdate,
        user: Optional[Any] = None,
    ) -> Post:
        """Pre-update hook for posts"""
        print(f"Updating post: {obj.title}")

        # Generate slug if title changed and slug not provided
        if obj_in.title and not obj_in.slug:
            obj_in.slug = self._generate_slug(obj_in.title)

        # Calculate reading time if content changed
        if obj_in.content and not obj_in.reading_time:
            word_count = len(obj_in.content.split())
            obj_in.reading_time = max(1, word_count // 200)

        # Prevent editing published posts by non-authors
        if obj.status.value == "published" and user and user.id != obj.author_id:
            if user.role.value not in ["admin", "moderator"]:
                raise ValueError("Only authors, admins, and moderators can edit published posts")

        return obj

    async def post_update(self, db_session: AsyncSession, obj: Post, *args, **kwargs) -> Post:
        """Post-update hook for posts"""
        print(f"Post updated successfully: {obj.title}")

        # Update comment count
        comment_count = await db_session.execute(
            select(func.count(Comment.id)).where(Comment.post_id == obj.id)
        )
        obj.comment_count = comment_count.scalar() or 0

        # Update like count
        like_count = await db_session.execute(
            select(func.count(Like.id)).where(Like.post_id == obj.id)
        )
        obj.like_count = like_count.scalar() or 0

        await db_session.commit()

        # Create analytics entry
        analytics = Analytics(
            event_type="post_updated",
            entity_type="post",
            entity_id=obj.id,
            user_id=obj.author_id,
        )
        db_session.add(analytics)
        await db_session.commit()

        return obj

    async def pre_delete(self, db_session: AsyncSession, obj: Post, *args, **kwargs) -> bool:
        """Pre-delete hook for posts"""
        # Prevent deletion of published posts
        if obj.status.value == "published":
            print(f"Attempted to delete published post: {obj.title}")
            return False

        print(f"Deleting post: {obj.title}")
        return True

    async def post_delete(self, db_session: AsyncSession, obj: Post, *args, **kwargs) -> Post:
        """Post-delete hook for posts"""
        print(f"Post deleted successfully: {obj.title}")

        # Update tag usage counts
        if hasattr(obj, "tags") and obj.tags:
            for tag in obj.tags:
                tag.usage_count = max(0, tag.usage_count - 1)
            await db_session.commit()

        # Create analytics entry
        analytics = Analytics(
            event_type="post_deleted",
            entity_type="post",
            entity_id=obj.id,
            user_id=obj.author_id,
        )
        db_session.add(analytics)
        await db_session.commit()

        return obj

    async def pre_read(self, db_session: AsyncSession, obj_id: uuid.UUID, *args, **kwargs) -> Any:
        """Pre-read hook for posts"""
        print(f"Reading post: {obj_id}")
        return obj_id

    async def post_read(
        self, db_session: AsyncSession, obj: Optional[Post], *args, **kwargs
    ) -> Optional[Post]:
        """Post-read hook for posts"""
        if obj:
            # Increment view count
            obj.view_count += 1
            await db_session.commit()

            print(f"Post read: {obj.title} (views: {obj.view_count})")

            # Create analytics entry
            analytics = Analytics(event_type="post_view", entity_type="post", entity_id=obj.id)
            db_session.add(analytics)
            await db_session.commit()

        return obj

    def _generate_slug(self, title: str) -> str:
        """Generate a URL-friendly slug from title"""
        import re

        # Convert to lowercase and replace spaces with hyphens
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug.strip("-")[:200]  # Limit to 200 characters


class CategoryHooks(CRUDHooks[Category, uuid.UUID, CategoryCreate, CategoryUpdate]):
    """Hooks for Category operations"""

    async def pre_create(
        self, db_session: AsyncSession, obj_in: CategoryCreate, *args, **kwargs
    ) -> CategoryCreate:
        """Pre-create hook for categories"""
        # Generate slug if not provided
        if not obj_in.slug:
            obj_in.slug = self._generate_slug(obj_in.name)

        # Validate color format
        if obj_in.color and not obj_in.color.startswith("#"):
            obj_in.color = f"#{obj_in.color}"

        print(f"Creating category: {obj_in.name}")
        return obj_in

    async def post_create(
        self, db_session: AsyncSession, obj: Category, *args, **kwargs
    ) -> Category:
        """Post-create hook for categories"""
        print(f"Category created successfully: {obj.name}")

        # Create analytics entry
        analytics = Analytics(
            event_type="category_created", entity_type="category", entity_id=obj.id
        )
        db_session.add(analytics)
        await db_session.commit()

        return obj

    def _generate_slug(self, name: str) -> str:
        """Generate a URL-friendly slug from name"""
        import re

        slug = re.sub(r"[^\w\s-]", "", name.lower())
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug.strip("-")[:100]


class TagHooks(CRUDHooks[Tag, uuid.UUID, TagCreate, TagUpdate]):
    """Hooks for Tag operations"""

    async def pre_create(
        self, db_session: AsyncSession, obj_in: TagCreate, *args, **kwargs
    ) -> TagCreate:
        """Pre-create hook for tags"""
        # Generate slug if not provided
        if not obj_in.slug:
            obj_in.slug = self._generate_slug(obj_in.name)

        # Validate color format
        if obj_in.color and not obj_in.color.startswith("#"):
            obj_in.color = f"#{obj_in.color}"

        print(f"Creating tag: {obj_in.name}")
        return obj_in

    async def post_create(self, db_session: AsyncSession, obj: Tag, *args, **kwargs) -> Tag:
        """Post-create hook for tags"""
        print(f"Tag created successfully: {obj.name}")

        # Create analytics entry
        analytics = Analytics(event_type="tag_created", entity_type="tag", entity_id=obj.id)
        db_session.add(analytics)
        await db_session.commit()

        return obj

    def _generate_slug(self, name: str) -> str:
        """Generate a URL-friendly slug from name"""
        import re

        slug = re.sub(r"[^\w\s-]", "", name.lower())
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug.strip("-")[:50]


class CommentHooks(CRUDHooks[Comment, uuid.UUID, CommentCreate, CommentUpdate]):
    """Hooks for Comment operations"""

    async def pre_create(
        self, db_session: AsyncSession, obj_in: CommentCreate, *args, **kwargs
    ) -> CommentCreate:
        """Pre-create hook for comments"""
        # Basic spam detection (note: these fields are set in the model, not schema)
        spam_words = ["spam", "buy now", "click here", "free money"]
        content_lower = obj_in.content.lower()
        if any(word in content_lower for word in spam_words):
            # Mark as spam in the database during creation
            print(f"Spam detected in comment: {obj_in.content[:50]}...")

        print(f"Creating comment for post: {obj_in.post_id}")
        return obj_in

    async def post_create(self, db_session: AsyncSession, obj: Comment, *args, **kwargs) -> Comment:
        """Post-create hook for comments"""
        print(f"Comment created successfully: {obj.id}")

        # Update post comment count
        post = await db_session.get(Post, obj.post_id)
        if post:
            post.comment_count += 1
            await db_session.commit()

        # Create analytics entry
        analytics = Analytics(
            event_type="comment_created",
            entity_type="comment",
            entity_id=obj.id,
            user_id=obj.author_id,
        )
        db_session.add(analytics)
        await db_session.commit()

        return obj

    async def pre_update(
        self,
        db_session: AsyncSession,
        obj: Comment,
        obj_in: CommentUpdate,
        user: Optional[Any] = None,
    ) -> Comment:
        """Pre-update hook for comments"""
        print(f"Updating comment: {obj.id}")

        # Only allow authors or moderators to edit comments
        if user and user.id != obj.author_id:
            if user.role.value not in ["admin", "moderator"]:
                raise ValueError("Only authors, admins, and moderators can edit comments")

        return obj

    async def post_update(self, db_session: AsyncSession, obj: Comment, *args, **kwargs) -> Comment:
        """Post-update hook for comments"""
        print(f"Comment updated successfully: {obj.id}")

        # Create analytics entry
        analytics = Analytics(
            event_type="comment_updated",
            entity_type="comment",
            entity_id=obj.id,
            user_id=obj.author_id,
        )
        db_session.add(analytics)
        await db_session.commit()

        return obj

    async def pre_delete(self, db_session: AsyncSession, obj: Comment, *args, **kwargs) -> bool:
        """Pre-delete hook for comments"""
        print(f"Deleting comment: {obj.id}")
        return True

    async def post_delete(self, db_session: AsyncSession, obj: Comment, *args, **kwargs) -> Comment:
        """Post-delete hook for comments"""
        print(f"Comment deleted successfully: {obj.id}")

        # Update post comment count
        post = await db_session.get(Post, obj.post_id)
        if post:
            post.comment_count = max(0, post.comment_count - 1)
            await db_session.commit()

        # Create analytics entry
        analytics = Analytics(
            event_type="comment_deleted",
            entity_type="comment",
            entity_id=obj.id,
            user_id=obj.author_id,
        )
        db_session.add(analytics)
        await db_session.commit()

        return obj
