import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from rag_system import RAGSystem
from vector_store import SearchResults
from models import Course, Lesson, CourseChunk


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    class MockConfig:
        def __init__(self):
            self.CHUNK_SIZE = 800
            self.CHUNK_OVERLAP = 100
            self.CHROMA_PATH = "./test_chroma_db"
            self.EMBEDDING_MODEL = "test-model"
            self.MAX_RESULTS = 5
            self.ANTHROPIC_API_KEY = "test_key"
            self.ANTHROPIC_MODEL = "test_model"
            self.MAX_HISTORY = 2
    
    return MockConfig()


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing"""
    mock = Mock()
    mock.search.return_value = SearchResults([], [], [])
    mock.get_course_count.return_value = 3
    mock.get_existing_course_titles.return_value = ["Course A", "Course B", "Course C"]
    return mock


@pytest.fixture
def mock_ai_generator():
    """Mock AI generator for testing"""
    mock = Mock()
    mock.generate_response.return_value = "Mock AI response"
    return mock


@pytest.fixture
def mock_session_manager():
    """Mock session manager for testing"""
    mock = Mock()
    mock.get_conversation_history.return_value = None
    mock.create_session.return_value = "test_session_123"
    return mock


@pytest.fixture
def mock_tool_manager():
    """Mock tool manager for testing"""
    mock = Mock()
    mock.get_tool_definitions.return_value = [{"name": "mock_tool", "description": "Mock tool"}]
    mock.get_last_sources.return_value = []
    mock.reset_sources.return_value = None
    return mock


@pytest.fixture
def mock_rag_system(mock_config, mock_vector_store, mock_ai_generator, mock_session_manager, mock_tool_manager):
    """Mock RAG system with all dependencies mocked"""
    with patch('rag_system.DocumentProcessor'), \
         patch('rag_system.VectorStore', return_value=mock_vector_store), \
         patch('rag_system.AIGenerator', return_value=mock_ai_generator), \
         patch('rag_system.SessionManager', return_value=mock_session_manager), \
         patch('rag_system.ToolManager', return_value=mock_tool_manager), \
         patch('rag_system.CourseSearchTool'):
        
        # Create a mock RAG system instead of the real one
        mock_rag = Mock()
        mock_rag.query = Mock(return_value=("Mock response", []))
        mock_rag.get_course_analytics = Mock(return_value={"total_courses": 0, "course_titles": []})
        mock_rag.session_manager = mock_session_manager
        
        return mock_rag


@pytest.fixture
def test_app(mock_rag_system):
    """Create a test FastAPI app with mocked dependencies"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional
    
    # Create test app without static file mounting to avoid path issues
    app = FastAPI(title="Test Course Materials RAG System")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Pydantic models (same as in app.py)
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None
    
    class SourceItem(BaseModel):
        text: str
        url: Optional[str] = None
    
    class QueryResponse(BaseModel):
        answer: str
        sources: List[SourceItem]
        session_id: str
    
    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]
    
    # API endpoints (same logic as app.py but inline)
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id or mock_rag_system.session_manager.create_session()
            answer, sources = mock_rag_system.query(request.query, session_id)
            
            source_items = []
            for source in sources:
                if isinstance(source, dict):
                    source_items.append(SourceItem(
                        text=source.get('text', str(source)),
                        url=source.get('url')
                    ))
                else:
                    source_items.append(SourceItem(text=str(source)))
            
            return QueryResponse(
                answer=answer,
                sources=source_items,
                session_id=session_id
            )
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/")
    async def root():
        return {"message": "Test RAG System API"}
    
    return app


@pytest.fixture
def test_client(test_app):
    """Create a test client for the FastAPI app"""
    return TestClient(test_app)


@pytest.fixture
def temp_docs_dir():
    """Create a temporary directory with test documents"""
    temp_dir = tempfile.mkdtemp()
    docs_dir = Path(temp_dir) / "docs"
    docs_dir.mkdir()
    
    # Create a test course document
    test_course = docs_dir / "test_course.txt"
    test_course.write_text("""Course Title: Introduction to AI
Course Link: https://example.com/ai-course
Course Instructor: Dr. Smith

Lesson 0: What is AI?
Lesson Link: https://example.com/lesson0
Artificial Intelligence is the simulation of human intelligence processes by machines.

Lesson 1: Machine Learning Basics
Lesson Link: https://example.com/lesson1
Machine learning is a subset of AI that enables systems to learn and improve automatically.
""")
    
    yield str(docs_dir)
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_query_request():
    """Sample query request for testing"""
    return {
        "query": "What is machine learning?",
        "session_id": "test_session_123"
    }


@pytest.fixture
def sample_query_response():
    """Sample query response for testing"""
    return {
        "answer": "Machine learning is a subset of AI that enables systems to learn automatically.",
        "sources": [
            {"text": "Course: Introduction to AI - Lesson 1", "url": "https://example.com/lesson1"}
        ],
        "session_id": "test_session_123"
    }


@pytest.fixture
def sample_course_stats():
    """Sample course statistics for testing"""
    return {
        "total_courses": 3,
        "course_titles": ["Introduction to AI", "Data Science Fundamentals", "Deep Learning"]
    }


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks before each test"""
    yield
    # Any cleanup code can go here if needed