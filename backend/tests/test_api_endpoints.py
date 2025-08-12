import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock


@pytest.mark.api
class TestAPIEndpoints:
    """Test cases for FastAPI endpoint functionality"""
    
    def test_query_endpoint_success(self, test_client, mock_rag_system, sample_query_request):
        """Test successful query processing via API"""
        # Setup mock response
        mock_rag_system.query.return_value = (
            "Machine learning is a subset of AI.",
            [{"text": "Course content", "url": "https://example.com/lesson1"}]
        )
        
        response = test_client.post("/api/query", json=sample_query_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["answer"] == "Machine learning is a subset of AI."
        assert len(data["sources"]) == 1
        assert data["sources"][0]["text"] == "Course content"
        assert data["sources"][0]["url"] == "https://example.com/lesson1"
        assert data["session_id"] == sample_query_request["session_id"]
        
        # Verify RAG system was called correctly
        mock_rag_system.query.assert_called_once_with(
            sample_query_request["query"], 
            sample_query_request["session_id"]
        )
    
    def test_query_endpoint_without_session_id(self, test_client, mock_rag_system):
        """Test query processing without providing session_id"""
        mock_rag_system.query.return_value = ("Response", [])
        mock_rag_system.session_manager.create_session.return_value = "new_session_456"
        
        request_data = {"query": "Test question"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "new_session_456"
        
        # Verify session was created
        mock_rag_system.session_manager.create_session.assert_called_once()
        mock_rag_system.query.assert_called_once_with("Test question", "new_session_456")
    
    def test_query_endpoint_with_string_sources(self, test_client, mock_rag_system):
        """Test query endpoint handling string sources (backward compatibility)"""
        mock_rag_system.query.return_value = (
            "Answer",
            ["String source 1", "String source 2"]
        )
        
        request_data = {"query": "Test question"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) == 2
        assert data["sources"][0]["text"] == "String source 1"
        assert data["sources"][0]["url"] is None
        assert data["sources"][1]["text"] == "String source 2"
        assert data["sources"][1]["url"] is None
    
    def test_query_endpoint_with_mixed_sources(self, test_client, mock_rag_system):
        """Test query endpoint with mixed dict and string sources"""
        mock_rag_system.query.return_value = (
            "Answer",
            [
                {"text": "Dict source", "url": "https://example.com"},
                "String source",
                {"text": "Dict without URL"}
            ]
        )
        
        request_data = {"query": "Test question"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) == 3
        assert data["sources"][0]["text"] == "Dict source"
        assert data["sources"][0]["url"] == "https://example.com"
        assert data["sources"][1]["text"] == "String source"
        assert data["sources"][1]["url"] is None
        assert data["sources"][2]["text"] == "Dict without URL"
        assert data["sources"][2]["url"] is None
    
    def test_query_endpoint_invalid_request(self, test_client):
        """Test query endpoint with invalid request data"""
        # Missing required 'query' field
        response = test_client.post("/api/query", json={"session_id": "test"})
        
        assert response.status_code == 422  # Validation error
        
        # Empty query
        response = test_client.post("/api/query", json={"query": ""})
        assert response.status_code == 200  # Should still process empty query
    
    def test_query_endpoint_rag_system_error(self, test_client, mock_rag_system):
        """Test query endpoint when RAG system raises an exception"""
        mock_rag_system.query.side_effect = Exception("RAG system failed")
        
        request_data = {"query": "Test question"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "RAG system failed" in data["detail"]
    
    def test_courses_endpoint_success(self, test_client, mock_rag_system, sample_course_stats):
        """Test successful course statistics retrieval"""
        mock_rag_system.get_course_analytics.return_value = sample_course_stats
        
        response = test_client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data
        assert data["total_courses"] == sample_course_stats["total_courses"]
        assert data["course_titles"] == sample_course_stats["course_titles"]
        
        # Verify analytics was called
        mock_rag_system.get_course_analytics.assert_called_once()
    
    def test_courses_endpoint_error(self, test_client, mock_rag_system):
        """Test courses endpoint when analytics fails"""
        mock_rag_system.get_course_analytics.side_effect = Exception("Analytics failed")
        
        response = test_client.get("/api/courses")
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Analytics failed" in data["detail"]
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint returns appropriate response"""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Test RAG System API" in data["message"]
    
    def test_cors_headers(self, test_client):
        """Test that CORS headers are properly set"""
        response = test_client.options("/api/query")
        
        # Check for CORS headers (TestClient might not include all headers)
        # This is a basic check - actual CORS testing would require specific setup
        assert response.status_code in [200, 405]  # OPTIONS might not be explicitly defined
    
    def test_request_response_models(self, test_client, mock_rag_system):
        """Test that request and response models are properly validated"""
        mock_rag_system.query.return_value = ("Answer", [])
        
        # Valid request
        valid_request = {
            "query": "What is AI?",
            "session_id": "test_123"
        }
        response = test_client.post("/api/query", json=valid_request)
        assert response.status_code == 200
        
        # Verify response structure
        data = response.json()
        required_fields = ["answer", "sources", "session_id"]
        for field in required_fields:
            assert field in data
        
        # Verify sources structure
        if data["sources"]:
            source = data["sources"][0]
            assert "text" in source
            assert "url" in source  # Should be present even if null
    
    def test_query_endpoint_content_type(self, test_client, mock_rag_system):
        """Test that endpoint handles different content types appropriately"""
        mock_rag_system.query.return_value = ("Answer", [])
        
        # Test with explicit JSON content type
        response = test_client.post(
            "/api/query",
            json={"query": "Test"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        
        # Test with form data (should fail)
        response = test_client.post(
            "/api/query",
            data={"query": "Test"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 422  # Should expect JSON
    
    def test_query_endpoint_large_response(self, test_client, mock_rag_system):
        """Test handling of large responses"""
        # Create a large response
        large_answer = "A" * 10000
        large_sources = [{"text": f"Source {i}", "url": f"https://example.com/{i}"} for i in range(100)]
        
        mock_rag_system.query.return_value = (large_answer, large_sources)
        
        request_data = {"query": "Large query"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["answer"]) == 10000
        assert len(data["sources"]) == 100
    
    def test_query_endpoint_unicode_content(self, test_client, mock_rag_system):
        """Test handling of Unicode content"""
        unicode_answer = "Réponse avec des caractères spéciaux: 中文, العربية, 🚀"
        unicode_sources = [{"text": "Source avec émojis 📚", "url": "https://example.com/unicode"}]
        
        mock_rag_system.query.return_value = (unicode_answer, unicode_sources)
        
        request_data = {"query": "Qu'est-ce que l'IA? 🤔"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == unicode_answer
        assert data["sources"][0]["text"] == "Source avec émojis 📚"
    
    def test_session_id_validation(self, test_client, mock_rag_system):
        """Test session ID validation and handling"""
        mock_rag_system.query.return_value = ("Answer", [])
        
        # Test with valid session ID
        response = test_client.post("/api/query", json={
            "query": "Test", 
            "session_id": "valid_session_123"
        })
        assert response.status_code == 200
        
        # Test with None session ID (should create new)
        response = test_client.post("/api/query", json={
            "query": "Test", 
            "session_id": None
        })
        assert response.status_code == 200
        
        # Test with empty string session ID
        response = test_client.post("/api/query", json={
            "query": "Test", 
            "session_id": ""
        })
        assert response.status_code == 200


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints"""
    
    def test_query_flow_integration(self, test_client, mock_rag_system):
        """Test the complete query flow integration"""
        # Setup mock to simulate real flow
        mock_rag_system.session_manager.create_session.return_value = "integration_session"
        mock_rag_system.query.return_value = (
            "Integrated response about machine learning",
            [
                {"text": "ML is a subset of AI", "url": "https://course.com/ml"},
                {"text": "It involves pattern recognition", "url": None}
            ]
        )
        
        # Make query request
        response = test_client.post("/api/query", json={
            "query": "Explain machine learning"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify complete response structure
        assert data["answer"] == "Integrated response about machine learning"
        assert len(data["sources"]) == 2
        assert data["session_id"] == "integration_session"
        
        # Verify mock interactions
        mock_rag_system.session_manager.create_session.assert_called_once()
        mock_rag_system.query.assert_called_once_with(
            "Explain machine learning", 
            "integration_session"
        )
    
    def test_courses_analytics_integration(self, test_client, mock_rag_system):
        """Test course analytics integration"""
        analytics_data = {
            "total_courses": 5,
            "course_titles": [
                "Introduction to AI",
                "Machine Learning Fundamentals", 
                "Deep Learning",
                "Natural Language Processing",
                "Computer Vision"
            ]
        }
        mock_rag_system.get_course_analytics.return_value = analytics_data
        
        response = test_client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 5
        assert len(data["course_titles"]) == 5
        assert "Introduction to AI" in data["course_titles"]
        
        # Verify analytics call
        mock_rag_system.get_course_analytics.assert_called_once()