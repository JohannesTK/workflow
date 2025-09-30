"""Base tool classes and protocols"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ToolResult(BaseModel):
    """Result from tool execution"""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    duration: Optional[float] = None


class Tool(ABC):
    """Base class for all tools"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given parameters"""
        pass

    def to_anthropic_tool(self) -> Dict[str, Any]:
        """Convert to Anthropic tool format"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.get_input_schema()
        }

    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        """Get JSON schema for tool inputs"""
        pass
