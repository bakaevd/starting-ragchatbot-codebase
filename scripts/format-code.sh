#!/bin/bash

# Code formatting script for RAG chatbot codebase
# Auto-format all Python code with Black and isort

echo "🎨 Formatting Python code..."

echo "📝 Running Black formatter..."
uv run black backend/ main.py

echo "📋 Running isort for import sorting..."
uv run isort backend/ main.py

echo "✨ Code formatting complete!"