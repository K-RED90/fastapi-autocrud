# Contributing to FastAPI-AutoCRUD

Thank you for your interest in contributing to FastAPI-AutoCRUD! This document provides guidelines and information for contributors.

## Getting Started

### Prerequisites

- Python 3.12 or higher
- Git
- pip (latest version)

### Development Setup

1. **Fork the repository**
   ```bash
   # Fork on GitHub, then clone your fork
   git clone https://github.com/K-RED90/fastapi-autocrud.git
cd fastapi-autocrud
   ```

2. **Set up development environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install in development mode
   pip install -e ".[test]"
   ```

3. **Verify setup**
   ```bash
   # Run tests
   pytest

   # Run linting
   ruff check .

   # Check formatting
   ruff format --check .
   ```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Write your code following the coding standards
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=auto_crud --cov-report=html

# Run linting
ruff check .

# Check formatting
ruff format --check .
```

### 4. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: add new feature description"

# Push to your fork
git push origin feature/your-feature-name
```

### 5. Create a Pull Request

1. Go to your fork on GitHub
2. Click "New Pull Request"
3. Select your feature branch
4. Fill out the PR template
5. Submit the PR

## Coding Standards

### Python Code Style

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Format code
ruff format .

# Check code style
ruff check .

# Auto-fix issues
ruff check --fix .
```

### Code Style Guidelines

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose
- Use meaningful variable and function names


## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_router.py

# Run tests with coverage
pytest --cov=auto_crud --cov-report=html

# Run tests in parallel
pytest -n auto
```

### Writing Tests

- Write tests for all new functionality
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern
- Use fixtures for common setup
- Test both success and error cases

### Example Test

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_create_user_success(db: AsyncSession):
    """Test successful user creation."""
    # Arrange
    user_data = {"email": "test@example.com", "name": "Test User"}
    
    # Act
    user = await create_user(db, user_data)
    
    # Assert
    assert user.email == "test@example.com"
    assert user.name == "Test User"
```

## Documentation

### Code Documentation

- Write docstrings for all public functions and classes
- Use Google-style docstrings
- Include type hints
- Document exceptions that may be raised

### README Updates

- Update README.md for new features
- Add usage examples
- Update installation instructions if needed
- Keep the documentation current

## Pull Request Guidelines

### Before Submitting

1. **Ensure tests pass**
   ```bash
   pytest
   ```

2. **Check code style**
   ```bash
   ruff check .
   ruff format --check .
   ```

3. **Update documentation**
   - Update docstrings
   - Update README if needed
   - Add usage examples

4. **Check for security issues**
   - Review code for potential security vulnerabilities
   - Ensure proper input validation
   - Check for SQL injection vulnerabilities

### PR Description

Include in your PR description:

- **Summary**: Brief description of changes
- **Motivation**: Why this change is needed
- **Changes**: Detailed list of changes
- **Testing**: How you tested the changes
- **Breaking Changes**: Any breaking changes

### Example PR Description

```markdown
## Summary
Add support for bulk operations in RouterFactory

## Motivation
Users need to perform bulk create, update, and delete operations efficiently.

## Changes
- Add bulk_create, bulk_update, bulk_delete methods to RouterFactory
- Add bulk endpoints to generated routers
- Add BulkResponse schema for bulk operation responses
- Add comprehensive tests for bulk operations

## Breaking Changes
None - all changes are backward compatible
```

## Release Process

### Version Bumping

We use semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Creating a Release

1. **Update version**
   ```bash
   # Update version in pyproject.toml
   # Update __version__ in auto_crud/__init__.py
   ```

2. **Create release branch**
   ```bash
   git checkout -b release/v0.1.1
   git commit -m "chore: bump version to 0.1.1"
   git push origin release/v0.1.1
   ```

3. **Create PR for release**
   - Create PR from release branch to main
   - Get review and approval
   - Merge to main

4. **Tag and release**
   ```bash
   git tag v0.1.1
   git push origin v0.1.1
   ```

## Getting Help

### Questions and Issues

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Code Review**: Ask questions in PR reviews

### Communication

- Be respectful and inclusive
- Use clear, descriptive language
- Provide context for questions
- Help others when you can

## Recognition

Contributors will be recognized in:

- GitHub contributors list
- Release notes
- Project documentation
- Contributor hall of fame (if applicable)

Thank you for contributing to FastAPI-AutoCRUD! 🚀 