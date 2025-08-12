@echo off
REM Quality check script for RAG chatbot codebase (Windows)
REM Run all code quality checks in sequence

echo 🔍 Running code quality checks...

echo 📝 Running Black formatter check...
uv run black --check --diff backend/ main.py
set BLACK_EXIT_CODE=%ERRORLEVEL%

echo 📋 Running isort import sorting check...
uv run isort --check-only --diff backend/ main.py
set ISORT_EXIT_CODE=%ERRORLEVEL%

echo 🔍 Running Flake8 linting...
uv run flake8 backend/ main.py
set FLAKE8_EXIT_CODE=%ERRORLEVEL%

echo 🧪 Running tests...
uv run python backend/tests/run_all_tests.py
set TESTS_EXIT_CODE=%ERRORLEVEL%

REM Summary
echo 📊 Quality Check Summary:
if %BLACK_EXIT_CODE% equ 0 (
    echo ✅ Black formatting: PASSED
) else (
    echo ❌ Black formatting: FAILED
)

if %ISORT_EXIT_CODE% equ 0 (
    echo ✅ Import sorting: PASSED
) else (
    echo ❌ Import sorting: FAILED
)

if %FLAKE8_EXIT_CODE% equ 0 (
    echo ✅ Flake8 linting: PASSED
) else (
    echo ❌ Flake8 linting: FAILED
)

if %TESTS_EXIT_CODE% equ 0 (
    echo ✅ Tests: PASSED
) else (
    echo ❌ Tests: FAILED
)

REM Exit with error if any check failed
if %BLACK_EXIT_CODE% neq 0 goto :failed
if %ISORT_EXIT_CODE% neq 0 goto :failed
if %FLAKE8_EXIT_CODE% neq 0 goto :failed
if %TESTS_EXIT_CODE% neq 0 goto :failed

echo 🎉 All quality checks passed!
exit /b 0

:failed
echo 💥 Some quality checks failed. Please fix the issues above.
exit /b 1