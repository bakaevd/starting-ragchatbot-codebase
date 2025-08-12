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

**Run individual Python files:**
```bash
uv run python backend/document_processor.py
uv run python main.py
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

**Testing/Development:**
- Course documents go in `/docs` folder (auto-loaded on startup)
- Environment variables in `.env` file (requires `ANTHROPIC_API_KEY`)

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

**RAG System (`rag_system.py`)** - Central orchestrator that coordinates all components. Entry point for query processing. Manages flow between AI generation, tool execution, and session handling. Key method: `query()` processes user questions through the two-phase AI interaction.

**AI Generator (`ai_generator.py`)** - Handles two-phase Claude API interaction with performance optimizations:
- Phase 1: Initial call with available tools (`generate_response()`)
- Phase 2: Follow-up call with tool results if tools were used (`_handle_tool_execution()`)
- Uses pre-built API parameters and static system prompts for efficiency
- Implements tool execution detection and conversation context management

**Tool System (`search_tools.py`)** - Modular architecture using abstract base classes:
- `Tool` interface for extensible tool definitions with `execute()` and `get_tool_definition()`
- `CourseSearchTool` for semantic course content search with source tracking
- `ToolManager` for tool registration, execution coordination, and source management
- Sources are tracked per search and include lesson links for UI display

**Vector Store (`vector_store.py`)** - ChromaDB integration with dual collections and unified search interface:
- `course_catalog`: Course metadata for fuzzy name resolution (uses sentence transformers)
- `course_content`: Chunked course material for semantic content search
- Main `search()` method handles course resolution, filtering, and content retrieval
- Implements complex filtering logic (`$and` operations) for course + lesson combinations

**Document Processor (`document_processor.py`)** - Structured text processing pipeline:
- Expects specific document format with course metadata headers
- Parses lessons using regex patterns (`Lesson N: Title`)
- Implements sentence-boundary-aware chunking (800 chars with 100 char overlap)
- Adds contextual prefixes to chunks including course and lesson information

### Configuration System

**Environment Setup Required:**
- `.env` file with `ANTHROPIC_API_KEY` (loaded from parent directory)
- Course documents in `/docs` folder (auto-loaded on startup)

**Key Configuration (`config.py`):**
- `ANTHROPIC_MODEL`: "claude-sonnet-4-20250514" (latest Claude model)
- `EMBEDDING_MODEL`: "all-MiniLM-L6-v2" (sentence transformers model)
- `CHUNK_SIZE`: 800 characters (balance between context and precision)
- `CHUNK_OVERLAP`: 100 characters (maintains context across chunks)
- `MAX_RESULTS`: 5 (vector search result limit)
- `MAX_HISTORY`: 2 (conversation memory limit)
- `CHROMA_PATH`: "./chroma_db" (persistent vector database location)

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

The system maintains conversation context through `SessionManager` (`session_manager.py`):
- Tracks conversation history per session with configurable limits
- Enables contextual follow-up questions within the same session
- Session IDs auto-generated if not provided and persist across frontend interactions
- Memory management prevents context overflow

### FastAPI Backend (`app.py`)

The web API provides RESTful endpoints:
- `POST /api/query`: Main query endpoint accepting `{query, session_id?}`
- `GET /api/courses`: Returns course statistics and titles
- Static file serving for frontend at root path
- CORS middleware configured for development
- Auto-loads course documents from `/docs` on startup
- Request/response models defined with Pydantic for type safety

### Frontend Integration

- Pure HTML/CSS/JS frontend (`frontend/`) served as static files
- Real-time chat interface with markdown rendering (`marked.js`)
- Source citation display in collapsible UI elements with lesson links
- Session persistence and loading states
- Automatic course statistics loading from `/api/courses` endpoint
- No build process - direct file serving

## Important Implementation Notes

- **Tool Usage Philosophy**: Claude autonomously decides when to use search tools - no forced search on every query
- **Two-Phase AI Architecture**: Tool-based queries require two separate Claude API calls for optimal results
- **Performance Optimizations**: Pre-built API parameters, static system prompts, and efficient string operations
- **Context Enhancement**: Chunks include course/lesson prefixes for better retrieval accuracy
- **Source Tracking**: Tool manager tracks sources with lesson links; sources reset after each query  
- **Error Handling**: Graceful fallbacks for missing courses, failed searches, and API errors
- **Memory Management**: Session history limited to prevent context overflow
- **Database Persistence**: ChromaDB data persists across restarts in `./chroma_db`
- **Dual Collection Strategy**: Separate collections for course metadata (name resolution) and content (search)

## Development Notes

- Always use `uv` for dependency management - never use `pip` directly
- All Python commands must be run through `uv run`
- Course documents auto-load from `/docs` on startup (no manual indexing required)
- Environment variables loaded from `.env` in parent directory
- Vector embeddings use sentence-transformers with "all-MiniLM-L6-v2" model
- Search supports partial course name matching and lesson number filtering