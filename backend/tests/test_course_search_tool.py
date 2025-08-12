import pytest
import sys
import os
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from search_tools import CourseSearchTool
from vector_store import SearchResults


class MockVectorStore:
    """Mock vector store for testing CourseSearchTool"""
    
    def __init__(self):
        self.search_results = None
        self.search_called_with = None
        self.lesson_link_return = None
        
    def search(self, query: str, course_name: str = None, lesson_number: int = None):
        """Mock search method that records parameters"""
        self.search_called_with = {
            'query': query,
            'course_name': course_name, 
            'lesson_number': lesson_number
        }
        return self.search_results
        
    def get_lesson_link(self, course_title: str, lesson_number: int):
        """Mock get_lesson_link method"""
        return self.lesson_link_return


class TestCourseSearchTool:
    """Test cases for CourseSearchTool.execute() method"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_store = MockVectorStore()
        self.search_tool = CourseSearchTool(self.mock_store)
        
    def test_get_tool_definition(self):
        """Test that tool definition is properly structured"""
        definition = self.search_tool.get_tool_definition()
        
        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["required"] == ["query"]
        
        # Check input schema properties
        properties = definition["input_schema"]["properties"]
        assert "query" in properties
        assert "course_name" in properties
        assert "lesson_number" in properties
        
    def test_execute_successful_search_basic(self):
        """Test successful search with basic query"""
        # Setup mock results
        self.mock_store.search_results = SearchResults(
            documents=["This is course content about machine learning"],
            metadata=[{"course_title": "AI Fundamentals", "lesson_number": 1}],
            distances=[0.1]
        )
        
        result = self.search_tool.execute("machine learning")
        
        # Verify search was called with correct parameters
        assert self.mock_store.search_called_with["query"] == "machine learning"
        assert self.mock_store.search_called_with["course_name"] is None
        assert self.mock_store.search_called_with["lesson_number"] is None
        
        # Verify result format
        assert "[AI Fundamentals - Lesson 1]" in result
        assert "This is course content about machine learning" in result
        
    def test_execute_successful_search_with_course_filter(self):
        """Test successful search with course name filter"""
        self.mock_store.search_results = SearchResults(
            documents=["Course content"],
            metadata=[{"course_title": "Python Basics", "lesson_number": 2}],
            distances=[0.2]
        )
        
        result = self.search_tool.execute("functions", course_name="Python")
        
        # Verify parameters passed correctly
        assert self.mock_store.search_called_with["query"] == "functions"
        assert self.mock_store.search_called_with["course_name"] == "Python"
        assert self.mock_store.search_called_with["lesson_number"] is None
        
        # Verify result format
        assert "[Python Basics - Lesson 2]" in result
        assert "Course content" in result
        
    def test_execute_successful_search_with_lesson_filter(self):
        """Test successful search with lesson number filter"""
        self.mock_store.search_results = SearchResults(
            documents=["Lesson specific content"],
            metadata=[{"course_title": "Data Science", "lesson_number": 3}],
            distances=[0.15]
        )
        
        result = self.search_tool.execute("analysis", lesson_number=3)
        
        # Verify parameters
        assert self.mock_store.search_called_with["query"] == "analysis"
        assert self.mock_store.search_called_with["course_name"] is None
        assert self.mock_store.search_called_with["lesson_number"] == 3
        
        assert "[Data Science - Lesson 3]" in result
        assert "Lesson specific content" in result
        
    def test_execute_successful_search_with_both_filters(self):
        """Test successful search with both course and lesson filters"""
        self.mock_store.search_results = SearchResults(
            documents=["Specific lesson content"],
            metadata=[{"course_title": "Web Development", "lesson_number": 5}],
            distances=[0.05]
        )
        
        result = self.search_tool.execute("javascript", course_name="Web", lesson_number=5)
        
        # Verify all parameters
        assert self.mock_store.search_called_with["query"] == "javascript"
        assert self.mock_store.search_called_with["course_name"] == "Web"
        assert self.mock_store.search_called_with["lesson_number"] == 5
        
        assert "[Web Development - Lesson 5]" in result
        assert "Specific lesson content" in result
        
    def test_execute_multiple_results(self):
        """Test search returning multiple results"""
        self.mock_store.search_results = SearchResults(
            documents=[
                "First piece of content",
                "Second piece of content"
            ],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2}
            ],
            distances=[0.1, 0.2]
        )
        
        result = self.search_tool.execute("test query")
        
        # Should contain both results with proper formatting
        assert "[Course A - Lesson 1]" in result
        assert "[Course B - Lesson 2]" in result
        assert "First piece of content" in result
        assert "Second piece of content" in result
        
        # Results should be separated by double newlines
        assert "\n\n" in result
        
    def test_execute_empty_results(self):
        """Test handling of empty search results"""
        self.mock_store.search_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[]
        )
        
        result = self.search_tool.execute("nonexistent topic")
        
        assert result == "No relevant content found."
        
    def test_execute_empty_results_with_course_filter(self):
        """Test empty results with course filter message"""
        self.mock_store.search_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[]
        )
        
        result = self.search_tool.execute("topic", course_name="Missing Course")
        
        assert result == "No relevant content found in course 'Missing Course'."
        
    def test_execute_empty_results_with_lesson_filter(self):
        """Test empty results with lesson filter message"""
        self.mock_store.search_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[]
        )
        
        result = self.search_tool.execute("topic", lesson_number=99)
        
        assert result == "No relevant content found in lesson 99."
        
    def test_execute_empty_results_with_both_filters(self):
        """Test empty results with both filters message"""
        self.mock_store.search_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[]
        )
        
        result = self.search_tool.execute("topic", course_name="Course", lesson_number=1)
        
        assert result == "No relevant content found in course 'Course' in lesson 1."
        
    def test_execute_search_error(self):
        """Test handling of search errors"""
        self.mock_store.search_results = SearchResults.empty("Database connection failed")
        
        result = self.search_tool.execute("any query")
        
        assert result == "Database connection failed"
        
    def test_execute_metadata_without_lesson_number(self):
        """Test handling metadata without lesson number"""
        self.mock_store.search_results = SearchResults(
            documents=["Content without lesson"],
            metadata=[{"course_title": "General Course"}],
            distances=[0.1]
        )
        
        result = self.search_tool.execute("general topic")
        
        assert "[General Course]" in result
        assert "Content without lesson" in result
        
    def test_execute_source_tracking_with_lesson_link(self):
        """Test that sources are properly tracked with lesson links"""
        self.mock_store.search_results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}],
            distances=[0.1]
        )
        self.mock_store.lesson_link_return = "https://example.com/lesson1"
        
        result = self.search_tool.execute("test")
        
        # Check that sources were tracked
        assert len(self.search_tool.last_sources) == 1
        source = self.search_tool.last_sources[0]
        assert source["text"] == "Test Course - Lesson 1"
        assert source["url"] == "https://example.com/lesson1"
        
    def test_execute_source_tracking_without_lesson_link(self):
        """Test source tracking without lesson links"""
        self.mock_store.search_results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "Test Course"}],
            distances=[0.1]
        )
        
        result = self.search_tool.execute("test")
        
        # Check that sources were tracked
        assert len(self.search_tool.last_sources) == 1
        source = self.search_tool.last_sources[0]
        assert source["text"] == "Test Course"
        assert source["url"] is None
        
    def test_execute_unknown_course_metadata(self):
        """Test handling of missing course metadata"""
        self.mock_store.search_results = SearchResults(
            documents=["Content with missing metadata"],
            metadata=[{}],  # Empty metadata
            distances=[0.1]
        )
        
        result = self.search_tool.execute("test")
        
        assert "[unknown]" in result
        assert "Content with missing metadata" in result


def run_course_search_tool_tests():
    """Run all CourseSearchTool tests and return results"""
    print("Running CourseSearchTool tests...")
    print("=" * 50)
    
    test_instance = TestCourseSearchTool()
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
    
    print(f"\nResults: {passed} passed, {failed} failed")
    if failures:
        print("\nFailures:")
        for test_name, error in failures:
            print(f"  {test_name}: {error}")
    
    return passed, failed, failures


if __name__ == "__main__":
    run_course_search_tool_tests()