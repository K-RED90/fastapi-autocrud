import datetime
import re
import uuid
from typing import Any, Dict, List, Optional

from fastapi import Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auto_crud.core.crud.base import BaseCRUD
from auto_crud.core.crud.decorators import action
from auto_crud.core.crud.router import RouterFactory
from auto_crud.core.schemas.pagination import (
    FilterParam,
    PaginatedResponse,
)
from auto_crud.dependencies.page_param import PageParams
from sample.db import get_session
from sample.hooks import PostHooks
from sample.models import Category, Comment, Post, PostStatus, Tag
from sample.schemas import (
    BulkOperationResponse,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    CommentResponse,
    PostCreate,
    PostDetailResponse,
    PostResponse,
    PostUpdate,
    TagCreate,
    TagResponse,
    TagUpdate,
)


class PostRouterFactory(RouterFactory[Post, uuid.UUID, PostCreate, PostUpdate]):
    @action(method="GET", detail=False, url_path="popular", response_model=List[PostResponse])
    async def get_popular_posts(
        self,
        session: AsyncSession = Depends(get_session),
        min_views: int = 10,
        min_likes: int = 5,
    ):
        """Get popular posts based on views and likes"""
        filters = [
            FilterParam(field="view_count", operator="ge", value=min_views),
            FilterParam(field="like_count", operator="ge", value=min_likes),
            FilterParam(field="status", operator="eq", value="published"),
        ]
        return await self.crud.list_objects(session, filters=filters)

    @action(
        method="POST", detail=True, url_path="publish", status_code=200, response_model=PostResponse
    )
    async def publish_post(self, session: AsyncSession = Depends(get_session), *, id: uuid.UUID):
        """Publish a draft post"""
        post = await self.crud.get_by_id(session, id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        if post.status == PostStatus.PUBLISHED:
            raise HTTPException(status_code=400, detail="Post is already published")

        update_data = {
            "status": PostStatus.PUBLISHED,
            "published_at": datetime.datetime.now(datetime.UTC),
        }
        return await self.crud.update(session, post, update_data)

    @action(
        method="POST", detail=True, url_path="archive", status_code=200, response_model=PostResponse
    )
    async def archive_post(self, session: AsyncSession = Depends(get_session), *, id: uuid.UUID):
        """Archive a post"""
        post = await self.crud.get_by_id(session, id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        update_data = {"status": PostStatus.ARCHIVED}
        return await self.crud.update(session, post, update_data)

    @action(
        method="GET",
        detail=True,
        url_path="stats",
        response_model=Dict[str, Any],
        response_class=JSONResponse,
    )
    async def get_post_stats(
        self, session: AsyncSession = Depends(get_session), *, id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get comprehensive post statistics"""
        post = await self.crud.get_by_id(session, id, prefetch=["comments", "likes"])
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        stmt = select(
            func.count(Post.likes.any()),
            func.count(Post.comments.any()),
        ).where(Post.id == post.id)

        result = (await session.execute(stmt)).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Post not found")
        total_likes, total_comments = result

        return {
            "total_views": post.view_count,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "average_engagement_rate": (total_likes + total_comments)
            / max(post.view_count, 1)
            * 100,
        }

    @action(method="GET", detail=True, url_path="comments", response_model=List[CommentResponse])
    async def get_post_comments(
        self,
        session: AsyncSession = Depends(get_session),
        *,
        id: uuid.UUID,
    ) -> List[Comment]:
        """Get all comments for a post"""
        post = await self.crud.get_by_id(session, id, prefetch=["comments"])
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        return post.comments

    @action(
        method="GET",
        detail=False,
        url_path="by-category/{category_id}",
        response_model=PaginatedResponse[PostResponse],
    )
    async def get_posts_by_category(
        self,
        session: AsyncSession = Depends(get_session),
        *,
        category_id: uuid.UUID,
        page_params: PageParams = Depends(),
    ):
        filters = [
            *page_params.filters,
            FilterParam(field="categories.id", operator="eq", value=category_id),
        ]

        return await self.crud.list_objects(
            session,
            filters=filters,
            prefetch=["categories"],
            search=page_params.search,
            search_fields=["title", "content", "excerpt"],
            sorting=page_params.sort_by,
            pagination={
                "page": page_params.page,
                "size": page_params.size,
            },
        )

    @action(
        method="GET",
        detail=False,
        url_path="by-tag/{tag_id}",
        response_model=List[PostResponse],
    )
    async def get_posts_by_tag(
        self,
        session: AsyncSession = Depends(get_session),
        *,
        tag_id: uuid.UUID,
        status: Optional[str] = None,
    ) -> List[PostResponse]:
        """Get all posts with a specific tag"""
        filters = [FilterParam(field="tags.id", operator="eq", value=tag_id)]

        if status:
            filters.append(FilterParam(field="status", operator="eq", value=status))

        posts = await self.crud.list_objects(session, filters=filters, prefetch=["tags"])
        return [PostResponse.model_validate(post) for post in posts]

    @action(method="POST", detail=False, url_path="bulk-archive")
    async def bulk_archive_posts(
        self, session: AsyncSession = Depends(get_session), *, post_ids: List[uuid.UUID]
    ) -> BulkOperationResponse:
        posts = await self.crud.list_objects(
            session, filters=[FilterParam(field="id", operator="in", value=post_ids)]
        )
        for post in posts:
            post.status = PostStatus.ARCHIVED
        updated_count = await self.crud.bulk_update(
            session, [PostUpdate.model_validate(post) for post in posts]
        )

        return BulkOperationResponse(
            success_count=updated_count, error_count=len(post_ids) - updated_count
        )

    async def perform_create(
        self,
        session: AsyncSession = Depends(get_session),
        data: PostCreate = Body(...),
    ) -> Post:
        if not data.slug:
            data.slug = self._generate_slug(data.title)

        if not data.reading_time:
            word_count = len(data.content.split())
            data.reading_time = max(1, word_count // 200)

        category_ids = data.category_ids
        tag_ids = data.tag_ids

        create_data = data.model_dump()
        create_data.pop("category_ids", None)
        create_data.pop("tag_ids", None)

        # Create the post using the base class
        post = await self.crud.create(session, obj_in=create_data, include=["categories", "tags"])

        # Handle relationships if provided
        if category_ids or tag_ids:
            if category_ids:
                # Fetch categories and add them to the post
                categories = await session.execute(
                    select(Category).where(Category.id.in_(category_ids))
                )
                post.categories.extend(categories.scalars().all())

            if tag_ids:
                # Fetch tags and add them to the post
                tags = await session.execute(select(Tag).where(Tag.id.in_(tag_ids)))
                post.tags.extend(tags.scalars().all())

            await session.commit()
            await session.refresh(post)

        return post

    async def perform_update(
        self,
        session: AsyncSession = Depends(get_session),
        *,
        id: uuid.UUID,
        data: PostUpdate = Body(...),
    ) -> Post:
        """Override update to add custom logic"""
        post = await self.crud.get_by_id(session, id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        # Generate slug if title changed and slug not provided
        if data.title and not data.slug:
            data.slug = self._generate_slug(data.title)

        # Calculate reading time if content changed
        if data.content and not data.reading_time:
            word_count = len(data.content.split())
            data.reading_time = max(1, word_count // 200)

        # Extract relationship data
        category_ids = data.category_ids
        tag_ids = data.tag_ids

        # Create a copy of data without relationship fields
        update_data = data.model_dump(exclude_unset=True)
        update_data.pop("category_ids", None)
        update_data.pop("tag_ids", None)

        # Update the post using the base class
        updated_post = await self.crud.update(session, obj=post, obj_in=update_data)

        # Handle relationships if provided
        if category_ids is not None or tag_ids is not None:
            if category_ids is not None:
                # Clear existing categories and add new ones
                updated_post.categories.clear()
                if category_ids:
                    categories = await session.execute(
                        select(Category).where(Category.id.in_(category_ids))
                    )
                    updated_post.categories.extend(categories.scalars().all())

            if tag_ids is not None:
                # Clear existing tags and add new ones
                updated_post.tags.clear()
                if tag_ids:
                    tags = await tag_crud.list_objects(
                        session, filters=[FilterParam(field="id", operator="in", value=tag_ids)]
                    )
                    updated_post.tags.extend(tags)

            await session.commit()
            await session.refresh(updated_post)

        return updated_post

    def _generate_slug(self, title: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug.strip("-")[:200]


# Category CRUD Router
class CategoryRouterFactory(RouterFactory[Category, uuid.UUID, CategoryCreate, CategoryUpdate]):
    """Extended CRUD router for Categories"""

    @action(method="GET", detail=False, url_path="active")
    async def get_active_categories(
        self, session: AsyncSession = Depends(get_session)
    ) -> List[CategoryResponse]:
        """Get all active categories"""
        filters = [FilterParam(field="is_active", operator="eq", value=True)]
        categories = await self.crud.list_objects(session, filters=filters)
        return [CategoryResponse.model_validate(cat) for cat in categories]

    @action(method="GET", detail=True, url_path="posts")
    async def get_category_posts(
        self, session: AsyncSession = Depends(get_session), *, id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """Get all posts in a category"""
        category = await self.crud.get_by_id(session, id, prefetch=["posts"])
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        return [
            {
                "id": str(post.id),
                "title": post.title,
                "slug": post.slug,
                "status": post.status,
                "view_count": post.view_count,
                "created_at": post.created_at.isoformat(),
            }
            for post in category.posts
        ]


class TagRouterFactory(RouterFactory[Tag, uuid.UUID, TagCreate, TagUpdate]):
    @action(method="GET", detail=False, url_path="popular")
    async def get_popular_tags(
        self, session: AsyncSession = Depends(get_session), *, min_usage: int = 5
    ) -> List[TagResponse]:
        """Get popular tags based on usage count"""
        filters = [FilterParam(field="usage_count", operator="ge", value=min_usage)]
        tags = await self.crud.list_objects(session, filters=filters)
        return [TagResponse.model_validate(tag) for tag in tags]

    @action(method="GET", detail=True, url_path="posts")
    async def get_tag_posts(
        self, session: AsyncSession = Depends(get_session), *, id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """Get all posts with a tag"""
        tag = await self.crud.get_by_id(session, id, prefetch=["posts"])
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        return [
            {
                "id": str(post.id),
                "title": post.title,
                "slug": post.slug,
                "status": post.status,
                "view_count": post.view_count,
                "created_at": post.created_at.isoformat(),
            }
            for post in tag.posts
        ]


post_crud = BaseCRUD[Post, uuid.UUID, PostCreate, PostUpdate](
    model=Post,
    hooks=PostHooks(),
)

post_router_factory = PostRouterFactory(
    crud=post_crud,
    session_factory=get_session,
    create_schema=PostCreate,
    update_schema=PostUpdate,
    prefix="/posts",
    tags=["posts"],
    enable_pagination=True,
    search_fields=["title", "content", "excerpt"],
    sort_default="-created_at",
    page_size=20,
    max_page_size=50,
    response_schemas={
        "create": PostResponse,
        "update": PostResponse,
        "read": PostDetailResponse,
        "list": PostResponse,
        "bulk_create": PostResponse,
        "bulk_update": PostResponse,
        "bulk_delete": PostResponse,
    },
)

category_crud = BaseCRUD[Category, uuid.UUID, CategoryCreate, CategoryUpdate](model=Category)

category_router_factory = CategoryRouterFactory(
    crud=category_crud,
    session_factory=get_session,
    create_schema=CategoryCreate,
    update_schema=CategoryUpdate,
    prefix="/categories",
    tags=["categories"],
    enable_pagination=True,
    search_fields=["name", "description"],
    sort_default="-created_at",
    page_size=20,
    max_page_size=50,
    response_schemas={
        "create": CategoryResponse,
        "update": CategoryResponse,
        "read": CategoryResponse,
        "list": CategoryResponse,
        "bulk_create": CategoryResponse,
        "bulk_update": CategoryResponse,
        "bulk_delete": CategoryResponse,
    },
)


tag_crud = BaseCRUD[Tag, uuid.UUID, TagCreate, TagUpdate](model=Tag)

tag_router_factory = TagRouterFactory(
    crud=tag_crud,
    session_factory=get_session,
    create_schema=TagCreate,
    update_schema=TagUpdate,
    prefix="/tags",
    tags=["tags"],
    enable_pagination=True,
    search_fields=["name", "description"],
    sort_default="-created_at",
    page_size=20,
    max_page_size=50,
    response_schemas={
        "create": TagResponse,
        "update": TagResponse,
        "read": TagResponse,
        "list": TagResponse,
        "bulk_create": TagResponse,
        "bulk_update": TagResponse,
        "bulk_delete": TagResponse,
    },
)

post_router = post_router_factory.get_router()
category_router = category_router_factory.get_router()
tag_router = tag_router_factory.get_router()
