"""Base agent class"""

from typing import Any, Dict, List, Optional
from anthropic import Anthropic
import os


class BaseAgent:
    """Base class for all agents"""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str = "claude-sonnet-4-20250514",
        api_key: Optional[str] = None,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model

        # Initialize Anthropic client
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

        # Conversation history
        self.messages: List[Dict[str, Any]] = []

    def add_message(self, role: str, content: str) -> None:
        """Add message to conversation history"""
        self.messages.append({
            "role": role,
            "content": content
        })

    def clear_history(self) -> None:
        """Clear conversation history"""
        self.messages = []

    async def send_message(
        self,
        message: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Send message to Claude and get response

        Args:
            message: User message
            tools: Available tools
            max_tokens: Maximum tokens in response

        Returns:
            Claude's response
        """
        # Add user message to history
        self.add_message("user", message)

        # Prepare request
        request_params = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": self.system_prompt,
            "messages": self.messages,
        }

        if tools:
            request_params["tools"] = tools

        # Get response
        response = self.client.messages.create(**request_params)

        # Extract assistant message
        assistant_message = ""
        tool_uses = []

        for content_block in response.content:
            if content_block.type == "text":
                assistant_message += content_block.text
            elif content_block.type == "tool_use":
                tool_uses.append({
                    "id": content_block.id,
                    "name": content_block.name,
                    "input": content_block.input,
                })

        # Add assistant response to history
        self.add_message("assistant", response.content)

        return {
            "message": assistant_message,
            "tool_uses": tool_uses,
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        }

    async def send_tool_result(
        self,
        tool_use_id: str,
        result: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Send tool execution result back to Claude

        Args:
            tool_use_id: ID of tool use from previous response
            result: Result of tool execution
            tools: Available tools
            max_tokens: Maximum tokens in response

        Returns:
            Claude's response
        """
        # Add tool result to messages
        self.messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": result,
            }]
        })

        # Get next response
        request_params = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": self.system_prompt,
            "messages": self.messages,
        }

        if tools:
            request_params["tools"] = tools

        response = self.client.messages.create(**request_params)

        # Extract response
        assistant_message = ""
        tool_uses = []

        for content_block in response.content:
            if content_block.type == "text":
                assistant_message += content_block.text
            elif content_block.type == "tool_use":
                tool_uses.append({
                    "id": content_block.id,
                    "name": content_block.name,
                    "input": content_block.input,
                })

        # Add to history
        self.add_message("assistant", response.content)

        return {
            "message": assistant_message,
            "tool_uses": tool_uses,
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        }
