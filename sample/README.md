# FastAPI-AutoCRUD Comprehensive Example

This is a comprehensive example demonstrating all FastAPI-AutoCRUD features and capabilities. It showcases a complete blog system with users, posts, categories, tags, comments, likes, and analytics.

## 🚀 Features Showcased

### Core FastAPI-AutoCRUD Features

#### 1. **Full CRUD Operations**
- ✅ Create, Read, Update, Delete with automatic endpoint generation
- ✅ Pagination with customizable page sizes
- ✅ Bulk operations (create, update, delete)
- ✅ Optimistic locking and conflict resolution

#### 2. **Advanced Filtering System**
- ✅ Multiple filter operators (EQ, NE, GT, LT, GE, LE, IN, NOT_IN, LIKE, ILIKE)
- ✅ Complex filter combinations
- ✅ Relationship filtering
- ✅ Date range filtering
- ✅ Enum filtering

#### 3. **Search Functionality**
- ✅ Full-text search across multiple fields
- ✅ Search with filters
- ✅ Search in relationships
- ✅ Custom search implementations

#### 4. **Sorting & Pagination**
- ✅ Multi-field sorting
- ✅ Custom sort orders
- ✅ Default sorting
- ✅ Sort field validation

#### 5. **Custom Actions**
- ✅ Extended endpoints with business logic
- ✅ Custom HTTP methods
- ✅ Complex business operations
- ✅ Relationship management

### Advanced Features

#### 6. **Comprehensive Hooks System**
- ✅ Pre/post hooks for all operations
- ✅ Custom validation logic
- ✅ Business rule enforcement
- ✅ Analytics tracking
- ✅ Data transformation

#### 7. **Relationship Management**
- ✅ Many-to-many relationships
- ✅ One-to-many relationships
- ✅ Self-referencing relationships
- ✅ Cascade operations
- ✅ Lazy loading

#### 8. **Custom Validation**
- ✅ Schema-level validation
- ✅ Business rule validation
- ✅ Custom validators
- ✅ Error handling

#### 9. **Analytics & Tracking**
- ✅ Automatic event tracking
- ✅ User activity monitoring
- ✅ Content engagement metrics
- ✅ Performance analytics

#### 10. **Role-Based Access Control**
- ✅ User roles and permissions
- ✅ Action-based authorization
- ✅ Content ownership validation
- ✅ Admin/moderator privileges

## 📊 Data Model

### Entities & Relationships

```
User (1) ──── (N) Post
User (N) ──── (N) User (Followers)
Post (N) ──── (N) Category
Post (N) ──── (N) Tag
Post (1) ──── (N) Comment
Post (1) ──── (N) Like
User (1) ──── (N) Comment
User (1) ──── (N) Like
Category (1) ──── (N) Category (Hierarchy)
Comment (1) ──── (N) Comment (Replies)
```

### Key Features by Entity

#### **Users**
- Role-based access control (Admin, Moderator, Author, Reader)
- Following/follower system
- User verification and activation
- Activity tracking
- Profile management

#### **Posts**
- Status management (Draft, Published, Archived, Deleted)
- SEO optimization (title, description, slug)
- Reading time calculation
- View count tracking
- Engagement metrics
- Category and tag associations

#### **Categories**
- Hierarchical organization
- Color coding
- Post count tracking
- Active/inactive status

#### **Tags**
- Usage count tracking
- Color coding
- Popular tags identification
- Post associations

#### **Comments**
- Nested replies
- Spam detection
- Approval workflow
- Author tracking

#### **Likes**
- User-post relationships
- Duplicate prevention
- Count tracking

#### **Analytics**
- Event tracking
- User activity monitoring
- Content engagement
- Performance metrics

## 🔧 API Endpoints

### Users (`/api/v1/users`)
```
GET    /users                    # List users with pagination
POST   /users                    # Create user
GET    /users/{id}               # Get user by ID
PUT    /users/{id}               # Update user
DELETE /users/{id}               # Delete user
POST   /users/bulk-create        # Bulk create users
PUT    /users/bulk-update        # Bulk update users
DELETE /users/bulk-delete        # Bulk delete users

# Custom Actions
GET    /users/active             # Get active users
GET    /users/verified           # Get verified users
GET    /users/authors            # Get authors
POST   /users/{id}/deactivate    # Deactivate user
POST   /users/{id}/activate      # Activate user
POST   /users/{id}/verify        # Verify user
GET    /users/{id}/stats         # Get user statistics
GET    /users/{id}/posts         # Get user posts
GET    /users/{id}/followers     # Get user followers
GET    /users/{id}/following     # Get user following
POST   /users/{id}/follow/{target_id}    # Follow user
DELETE /users/{id}/unfollow/{target_id}  # Unfollow user
GET    /users/search             # Search users
GET    /users/online             # Get online users
POST   /users/{id}/update-last-login     # Update last login
POST   /users/bulk-activate      # Bulk activate users
POST   /users/bulk-deactivate    # Bulk deactivate users
```

### Posts (`/api/v1/posts`)
```
GET    /posts                    # List posts with pagination
POST   /posts                    # Create post
GET    /posts/{id}               # Get post by ID
PUT    /posts/{id}               # Update post
DELETE /posts/{id}               # Delete post
POST   /posts/bulk-create        # Bulk create posts
PUT    /posts/bulk-update        # Bulk update posts
DELETE /posts/bulk-delete        # Bulk delete posts

# Custom Actions
GET    /posts/published           # Get published posts
GET    /posts/draft              # Get draft posts
GET    /posts/popular            # Get popular posts
GET    /posts/trending           # Get trending posts
POST   /posts/{id}/publish       # Publish post
POST   /posts/{id}/unpublish     # Unpublish post
POST   /posts/{id}/archive       # Archive post
GET    /posts/{id}/stats         # Get post statistics
GET    /posts/{id}/comments      # Get post comments
GET    /posts/{id}/likes         # Get post likes
POST   /posts/{id}/like          # Like post
DELETE /posts/{id}/unlike        # Unlike post
GET    /posts/search             # Search posts
GET    /posts/by-category/{category_id}  # Get posts by category
GET    /posts/by-tag/{tag_id}    # Get posts by tag
GET    /posts/by-author/{author_id}      # Get posts by author
POST   /posts/bulk-publish       # Bulk publish posts
POST   /posts/bulk-archive       # Bulk archive posts
```

### Categories (`/api/v1/categories`)
```
GET    /categories               # List categories with pagination
POST   /categories               # Create category
GET    /categories/{id}          # Get category by ID
PUT    /categories/{id}          # Update category
DELETE /categories/{id}          # Delete category

# Custom Actions
GET    /categories/active        # Get active categories
GET    /categories/{id}/posts    # Get category posts
GET    /categories/{id}/stats    # Get category statistics
```

### Tags (`/api/v1/tags`)
```
GET    /tags                     # List tags with pagination
POST   /tags                     # Create tag
GET    /tags/{id}                # Get tag by ID
PUT    /tags/{id}                # Update tag
DELETE /tags/{id}                # Delete tag

# Custom Actions
GET    /tags/popular             # Get popular tags
GET    /tags/{id}/posts          # Get tag posts
```

## 🎯 Key Demonstrations

### 1. **Custom Actions**
- User follow/unfollow system
- Post publish/unpublish workflow
- Bulk operations with error handling
- Search with filters
- Statistics and analytics

### 2. **Hooks System**
- Password hashing in pre-create hooks
- Analytics tracking in post hooks
- Business rule validation
- Spam detection
- Permission checking

### 3. **Advanced Filtering**
```python
# Complex filters example
filters = [
    FilterParam(field="status", operator="eq", value="published"),
    FilterParam(field="view_count", operator="ge", value=10),
    FilterParam(field="created_at", operator="ge", value=cutoff_date)
]
```

### 4. **Relationship Management**
- Many-to-many: Posts ↔ Categories, Posts ↔ Tags
- One-to-many: Users → Posts, Posts → Comments
- Self-referencing: User followers, Comment replies

### 5. **Computed Fields**
- Reading time calculation
- Engagement rate computation
- Display name generation
- Online status detection

### 6. **Business Logic**
- Role-based permissions
- Content ownership validation
- Spam detection
- Status management
- Analytics tracking

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL
- FastAPI
- SQLAlchemy
- Pydantic

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Set up database
# (Configure your database connection in db.py)

# Run the application
python -m sample.main
```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📈 Performance Features

### 1. **Optimized Queries**
- Lazy loading of relationships
- Efficient pagination
- Indexed fields for fast filtering
- Optimized bulk operations

### 2. **Caching Strategy**
- Query result caching
- Relationship caching
- Analytics aggregation

### 3. **Database Optimization**
- Proper indexing
- Efficient joins
- Query optimization
- Connection pooling

## 🔒 Security Features

### 1. **Authentication & Authorization**
- Role-based access control
- Action-based permissions
- Content ownership validation

### 2. **Data Validation**
- Schema-level validation
- Business rule validation
- Input sanitization
- SQL injection prevention

### 3. **Audit Trail**
- Comprehensive logging
- Analytics tracking
- User activity monitoring
- Change tracking

## 🧪 Testing

### Test Coverage
- Unit tests for all CRUD operations
- Integration tests for relationships
- Performance tests for bulk operations
- Security tests for permissions

### Example Test Cases
```python
# Test custom actions
async def test_user_follow():
    # Test follow/unfollow functionality
    
# Test hooks
async def test_password_hashing():
    # Test password hashing in hooks
    
# Test filtering
async def test_complex_filters():
    # Test advanced filtering
```

## 📊 Monitoring & Analytics

### 1. **Performance Metrics**
- Response time tracking
- Database query optimization
- Memory usage monitoring
- Error rate tracking

### 2. **Business Metrics**
- User engagement
- Content popularity
- System usage patterns
- Error analysis

### 3. **Health Checks**
- Database connectivity
- Service availability
- Performance thresholds
- Error monitoring

## 🔧 Configuration

### Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@localhost/dbname
DEBUG=True
LOG_LEVEL=INFO
```

### Database Configuration
```python
# Configure your database connection
DATABASE_URL = "postgresql://user:pass@localhost/autocrud_example"
```

## 🤝 Contributing

This example demonstrates the full capabilities of FastAPI-AutoCRUD. Feel free to:

1. **Extend the features** - Add more custom actions
2. **Improve the models** - Add more complex relationships
3. **Enhance the hooks** - Add more business logic
4. **Optimize performance** - Improve query efficiency
5. **Add tests** - Increase test coverage

## 📚 Learning Resources

- [FastAPI-AutoCRUD Documentation](https://autocrud.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)

## 🎯 Use Cases

This comprehensive example is perfect for:

1. **Learning FastAPI-AutoCRUD** - Understand all features
2. **API Development** - Use as a template for real projects
3. **Testing** - Validate FastAPI-AutoCRUD capabilities
4. **Demonstration** - Showcase to stakeholders
5. **Prototyping** - Rapid application development

## 📄 License

This example is provided as-is for educational and demonstration purposes. 