#!/usr/bin/env python3
"""
Installation verification script for FastAPI-AutoCRUD.
This script helps users verify that FastAPI-AutoCRUD is installed correctly.
"""

import importlib
import sys
from typing import List, Tuple


def check_python_version() -> bool:
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 12:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print(
            f"❌ Python {version.major}.{version.minor}.{version.micro} is not compatible (requires 3.12+)"
        )
        return False


def check_imports() -> List[Tuple[str, bool]]:
    """Check if all required packages can be imported."""
    required_packages = [
        "fastapi",
        "pydantic",
        "sqlalchemy",
        "loguru",
    ]

    results = []

    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package} is available")
            results.append((package, True))
        except ImportError as e:
            print(f"❌ {package} is not available: {e}")
            results.append((package, False))

    return results


def check_autocrud_import() -> bool:
    """Check if FastAPI-AutoCRUD can be imported."""
    try:
        import auto_crud

        print(f"✅ FastAPI-AutoCRUD {auto_crud.__version__} is installed")

        # Check core components
        from auto_crud import BaseCRUD, RouterFactory, action

        print("✅ Core components are available")

        return True
    except ImportError as e:
        print(f"❌ FastAPI-AutoCRUD is not installed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error importing FastAPI-AutoCRUD: {e}")
        return False


def main():
    """Main verification function."""
    print("🔍 FastAPI-AutoCRUD Installation Verification")
    print("=" * 50)

    all_passed = True

    # Check Python version
    if not check_python_version():
        all_passed = False

    print()

    # Check required packages
    print("Checking required packages...")
    import_results = check_imports()
    if not all(result[1] for result in import_results):
        all_passed = False

    print()

    # Check FastAPI-AutoCRUD import
    print("Checking FastAPI-AutoCRUD installation...")
    if not check_autocrud_import():
        all_passed = False

    print()

    print()
    print("=" * 50)

    if all_passed:
        print("🎉 All checks passed! FastAPI-AutoCRUD is installed correctly.")
        print("\nYou can now use FastAPI-AutoCRUD in your FastAPI applications.")
        print("Check the README.md for usage examples.")
    else:
        print("❌ Some checks failed. Please review the errors above.")
        print("\nTroubleshooting tips:")
        print("1. Make sure you're using Python 3.12 or higher")
        print(
            "2. Install FastAPI-AutoCRUD: pip install git+https://github.com/K-RED90/auto_crud.git"
        )
        print("3. Check the INSTALL.md file for detailed instructions")
        sys.exit(1)


if __name__ == "__main__":
    main()
