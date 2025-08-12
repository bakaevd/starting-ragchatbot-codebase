from typing import Any, Dict, List, Optional

import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Available Tools:
- **search_course_content**: For questions about specific course content or detailed educational materials
- **get_course_outline**: For questions about course structure, lesson lists, or course outlines

Tool Usage Guidelines:
- **Sequential tool use allowed**: You may use tools across multiple rounds (maximum 2 rounds total)
- **Strategic tool selection**: Use the most appropriate tool for each information need
- **Progressive information gathering**: Use initial tool results to inform subsequent tool usage
- Use the **search_course_content** tool for questions about specific content within courses
- Use the **get_course_outline** tool for questions about course structure, lesson titles, or complete course outlines
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

Sequential Tool Usage Examples:
- Round 1: Get course outline to understand structure
- Round 2: Search specific lesson content based on outline information
- Round 1: Search broad topic across courses
- Round 2: Deep dive into specific course based on initial results

Course Outline Responses:
- When using get_course_outline, always include:
  - Course title
  - Course link (if available)
  - Complete lesson list with lesson numbers and titles
- Format the information clearly and comprehensively

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course-specific questions**: Use appropriate tools strategically across rounds
- **Complex queries**: Break down into multiple tool calls across rounds as needed
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the tool results" or describe your tool usage strategy

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
        max_tool_rounds: int = 2,
    ) -> str:
        """
        Generate AI response with sequential tool calling capability.
        Manages up to max_tool_rounds of tool execution.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_tool_rounds: Maximum number of tool calling rounds (default 2)

        Returns:
            Generated response as string
        """

        # Build system content efficiently
        system_content = self._build_system_content(conversation_history)

        # Initialize conversation context
        messages = [{"role": "user", "content": query}]

        # Execute tool rounds
        for round_num in range(max_tool_rounds):
            response = self._execute_single_round(messages, system_content, tools)

            if response.stop_reason != "tool_use" or not tool_manager:
                # No tools used or no tool manager - return response
                # Handle case where response content might be tool_use without tool_manager
                if response.content and hasattr(response.content[0], "text"):
                    return response.content[0].text
                else:
                    return ""  # Graceful fallback for tool_use content without tool_manager

            # Handle tool execution and update conversation
            messages = self._handle_tool_execution_round(
                response, messages, tool_manager, round_num + 1
            )

            # Check if we should continue (tools used successfully)
            if not self._should_continue_tool_rounds(
                messages, round_num + 1, max_tool_rounds
            ):
                break

        # Final call without tools to get concluding response
        return self._get_final_response(messages, system_content)

    def _build_system_content(self, conversation_history: Optional[str] = None) -> str:
        """
        Build system content efficiently - avoid string ops when possible.

        Args:
            conversation_history: Previous messages for context

        Returns:
            System content string
        """
        return (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

    def _execute_single_round(
        self, messages: List[Dict], system_content: str, tools: Optional[List]
    ):
        """
        Execute a single API round with tools available.

        Args:
            messages: Current conversation messages
            system_content: System prompt content
            tools: Available tools for this round

        Returns:
            API response from Claude
        """
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content,
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response from Claude
        return self.client.messages.create(**api_params)

    def _handle_tool_execution_round(
        self, response, messages: List[Dict], tool_manager, round_num: int
    ) -> List[Dict]:
        """
        Handle tool execution for a single round and update conversation context.
        Returns updated messages for next round.

        Args:
            response: The response containing tool use requests
            messages: Current conversation messages
            tool_manager: Manager to execute tools
            round_num: Current round number (1-based)

        Returns:
            Updated messages list for next round
        """
        # Add AI's tool use response to conversation
        messages.append({"role": "assistant", "content": response.content})

        # Execute tools and collect results
        tool_results = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )
                except Exception as e:
                    # Handle tool execution errors gracefully
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": f"Tool execution failed: {str(e)}",
                        }
                    )

        # Add tool results to conversation if any
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        return messages

    def _should_continue_tool_rounds(
        self, messages: List[Dict], current_round: int, max_rounds: int
    ) -> bool:
        """
        Determine if tool calling should continue for another round.

        Args:
            messages: Current conversation messages
            current_round: Current round number (1-based)
            max_rounds: Maximum allowed rounds

        Returns:
            True if should continue, False otherwise
        """
        # Don't exceed maximum rounds
        if current_round >= max_rounds:
            return False

        # Check if last tool execution had errors
        if len(messages) >= 2:
            last_message = messages[-1]
            if last_message and last_message.get("role") == "user":
                # Check if any tool results indicate failure
                for result in last_message.get("content", []):
                    if isinstance(result, dict) and "Tool execution failed" in str(
                        result.get("content", "")
                    ):
                        return False

        return True

    def _get_final_response(self, messages: List[Dict], system_content: str) -> str:
        """
        Get final response without tools after tool rounds complete.

        Args:
            messages: Final conversation messages
            system_content: System prompt content

        Returns:
            Final response text
        """
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content,
        }

        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text

    def _handle_tool_execution(
        self, initial_response, base_params: Dict[str, Any], tool_manager
    ):
        """
        Legacy method for backward compatibility.
        Handle execution of tool calls and get follow-up response.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()

        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})

        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )
                except Exception as e:
                    # Handle tool execution errors gracefully
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": f"Tool execution failed: {str(e)}",
                        }
                    )

        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"],
        }

        # Get final response
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text
