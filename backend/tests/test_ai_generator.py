import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ai_generator import AIGenerator


class MockAnthropicClient:
    """Mock Anthropic client for testing"""
    
    def __init__(self):
        self.messages = Mock()
        self.create_responses = []
        self.create_call_count = 0
        
    def set_responses(self, responses):
        """Set the responses that will be returned by messages.create()"""
        self.create_responses = responses
        self.create_call_count = 0
        
    def messages_create_side_effect(self, **kwargs):
        """Side effect function for messages.create()"""
        if self.create_call_count < len(self.create_responses):
            response = self.create_responses[self.create_call_count]
            self.create_call_count += 1
            return response
        else:
            raise Exception("No more mock responses available")


class MockAnthropicResponse:
    """Mock response from Anthropic API"""
    
    def __init__(self, content, stop_reason="end_turn"):
        self.content = content
        self.stop_reason = stop_reason


class MockTextContent:
    """Mock text content block"""
    
    def __init__(self, text):
        self.text = text
        self.type = "text"


class MockToolUseContent:
    """Mock tool use content block"""
    
    def __init__(self, name, input_params, tool_id="tool_123"):
        self.name = name
        self.input = input_params
        self.id = tool_id
        self.type = "tool_use"


class MockToolManager:
    """Mock tool manager for testing"""
    
    def __init__(self):
        self.execute_tool_calls = []
        self.execute_tool_returns = {}
        
    def execute_tool(self, tool_name, **kwargs):
        """Mock execute_tool method"""
        call_info = {"tool_name": tool_name, "kwargs": kwargs}
        self.execute_tool_calls.append(call_info)
        
        # Return preset result or default
        key = f"{tool_name}_{str(kwargs)}"
        return self.execute_tool_returns.get(key, f"Mock result for {tool_name}")


class TestAIGenerator:
    """Test cases for AIGenerator class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_client = MockAnthropicClient()
        
        # Create AIGenerator with mock client
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value = self.mock_client
            self.ai_generator = AIGenerator(api_key="test_key", model="test_model")
            
        # Configure mock client
        self.mock_client.messages.create = Mock(side_effect=self.mock_client.messages_create_side_effect)
        
    def test_init_sets_correct_attributes(self):
        """Test that AIGenerator initializes with correct attributes"""
        assert self.ai_generator.model == "test_model"
        assert self.ai_generator.base_params["model"] == "test_model"
        assert self.ai_generator.base_params["temperature"] == 0
        assert self.ai_generator.base_params["max_tokens"] == 800
        
    def test_generate_response_without_tools(self):
        """Test basic response generation without tools"""
        mock_response = MockAnthropicResponse([MockTextContent("This is a test response")])
        self.mock_client.set_responses([mock_response])
        
        result = self.ai_generator.generate_response("What is machine learning?")
        
        assert result == "This is a test response"
        assert self.mock_client.messages.create.call_count == 1
        
        # Verify API call parameters
        call_args = self.mock_client.messages.create.call_args[1]
        assert call_args["model"] == "test_model"
        assert call_args["temperature"] == 0
        assert call_args["max_tokens"] == 800
        assert len(call_args["messages"]) == 1
        assert call_args["messages"][0]["content"] == "What is machine learning?"
        assert "tools" not in call_args
        
    def test_generate_response_with_conversation_history(self):
        """Test response generation with conversation history"""
        mock_response = MockAnthropicResponse([MockTextContent("Response with history")])
        self.mock_client.set_responses([mock_response])
        
        history = "Previous conversation context"
        result = self.ai_generator.generate_response(
            "Follow-up question", 
            conversation_history=history
        )
        
        assert result == "Response with history"
        
        # Verify system prompt includes history
        call_args = self.mock_client.messages.create.call_args[1]
        assert history in call_args["system"]
        
    def test_generate_response_with_tools_no_tool_use(self):
        """Test response generation with tools available but not used"""
        mock_response = MockAnthropicResponse([MockTextContent("Direct response without tools")])
        self.mock_client.set_responses([mock_response])
        
        tools = [{"name": "search_course_content", "description": "Search tool"}]
        mock_tool_manager = MockToolManager()
        
        result = self.ai_generator.generate_response(
            "General knowledge question",
            tools=tools,
            tool_manager=mock_tool_manager
        )
        
        assert result == "Direct response without tools"
        
        # Verify tools were included in API call
        call_args = self.mock_client.messages.create.call_args[1]
        assert "tools" in call_args
        assert call_args["tools"] == tools
        assert call_args["tool_choice"] == {"type": "auto"}
        
        # Verify no tool execution occurred
        assert len(mock_tool_manager.execute_tool_calls) == 0
        
    def test_generate_response_with_tool_use_single_tool(self):
        """Test response generation with single tool use"""
        # First response: tool use
        tool_use_content = MockToolUseContent(
            "search_course_content", 
            {"query": "machine learning", "course_name": "AI Basics"}
        )
        mock_tool_response = MockAnthropicResponse([tool_use_content], stop_reason="tool_use")
        
        # Second response: final answer after tool execution
        final_response = MockAnthropicResponse([MockTextContent("Based on the search results, machine learning is...")])
        
        self.mock_client.set_responses([mock_tool_response, final_response])
        
        tools = [{"name": "search_course_content", "description": "Search tool"}]
        mock_tool_manager = MockToolManager()
        mock_tool_manager.execute_tool_returns["search_course_content_{'query': 'machine learning', 'course_name': 'AI Basics'}"] = "Machine learning content from course"
        
        result = self.ai_generator.generate_response(
            "What is machine learning?",
            tools=tools,
            tool_manager=mock_tool_manager
        )
        
        assert result == "Based on the search results, machine learning is..."
        assert self.mock_client.messages.create.call_count == 2
        
        # Verify tool was executed
        assert len(mock_tool_manager.execute_tool_calls) == 1
        tool_call = mock_tool_manager.execute_tool_calls[0]
        assert tool_call["tool_name"] == "search_course_content"
        assert tool_call["kwargs"]["query"] == "machine learning"
        assert tool_call["kwargs"]["course_name"] == "AI Basics"
        
    def test_generate_response_with_multiple_tool_uses(self):
        """Test response generation with multiple tool uses in one call"""
        # First response: multiple tool uses
        tool_use_1 = MockToolUseContent("search_course_content", {"query": "python"}, "tool_1")
        tool_use_2 = MockToolUseContent("get_course_outline", {"course_name": "Python"}, "tool_2")
        mock_tool_response = MockAnthropicResponse([tool_use_1, tool_use_2], stop_reason="tool_use")
        
        # Second response: final answer
        final_response = MockAnthropicResponse([MockTextContent("Here's information about Python from multiple sources")])
        
        self.mock_client.set_responses([mock_tool_response, final_response])
        
        tools = [
            {"name": "search_course_content", "description": "Search tool"},
            {"name": "get_course_outline", "description": "Outline tool"}
        ]
        mock_tool_manager = MockToolManager()
        
        result = self.ai_generator.generate_response(
            "Tell me about Python courses",
            tools=tools,
            tool_manager=mock_tool_manager
        )
        
        assert result == "Here's information about Python from multiple sources"
        
        # Verify both tools were executed
        assert len(mock_tool_manager.execute_tool_calls) == 2
        
        tool_calls = mock_tool_manager.execute_tool_calls
        tool_names = [call["tool_name"] for call in tool_calls]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names
        
    def test_handle_tool_execution_message_structure(self):
        """Test that tool execution creates proper message structure"""
        # Create a tool use response
        tool_use_content = MockToolUseContent(
            "search_course_content", 
            {"query": "test query"},
            "tool_123"
        )
        initial_response = MockAnthropicResponse([tool_use_content], stop_reason="tool_use")
        
        final_response = MockAnthropicResponse([MockTextContent("Final answer")])
        self.mock_client.set_responses([final_response])
        
        mock_tool_manager = MockToolManager()
        mock_tool_manager.execute_tool_returns["search_course_content_{'query': 'test query'}"] = "Tool result content"
        
        # Simulate the base parameters that would be passed
        base_params = {
            "messages": [{"role": "user", "content": "Test question"}],
            "system": "System prompt",
            "model": "test_model",
            "temperature": 0,
            "max_tokens": 800
        }
        
        result = self.ai_generator._handle_tool_execution(
            initial_response, 
            base_params, 
            mock_tool_manager
        )
        
        assert result == "Final answer"
        
        # Verify the message structure in the final API call
        call_args = self.mock_client.messages.create.call_args[1]
        messages = call_args["messages"]
        
        # Should have 3 messages: original user, assistant tool use, user tool results
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        
        # Check tool result structure
        tool_results = messages[2]["content"]
        assert len(tool_results) == 1
        assert tool_results[0]["type"] == "tool_result"
        assert tool_results[0]["tool_use_id"] == "tool_123"
        assert tool_results[0]["content"] == "Tool result content"
        
    def test_tool_execution_without_tool_manager(self):
        """Test that tool use without tool manager returns direct response"""
        tool_use_content = MockToolUseContent("search_course_content", {"query": "test"})
        mock_response = MockAnthropicResponse([tool_use_content], stop_reason="tool_use")
        self.mock_client.set_responses([mock_response])
        
        result = self.ai_generator.generate_response(
            "Test question",
            tools=[{"name": "search_course_content"}],
            tool_manager=None  # No tool manager
        )
        
        # Should return empty string or handle gracefully
        assert result == ""  # Since content[0].text would fail on tool_use content
        
    def test_system_prompt_structure(self):
        """Test that system prompt is properly structured"""
        mock_response = MockAnthropicResponse([MockTextContent("Test response")])
        self.mock_client.set_responses([mock_response])
        
        self.ai_generator.generate_response("Test query")
        
        call_args = self.mock_client.messages.create.call_args[1]
        system_prompt = call_args["system"]
        
        # Verify key elements are in system prompt
        assert "search_course_content" in system_prompt
        assert "get_course_outline" in system_prompt
        assert "Tool Usage Guidelines" in system_prompt
        assert "Response Protocol" in system_prompt
        assert "Sequential tool use allowed" in system_prompt
        assert "maximum 2 rounds total" in system_prompt
        assert "Progressive information gathering" in system_prompt
        
    def test_api_parameters_consistency(self):
        """Test that API parameters are consistent between calls"""
        tool_use_content = MockToolUseContent("search_course_content", {"query": "test"})
        initial_response = MockAnthropicResponse([tool_use_content], stop_reason="tool_use")
        final_response = MockAnthropicResponse([MockTextContent("Final")])
        
        self.mock_client.set_responses([initial_response, final_response])
        
        mock_tool_manager = MockToolManager()
        
        # Use max_tool_rounds=1 to simulate legacy single-round behavior
        self.ai_generator.generate_response(
            "Test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
            max_tool_rounds=1
        )
        
        # Should have exactly 2 API calls: tool round + final response
        all_calls = self.mock_client.messages.create.call_args_list
        assert len(all_calls) == 2
        
        first_call = all_calls[0][1]
        second_call = all_calls[1][1]
        
        # Check base parameters are consistent
        assert first_call["model"] == second_call["model"]
        assert first_call["temperature"] == second_call["temperature"]
        assert first_call["max_tokens"] == second_call["max_tokens"]
        assert first_call["system"] == second_call["system"]
        
        # First call should have tools, final call should not
        assert "tools" in first_call
        assert "tools" not in second_call
    
    def test_sequential_tool_calling_two_rounds(self):
        """Test sequential tool calling with two rounds"""
        # Round 1: tool use
        tool_use_1 = MockToolUseContent("get_course_outline", {"course_name": "Python"}, "tool_1")
        round_1_response = MockAnthropicResponse([tool_use_1], stop_reason="tool_use")
        
        # Round 2: another tool use
        tool_use_2 = MockToolUseContent("search_course_content", {"query": "lesson 4"}, "tool_2")
        round_2_response = MockAnthropicResponse([tool_use_2], stop_reason="tool_use")
        
        # Final response: no tools
        final_response = MockAnthropicResponse([MockTextContent("Complete answer based on both tool results")])
        
        self.mock_client.set_responses([round_1_response, round_2_response, final_response])
        
        tools = [
            {"name": "get_course_outline", "description": "Get course outline"},
            {"name": "search_course_content", "description": "Search content"}
        ]
        mock_tool_manager = MockToolManager()
        mock_tool_manager.execute_tool_returns["get_course_outline_{'course_name': 'Python'}"] = "Python course outline with lesson 4: Advanced Topics"
        mock_tool_manager.execute_tool_returns["search_course_content_{'query': 'lesson 4'}"] = "Advanced Python topics content"
        
        result = self.ai_generator.generate_response(
            "Search for a course that discusses the same topic as lesson 4 of Python course",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_tool_rounds=2
        )
        
        assert result == "Complete answer based on both tool results"
        assert self.mock_client.messages.create.call_count == 3  # 2 tool rounds + 1 final
        
        # Verify both tools were executed
        assert len(mock_tool_manager.execute_tool_calls) == 2
        tool_names = [call["tool_name"] for call in mock_tool_manager.execute_tool_calls]
        assert "get_course_outline" in tool_names
        assert "search_course_content" in tool_names
    
    def test_sequential_tool_calling_early_termination(self):
        """Test sequential tool calling with early termination (no tools in first round)"""
        # First round: direct response (no tools)
        direct_response = MockAnthropicResponse([MockTextContent("Direct answer without tools")])
        
        self.mock_client.set_responses([direct_response])
        
        tools = [{"name": "search_course_content", "description": "Search tool"}]
        mock_tool_manager = MockToolManager()
        
        result = self.ai_generator.generate_response(
            "What is 2+2?",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_tool_rounds=2
        )
        
        assert result == "Direct answer without tools"
        assert self.mock_client.messages.create.call_count == 1  # Only one call
        assert len(mock_tool_manager.execute_tool_calls) == 0  # No tools executed
    
    def test_sequential_tool_calling_max_rounds_limit(self):
        """Test that sequential tool calling respects max_tool_rounds limit"""
        # Round 1: tool use
        tool_use_1 = MockToolUseContent("search_course_content", {"query": "test1"}, "tool_1")
        round_1_response = MockAnthropicResponse([tool_use_1], stop_reason="tool_use")
        
        # Round 2: tool use (should be last due to max_tool_rounds=2)
        tool_use_2 = MockToolUseContent("search_course_content", {"query": "test2"}, "tool_2")
        round_2_response = MockAnthropicResponse([tool_use_2], stop_reason="tool_use")
        
        # Final response after max rounds reached
        final_response = MockAnthropicResponse([MockTextContent("Final answer after 2 rounds")])
        
        self.mock_client.set_responses([round_1_response, round_2_response, final_response])
        
        tools = [{"name": "search_course_content", "description": "Search tool"}]
        mock_tool_manager = MockToolManager()
        
        result = self.ai_generator.generate_response(
            "Complex query requiring multiple searches",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_tool_rounds=2
        )
        
        assert result == "Final answer after 2 rounds"
        assert self.mock_client.messages.create.call_count == 3
        assert len(mock_tool_manager.execute_tool_calls) == 2
    
    def test_sequential_tool_calling_with_tool_failure(self):
        """Test sequential tool calling with tool execution failure"""
        # Round 1: tool use that will fail
        tool_use_1 = MockToolUseContent("search_course_content", {"query": "test"}, "tool_1")
        round_1_response = MockAnthropicResponse([tool_use_1], stop_reason="tool_use")
        
        # Should not proceed to round 2 due to tool failure
        final_response = MockAnthropicResponse([MockTextContent("Response after tool failure")])
        
        self.mock_client.set_responses([round_1_response, final_response])
        
        tools = [{"name": "search_course_content", "description": "Search tool"}]
        mock_tool_manager = MockToolManager()
        
        # Make the first tool call raise an exception
        original_execute = mock_tool_manager.execute_tool
        def failing_execute_tool(tool_name, **kwargs):
            if tool_name == "search_course_content":
                raise Exception("Database connection failed")
            return original_execute(tool_name, **kwargs)
        mock_tool_manager.execute_tool = failing_execute_tool
        
        result = self.ai_generator.generate_response(
            "Test query",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_tool_rounds=2
        )
        
        assert result == "Response after tool failure"
        # Should stop after first round due to tool failure
        assert self.mock_client.messages.create.call_count == 2
    
    def test_backward_compatibility_max_tool_rounds_default(self):
        """Test backward compatibility - max_tool_rounds defaults to 2"""
        tool_use_content = MockToolUseContent("search_course_content", {"query": "test"})
        initial_response = MockAnthropicResponse([tool_use_content], stop_reason="tool_use")
        final_response = MockAnthropicResponse([MockTextContent("Final response")])
        
        self.mock_client.set_responses([initial_response, final_response])
        
        tools = [{"name": "search_course_content", "description": "Search tool"}]
        mock_tool_manager = MockToolManager()
        
        # Call without max_tool_rounds parameter (should default to 2)
        result = self.ai_generator.generate_response(
            "Test query",
            tools=tools,
            tool_manager=mock_tool_manager
        )
        
        assert result == "Final response"
        # Should work same as before for single tool use
        assert self.mock_client.messages.create.call_count == 2
    
    def test_conversation_context_preservation_across_rounds(self):
        """Test that conversation context is preserved across tool rounds"""
        # Round 1: tool use
        tool_use_1 = MockToolUseContent("get_course_outline", {"course_name": "Python"}, "tool_1")
        round_1_response = MockAnthropicResponse([tool_use_1], stop_reason="tool_use")
        
        # Round 2: another tool use
        tool_use_2 = MockToolUseContent("search_course_content", {"query": "lesson 4"}, "tool_2")
        round_2_response = MockAnthropicResponse([tool_use_2], stop_reason="tool_use")
        
        # Final response
        final_response = MockAnthropicResponse([MockTextContent("Final response")])
        
        self.mock_client.set_responses([round_1_response, round_2_response, final_response])
        
        tools = [
            {"name": "get_course_outline", "description": "Get outline"},
            {"name": "search_course_content", "description": "Search content"}
        ]
        mock_tool_manager = MockToolManager()
        
        result = self.ai_generator.generate_response(
            "Complex query",
            conversation_history="Previous conversation context",
            tools=tools,
            tool_manager=mock_tool_manager
        )
        
        # Verify conversation history is included in all API calls
        all_calls = self.mock_client.messages.create.call_args_list
        for call in all_calls:
            system_content = call[1]["system"]
            assert "Previous conversation context" in system_content
        
        # Verify messages accumulate properly across rounds
        final_call = all_calls[-1][1]
        messages = final_call["messages"]
        
        # Should have: user query + assistant tool1 + user tool1_result + assistant tool2 + user tool2_result
        assert len(messages) >= 5
        assert messages[0]["role"] == "user"  # Original query
        assert messages[1]["role"] == "assistant"  # First tool use
        assert messages[2]["role"] == "user"  # First tool results
        assert messages[3]["role"] == "assistant"  # Second tool use
        assert messages[4]["role"] == "user"  # Second tool results


def run_ai_generator_tests():
    """Run all AIGenerator tests and return results"""
    print("Running AIGenerator tests...")
    print("=" * 50)
    
    test_instance = TestAIGenerator()
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
    run_ai_generator_tests()