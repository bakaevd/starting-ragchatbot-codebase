import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any, Tuple

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from rag_system import RAGSystem
from vector_store import SearchResults
from models import Course, Lesson, CourseChunk


class MockConfig:
    """Mock configuration for testing"""
    
    def __init__(self):
        self.CHUNK_SIZE = 800
        self.CHUNK_OVERLAP = 100
        self.CHROMA_PATH = "./test_chroma_db"
        self.EMBEDDING_MODEL = "test-model"
        self.MAX_RESULTS = 5
        self.ANTHROPIC_API_KEY = "test_key"
        self.ANTHROPIC_MODEL = "test_model"
        self.MAX_HISTORY = 2


class MockDocumentProcessor:
    """Mock document processor"""
    
    def __init__(self, chunk_size, chunk_overlap):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap


class MockVectorStore:
    """Mock vector store for testing"""
    
    def __init__(self, chroma_path, embedding_model, max_results):
        self.search_results = None
        self.search_calls = []
        self.course_count = 0
        self.course_titles = []
        
    def search(self, query, course_name=None, lesson_number=None):
        self.search_calls.append({
            'query': query,
            'course_name': course_name,
            'lesson_number': lesson_number
        })
        return self.search_results or SearchResults([], [], [])
        
    def get_course_count(self):
        return self.course_count
        
    def get_existing_course_titles(self):
        return self.course_titles


class MockAIGenerator:
    """Mock AI generator"""
    
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model
        self.response = "Default mock response"
        self.generate_calls = []
        
    def generate_response(self, query, conversation_history=None, tools=None, tool_manager=None):
        call_info = {
            'query': query,
            'conversation_history': conversation_history,
            'tools': tools,
            'tool_manager': tool_manager
        }
        self.generate_calls.append(call_info)
        return self.response


class MockSessionManager:
    """Mock session manager"""
    
    def __init__(self, max_history):
        self.max_history = max_history
        self.sessions = {}
        self.exchanges = []
        
    def get_conversation_history(self, session_id):
        return self.sessions.get(session_id, "No previous conversation")
        
    def add_exchange(self, session_id, query, response):
        self.exchanges.append({
            'session_id': session_id,
            'query': query,
            'response': response
        })
        
    def create_session(self):
        return "test_session_123"


class MockToolManager:
    """Mock tool manager"""
    
    def __init__(self):
        self.tools = {}
        self.last_sources = []
        self.tool_calls = []
        
    def register_tool(self, tool):
        self.tools[tool.__class__.__name__] = tool
        
    def get_tool_definitions(self):
        return [{"name": "mock_tool", "description": "Mock tool"}]
        
    def execute_tool(self, tool_name, **kwargs):
        self.tool_calls.append({'tool_name': tool_name, 'kwargs': kwargs})
        return "Mock tool result"
        
    def get_last_sources(self):
        return self.last_sources
        
    def reset_sources(self):
        self.last_sources = []


class MockCourseSearchTool:
    """Mock course search tool"""
    
    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.last_sources = []


class MockCourseOutlineTool:
    """Mock course outline tool"""
    
    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.last_sources = []


class TestRAGSystem:
    """Test cases for RAGSystem end-to-end functionality"""
    
    def setup_method(self):
        """Set up test fixtures with mocked dependencies"""
        self.mock_config = MockConfig()
        
        # Mock all the components
        with patch('rag_system.DocumentProcessor', MockDocumentProcessor), \
             patch('rag_system.VectorStore', MockVectorStore), \
             patch('rag_system.AIGenerator', MockAIGenerator), \
             patch('rag_system.SessionManager', MockSessionManager), \
             patch('rag_system.ToolManager', MockToolManager), \
             patch('rag_system.CourseSearchTool', MockCourseSearchTool), \
             patch('rag_system.CourseOutlineTool', MockCourseOutlineTool):
            
            self.rag_system = RAGSystem(self.mock_config)
            
        # Get references to mocked components
        self.mock_vector_store = self.rag_system.vector_store
        self.mock_ai_generator = self.rag_system.ai_generator
        self.mock_session_manager = self.rag_system.session_manager
        self.mock_tool_manager = self.rag_system.tool_manager
        
    def test_initialization(self):
        """Test that RAGSystem initializes all components correctly"""
        assert self.rag_system.config == self.mock_config
        assert self.rag_system.document_processor is not None
        assert self.rag_system.vector_store is not None
        assert self.rag_system.ai_generator is not None
        assert self.rag_system.session_manager is not None
        assert self.rag_system.tool_manager is not None
        assert self.rag_system.search_tool is not None
        assert self.rag_system.outline_tool is not None
        
        # Verify tools were registered
        assert 'MockCourseSearchTool' in self.mock_tool_manager.tools
        assert 'MockCourseOutlineTool' in self.mock_tool_manager.tools
        
    def test_query_without_session_id(self):
        """Test query processing without session ID"""
        self.mock_ai_generator.response = "AI response to query"
        self.mock_tool_manager.last_sources = [{"text": "Test Source", "url": None}]
        
        response, sources = self.rag_system.query("What is machine learning?")
        
        assert response == "AI response to query"
        assert len(sources) == 1
        assert sources[0]["text"] == "Test Source"
        
        # Verify AI generator was called correctly
        assert len(self.mock_ai_generator.generate_calls) == 1
        call = self.mock_ai_generator.generate_calls[0]
        assert "What is machine learning?" in call['query']
        assert call['conversation_history'] is None
        assert call['tools'] == [{"name": "mock_tool", "description": "Mock tool"}]
        assert call['tool_manager'] == self.mock_tool_manager
        
        # Verify sources were reset
        assert len(self.mock_tool_manager.last_sources) == 0
        
    def test_query_with_session_id(self):
        """Test query processing with existing session"""
        session_id = "test_session_123"
        self.mock_session_manager.sessions[session_id] = "Previous conversation context"
        self.mock_ai_generator.response = "Contextual response"
        
        response, sources = self.rag_system.query("Follow-up question", session_id)
        
        assert response == "Contextual response"
        
        # Verify conversation history was passed
        call = self.mock_ai_generator.generate_calls[0]
        assert call['conversation_history'] == "Previous conversation context"
        
        # Verify session was updated
        assert len(self.mock_session_manager.exchanges) == 1
        exchange = self.mock_session_manager.exchanges[0]
        assert exchange['session_id'] == session_id
        assert exchange['query'] == "Follow-up question"
        assert exchange['response'] == "Contextual response"
        
    def test_query_with_sources(self):
        """Test query processing that returns sources"""
        self.mock_ai_generator.response = "Response with sources"
        self.mock_tool_manager.last_sources = [
            {"text": "Course A - Lesson 1", "url": "https://example.com/lesson1"},
            {"text": "Course B - Lesson 2", "url": None}
        ]
        
        response, sources = self.rag_system.query("Content query")
        
        assert response == "Response with sources"
        assert len(sources) == 2
        assert sources[0]["text"] == "Course A - Lesson 1"
        assert sources[0]["url"] == "https://example.com/lesson1"
        assert sources[1]["text"] == "Course B - Lesson 2"
        assert sources[1]["url"] is None
        
    def test_query_prompt_formatting(self):
        """Test that query prompt is formatted correctly"""
        self.rag_system.query("Test question")
        
        call = self.mock_ai_generator.generate_calls[0]
        query = call['query']
        
        assert "Answer this question about course materials:" in query
        assert "Test question" in query
        
    def test_query_tools_passed_correctly(self):
        """Test that tools are passed correctly to AI generator"""
        self.rag_system.query("Test question")
        
        call = self.mock_ai_generator.generate_calls[0]
        assert call['tools'] == [{"name": "mock_tool", "description": "Mock tool"}]
        assert call['tool_manager'] == self.mock_tool_manager
        
    def test_get_course_analytics(self):
        """Test course analytics retrieval"""
        self.mock_vector_store.course_count = 5
        self.mock_vector_store.course_titles = ["Course A", "Course B", "Course C"]
        
        analytics = self.rag_system.get_course_analytics()
        
        assert analytics["total_courses"] == 5
        assert analytics["course_titles"] == ["Course A", "Course B", "Course C"]
        
    def test_query_error_handling(self):
        """Test error handling in query processing"""
        # Make AI generator raise an exception
        def raise_error(*args, **kwargs):
            raise Exception("AI Generator failed")
            
        self.mock_ai_generator.generate_response = raise_error
        
        # Query should not crash the system
        try:
            response, sources = self.rag_system.query("Test question")
            # If no exception handling, this should raise
            assert False, "Expected exception was not raised"
        except Exception as e:
            assert "AI Generator failed" in str(e)
            
    def test_session_manager_integration(self):
        """Test integration with session manager"""
        # Test session creation when no session_id provided
        response, sources = self.rag_system.query("Test")
        
        # Should not create session (session_id is None in query method when not provided)
        # But should handle gracefully
        assert response is not None
        
    def test_source_reset_functionality(self):
        """Test that sources are properly reset after retrieval"""
        self.mock_tool_manager.last_sources = [{"text": "Source 1"}, {"text": "Source 2"}]
        
        response, sources = self.rag_system.query("Test")
        
        # Sources should be returned
        assert len(sources) == 2
        
        # Sources should be reset in tool manager
        assert len(self.mock_tool_manager.last_sources) == 0
        
    def test_multiple_queries_isolation(self):
        """Test that multiple queries don't interfere with each other"""
        # First query
        self.mock_tool_manager.last_sources = [{"text": "First query source"}]
        self.mock_ai_generator.response = "First response"
        response1, sources1 = self.rag_system.query("First question")
        
        # Second query
        self.mock_tool_manager.last_sources = [{"text": "Second query source"}]
        self.mock_ai_generator.response = "Second response"
        response2, sources2 = self.rag_system.query("Second question")
        
        # Responses should be different
        assert response1 == "First response"
        assert response2 == "Second response"
        
        # Sources should be isolated
        assert sources1[0]["text"] == "First query source"
        assert sources2[0]["text"] == "Second query source"
        
        # Should have made two separate AI calls
        assert len(self.mock_ai_generator.generate_calls) == 2
        
    def test_empty_sources_handling(self):
        """Test handling when no sources are returned"""
        self.mock_tool_manager.last_sources = []
        self.mock_ai_generator.response = "Response without sources"
        
        response, sources = self.rag_system.query("Question")
        
        assert response == "Response without sources"
        assert sources == []


def run_integration_tests():
    """Run integration tests that test actual component interactions"""
    print("Running integration tests...")
    print("=" * 50)
    
    passed = 0
    failed = 0
    failures = []
    
    # Test 1: Real config loading
    try:
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from config import config
        
        # Check if config has required attributes
        required_attrs = ['ANTHROPIC_API_KEY', 'ANTHROPIC_MODEL', 'CHUNK_SIZE', 'MAX_RESULTS']
        missing_attrs = [attr for attr in required_attrs if not hasattr(config, attr)]
        
        if missing_attrs:
            print(f"✗ Config missing attributes: {missing_attrs}")
            failed += 1
            failures.append(("Config validation", f"Missing: {missing_attrs}"))
        else:
            print("✓ Config has all required attributes")
            passed += 1
            
        # Check for potential config issues
        if config.MAX_RESULTS == 0:
            print(f"✗ Config issue: MAX_RESULTS is 0 (should be > 0)")
            failed += 1
            failures.append(("Config validation", "MAX_RESULTS is 0"))
        else:
            print(f"✓ Config MAX_RESULTS is valid: {config.MAX_RESULTS}")
            passed += 1
            
    except Exception as e:
        print(f"✗ Config loading failed: {str(e)}")
        failed += 1
        failures.append(("Config loading", str(e)))
    
    # Test 2: Check if required modules can be imported
    try:
        from vector_store import VectorStore, SearchResults
        from ai_generator import AIGenerator
        from search_tools import CourseSearchTool, ToolManager
        print("✓ All required modules import successfully")
        passed += 1
    except Exception as e:
        print(f"✗ Module import failed: {str(e)}")
        failed += 1
        failures.append(("Module imports", str(e)))
    
    # Test 3: Check if SearchResults class works correctly
    try:
        # Test empty results
        empty_results = SearchResults.empty("Test error")
        assert empty_results.error == "Test error"
        assert empty_results.is_empty()
        
        # Test normal results
        normal_results = SearchResults(["doc1", "doc2"], [{"meta": "data"}], [0.1, 0.2])
        assert not normal_results.is_empty()
        assert len(normal_results.documents) == 2
        
        print("✓ SearchResults class works correctly")
        passed += 1
    except Exception as e:
        print(f"✗ SearchResults test failed: {str(e)}")
        failed += 1
        failures.append(("SearchResults", str(e)))
    
    print(f"\nIntegration test results: {passed} passed, {failed} failed")
    return passed, failed, failures


def run_rag_system_tests():
    """Run all RAG system tests and return results"""
    print("Running RAG System tests...")
    print("=" * 50)
    
    test_instance = TestRAGSystem()
    test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
    
    passed = 0
    failed = 0
    failures = []
    
    for test_method in test_methods:
        try:
            test_instance.setup_method()
            getattr(test_instance, test_method)()
            print(f"✓ {test_method}")
            passed += 1
        except Exception as e:
            print(f"✗ {test_method}: {str(e)}")
            failed += 1
            failures.append((test_method, str(e)))
    
    print(f"\nRAG System test results: {passed} passed, {failed} failed")
    if failures:
        print("\nFailures:")
        for test_name, error in failures:
            print(f"  {test_name}: {error}")
    
    return passed, failed, failures


if __name__ == "__main__":
    rag_passed, rag_failed, rag_failures = run_rag_system_tests()
    print("\n" + "="*50)
    int_passed, int_failed, int_failures = run_integration_tests()
    
    total_passed = rag_passed + int_passed
    total_failed = rag_failed + int_failed
    
    print(f"\nOverall results: {total_passed} passed, {total_failed} failed")