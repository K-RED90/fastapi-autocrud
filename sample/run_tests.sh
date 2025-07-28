#!/bin/bash

# FastAPI-AutoCRUD Comprehensive Test Runner
# This script sets up the environment and runs all tests

set -e  # Exit on any error

echo "🚀 FastAPI-AutoCRUD Comprehensive Testing Setup"
echo "======================================"

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Please run this script from the auto_crud root directory"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

echo "📦 Installing dependencies..."

# Install core dependencies
if command -v uv &> /dev/null; then
    echo "   Using uv for fast installation..."
    uv pip install -e .
    uv pip install -r examples/requirements.txt
else
    echo "   Using pip for installation..."
    pip install -e .
    pip install -r examples/requirements.txt
fi

echo "✅ Dependencies installed successfully"

echo ""
echo "🧪 Running comprehensive tests..."
echo "================================"

# Run the comprehensive test suite
cd examples
python test_all_features.py

echo ""
echo "🌐 Starting FastAPI server for manual testing..."
echo "==============================================="
echo "The server will start at: http://127.0.0.1:8000"
echo "API documentation: http://127.0.0.1:8000/docs"
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server (optional)
read -p "Do you want to start the FastAPI server? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    uvicorn example_usage:app --reload --port 8000
fi 