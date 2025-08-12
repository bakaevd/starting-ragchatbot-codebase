# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Start the application:**
```bash
# Quick start (recommended)
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

**Install dependencies:**
```bash
uv sync
```

**Important**: Always use `uv` for dependency management - do not use `pip` directly. All Python commands should be run through `uv run`.

**Code Quality:**
```bash
# Format code automatically (recommended before committing)
./scripts/format-code.sh        # Unix/Mac
scripts\format-code.bat         # Windows

# Run all quality checks
./scripts/quality-check.sh      # Unix/Mac  
scripts\quality-check.bat       # Windows

# Individual quality checks
uv run black --check backend/ main.py    # Check formatting
uv run black backend/ main.py            # Auto-format code
uv run isort backend/ main.py            # Sort imports
uv run flake8 backend/ main.py           # Run linting
```

**Access points:**
- Web interface: http://localhost:8000
- API docs: http://localhost:8000/docs

## Architecture Overview

This is a **Retrieval-Augmented Generation (RAG) system** built as a full-stack web application for querying course materials using AI. The architecture follows a modular design with clear separation of concerns:

### Core Flow Pattern
The system implements a **tool-enhanced RAG pipeline**:
1. User queries enter via FastAPI endpoints
2. RAG system orchestrates the flow through AI Generator 
3. Claude AI decides whether to use search tools based on query content
4. If tools are used: semantic search → context retrieval → final AI response
5. Response includes generated answer + source citations

### Key Architectural Components

**RAG System (`rag_system.py`)** - Central orchestrator that coordinates all components. This is the main entry point for query processing and manages the flow between AI generation, tool execution, and session handling.

**AI Generator (`ai_generator.py`)** - Handles two-phase Claude API interaction:
- Phase 1: Initial call with available tools 
- Phase 2: Follow-up call with tool results (if tools were used)
- Implements tool execution detection and conversation context management

**Tool System (`search_tools.py`)** - Modular tool architecture using abstract base classes:
- `Tool` interface for extensible tool definitions
- `CourseSearchTool` for semantic course content search
- `ToolManager` for tool registration and execution coordination

**Vector Store (`vector_store.py`)** - ChromaDB integration with dual collections:
- `course_catalog`: Course metadata for name resolution
- `course_content`: Chunked course material for content search
- Implements course name fuzzy matching and filtered search

**Document Processor (`document_processor.py`)** - Structured text processing pipeline:
- Expects specific document format with course metadata headers
- Parses lessons using regex patterns (`Lesson N: Title`)
- Implements sentence-boundary-aware chunking with configurable overlap
- Adds contextual prefixes to chunks for better retrieval

### Configuration System

**Environment Setup Required:**
- `.env` file with `ANTHROPIC_API_KEY`
- Course documents in `/docs` folder (loaded automatically on startup)

**Key Configuration (`config.py`):**
- `CHUNK_SIZE`: 800 characters (balance between context and precision)
- `CHUNK_OVERLAP`: 100 characters (maintains context across chunks)
- `MAX_RESULTS`: 5 (vector search limit)
- `MAX_HISTORY`: 2 (conversation memory)

### Expected Document Format

Course files in `/docs` should follow this structure:
```
Course Title: [Title]
Course Link: [URL]
Course Instructor: [Name]

Lesson 0: Introduction
Lesson Link: [URL]
[Content...]

Lesson 1: [Next lesson title]
[Content...]
```

### Session Management

The system maintains conversation context through `SessionManager`:
- Tracks conversation history per session
- Enables contextual follow-up questions
- Session IDs persist across frontend interactions

### Frontend Integration

- Pure HTML/CSS/JS frontend served as static files
- Real-time chat interface with markdown rendering
- Source citation display in collapsible UI elements
- Automatic course statistics loading from `/api/courses` endpoint

## Important Implementation Notes

- **Tool Usage Philosophy**: Claude decides tool usage - no forced search on every query
- **Two-Phase AI Calls**: Tool-based queries require two separate Claude API calls  
- **Context Enhancement**: Chunks include course/lesson context for better retrieval accuracy
- **Source Tracking**: Tool manager tracks and provides source citations for responses
- **Error Handling**: Graceful fallbacks for missing courses, failed searches, API errors
- always use uv to run the server do not use pip directly
- use uv to run Python files
- make sure to use uv to manage all dependencies