#!/usr/bin/env python3
"""
Build script for FastAPI-AutoCRUD package.
This script helps developers build the package for distribution.
"""

import os
import shutil
import subprocess
import sys


def run_command(command: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, command)

    return result


def clean_build():
    """Clean previous build artifacts."""

    # Remove build directories
    for path in ["build", "dist", "*.egg-info"]:
        if os.path.exists(path):
            shutil.rmtree(path)


def install_build_deps():
    run_command("pip install build wheel setuptools")


def build_package():
    """Build the package."""
    print("Building package...")
    run_command("python -m build --wheel")


def check_package():
    """Check the built package."""
    print("Checking package...")
    run_command("twine check dist/*")


def main():
    """Main build function."""
    print("🚀 FastAPI-AutoCRUD Build Script")
    print("=" * 40)

    try:
        # Clean previous builds
        clean_build()

        # Install build dependencies
        install_build_deps()

        # Build package
        build_package()

        # Check package
        check_package()

        print("\n✅ Build completed successfully!")

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
