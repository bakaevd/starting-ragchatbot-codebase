#!/bin/bash

# Quality check script for RAG chatbot codebase
# Run all code quality checks in sequence

echo "🔍 Running code quality checks..."

echo "📝 Running Black formatter check..."
uv run black --check --diff backend/ main.py
BLACK_EXIT_CODE=$?

echo "📋 Running isort import sorting check..."
uv run isort --check-only --diff backend/ main.py
ISORT_EXIT_CODE=$?

echo "🔍 Running Flake8 linting..."
uv run flake8 backend/ main.py
FLAKE8_EXIT_CODE=$?

echo "🧪 Running tests..."
uv run python backend/tests/run_all_tests.py
TESTS_EXIT_CODE=$?

# Summary
echo "📊 Quality Check Summary:"
if [ $BLACK_EXIT_CODE -eq 0 ]; then
    echo "✅ Black formatting: PASSED"
else
    echo "❌ Black formatting: FAILED"
fi

if [ $ISORT_EXIT_CODE -eq 0 ]; then
    echo "✅ Import sorting: PASSED"
else
    echo "❌ Import sorting: FAILED"
fi

if [ $FLAKE8_EXIT_CODE -eq 0 ]; then
    echo "✅ Flake8 linting: PASSED"
else
    echo "❌ Flake8 linting: FAILED"
fi

if [ $TESTS_EXIT_CODE -eq 0 ]; then
    echo "✅ Tests: PASSED"
else
    echo "❌ Tests: FAILED"
fi

# Exit with error if any check failed
if [ $BLACK_EXIT_CODE -ne 0 ] || [ $ISORT_EXIT_CODE -ne 0 ] || [ $FLAKE8_EXIT_CODE -ne 0 ] || [ $TESTS_EXIT_CODE -ne 0 ]; then
    echo "💥 Some quality checks failed. Please fix the issues above."
    exit 1
else
    echo "🎉 All quality checks passed!"
    exit 0
fi