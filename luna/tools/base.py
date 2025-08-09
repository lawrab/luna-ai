"""
Base tool system with type safety and extensibility.
"""
import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type

from pydantic import BaseModel, ValidationError

from ..core.types import Tool, ToolInput, ToolResult, ToolMetadata, ToolException, CorrelationId
from ..core.logging import get_logger, LoggingMixin


logger = get_logger(__name__)


class BaseTool(ABC, LoggingMixin):
    """
    Base class for all L.U.N.A. tools with validation and error handling.
    """
    
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Tool metadata for discovery and validation."""
        pass
    
    @abstractmethod
    async def execute(self, input_data: ToolInput) -> ToolResult:
        """Execute the tool with validated input."""
        pass
    
    async def safe_execute(self, input_data: dict, correlation_id: Optional[CorrelationId] = None) -> ToolResult:
        """
        Safely execute the tool with input validation and error handling.
        """
        start_time = time.time()
        
        try:
            # Validate input
            validated_input = self.metadata.input_schema(**input_data)
            
            # Execute tool
            self.logger.info(
                f"Executing tool: {self.metadata.name}",
                extra={"extra_fields": {
                    "tool_name": self.metadata.name,
                    "tool_category": self.metadata.category,
                    "correlation_id": correlation_id.value if correlation_id else None,
                }}
            )
            
            result = await self.execute(validated_input)
            
            # Add execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            result.execution_time_ms = execution_time_ms
            
            self.logger.info(
                f"Tool executed successfully: {self.metadata.name}",
                extra={"extra_fields": {
                    "tool_name": self.metadata.name,
                    "execution_time_ms": execution_time_ms,
                    "success": result.success,
                    "correlation_id": correlation_id.value if correlation_id else None,
                }}
            )
            
            return result
            
        except ValidationError as e:
            error_msg = f"Invalid input for tool {self.metadata.name}: {e}"
            self.logger.error(error_msg, extra={"extra_fields": {"validation_errors": str(e)}})
            
            return ToolResult(
                success=False,
                message=error_msg,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
            
        except ToolException as e:
            error_msg = f"Tool execution failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            
            return ToolResult(
                success=False,
                message=error_msg,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
            
        except Exception as e:
            error_msg = f"Unexpected error in tool {self.metadata.name}: {e}"
            self.logger.error(error_msg, exc_info=True)
            
            return ToolResult(
                success=False,
                message=error_msg,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def get_json_schema(self) -> dict:
        """Get JSON schema for the tool input."""
        return self.metadata.input_schema.model_json_schema()
    
    def get_description_for_llm(self) -> str:
        """Get a formatted description for LLM consumption."""
        schema = self.get_json_schema()
        
        description = f"""
Tool: {self.metadata.name}
Description: {self.metadata.description}
Category: {self.metadata.category}
Input Schema: {schema}
Example Usage:
{{
    "tool_name": "{self.metadata.name}",
    "tool_args": {self._get_example_input()}
}}
""".strip()
        
        return description
    
    def _get_example_input(self) -> dict:
        """Generate example input from schema."""
        schema = self.get_json_schema()
        properties = schema.get("properties", {})
        
        example = {}
        for field_name, field_schema in properties.items():
            field_type = field_schema.get("type", "string")
            
            if field_type == "string":
                example[field_name] = f"example_{field_name}"
            elif field_type == "integer":
                example[field_name] = 42
            elif field_type == "number":
                example[field_name] = 3.14
            elif field_type == "boolean":
                example[field_name] = True
            elif field_type == "array":
                example[field_name] = []
            else:
                example[field_name] = "example_value"
        
        return example


class ToolRegistry:
    """
    Registry for managing and discovering tools.
    """
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tools_by_category: Dict[str, List[BaseTool]] = {}
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool in the registry."""
        tool_name = tool.metadata.name
        
        if tool_name in self._tools:
            logger.warning(f"Tool {tool_name} already registered, overwriting")
        
        self._tools[tool_name] = tool
        
        # Add to category index
        category = tool.metadata.category
        if category not in self._tools_by_category:
            self._tools_by_category[category] = []
        self._tools_by_category[category].append(tool)
        
        logger.info(f"Registered tool: {tool_name} (category: {category})")
    
    def unregister(self, tool_name: str) -> bool:
        """Remove a tool from the registry."""
        if tool_name not in self._tools:
            return False
        
        tool = self._tools.pop(tool_name)
        
        # Remove from category index
        category = tool.metadata.category
        if category in self._tools_by_category:
            self._tools_by_category[category] = [
                t for t in self._tools_by_category[category] if t.metadata.name != tool_name
            ]
            if not self._tools_by_category[category]:
                del self._tools_by_category[category]
        
        logger.info(f"Unregistered tool: {tool_name}")
        return True
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(tool_name)
    
    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """Get all tools in a category."""
        return self._tools_by_category.get(category, [])
    
    def get_all_tools(self) -> List[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    def get_tool_names(self) -> List[str]:
        """Get names of all registered tools."""
        return list(self._tools.keys())
    
    def get_categories(self) -> List[str]:
        """Get all tool categories."""
        return list(self._tools_by_category.keys())
    
    async def execute_tool(
        self,
        tool_name: str,
        input_data: dict,
        correlation_id: Optional[CorrelationId] = None
    ) -> ToolResult:
        """Execute a tool by name with error handling."""
        tool = self.get_tool(tool_name)
        
        if not tool:
            return ToolResult(
                success=False,
                message=f"Tool not found: {tool_name}. Available tools: {', '.join(self.get_tool_names())}"
            )
        
        return await tool.safe_execute(input_data, correlation_id)
    
    def get_llm_tool_descriptions(self) -> str:
        """Get formatted tool descriptions for LLM system prompt."""
        if not self._tools:
            return "No tools available."
        
        descriptions = []
        for category, tools in self._tools_by_category.items():
            descriptions.append(f"\n--- {category.upper()} TOOLS ---")
            for tool in tools:
                descriptions.append(tool.get_description_for_llm())
        
        return "\n\n".join(descriptions)
    
    def validate_tool_call(self, tool_call: dict) -> tuple[bool, str]:
        """
        Validate a tool call structure.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not isinstance(tool_call, dict):
            return False, "Tool call must be a dictionary"
        
        if "tool_name" not in tool_call:
            return False, "Tool call must include 'tool_name'"
        
        tool_name = tool_call["tool_name"]
        if tool_name not in self._tools:
            available = ", ".join(self.get_tool_names())
            return False, f"Unknown tool: {tool_name}. Available tools: {available}"
        
        if "tool_args" not in tool_call:
            return False, "Tool call must include 'tool_args'"
        
        if not isinstance(tool_call["tool_args"], dict):
            return False, "'tool_args' must be a dictionary"
        
        return True, ""


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(tool: BaseTool) -> None:
    """Register a tool in the global registry."""
    get_tool_registry().register(tool)


def get_tool(tool_name: str) -> Optional[BaseTool]:
    """Get a tool from the global registry."""
    return get_tool_registry().get_tool(tool_name)