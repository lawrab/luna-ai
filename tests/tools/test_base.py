"""
Tests for the base tool system.
"""
import pytest
from unittest.mock import AsyncMock, patch
from pydantic import BaseModel, Field

from luna.core.types import ToolInput, ToolResult, ToolMetadata, ToolException, CorrelationId
from luna.tools.base import BaseTool, ToolRegistry


class MockToolInputSchema(ToolInput):
    """Mock input schema for testing."""
    message: str = Field(..., description="Test message")
    count: int = Field(default=1, description="Test count", ge=0)


class TestTool(BaseTool):
    """Simple test tool."""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="test_tool",
            description="A tool for testing",
            input_schema=MockToolInputSchema,
            category="test",
            tags=["test"]
        )
    
    async def execute(self, input_data: MockToolInputSchema) -> ToolResult:
        if input_data.message == "fail":
            raise ToolException("Intentional test failure")
        
        return ToolResult(
            success=True,
            message=f"Processed: {input_data.message}",
            data={"message": input_data.message, "count": input_data.count}
        )


class FailingTool(BaseTool):
    """Tool that always fails."""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="failing_tool",
            description="A tool that always fails",
            input_schema=MockToolInputSchema,
            category="test"
        )
    
    async def execute(self, input_data: MockToolInputSchema) -> ToolResult:
        raise Exception("This tool always fails")


class TestBaseTool:
    """Test the BaseTool implementation."""
    
    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Test successful tool execution."""
        tool = TestTool()
        input_data = {"message": "hello", "count": 5}
        correlation_id = CorrelationId("test-correlation")
        
        result = await tool.safe_execute(input_data, correlation_id)
        
        assert result.success is True
        assert "Processed: hello" in result.message
        assert result.data["message"] == "hello"
        assert result.data["count"] == 5
        assert result.execution_time_ms is not None
        assert result.execution_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_input_validation_error(self):
        """Test handling of input validation errors."""
        tool = TestTool()
        invalid_input = {"message": "hello", "count": -1}  # count must be >= 0
        
        result = await tool.safe_execute(invalid_input)
        
        assert result.success is False
        assert "Invalid input" in result.message
        assert result.execution_time_ms is not None
    
    @pytest.mark.asyncio
    async def test_missing_required_field(self):
        """Test handling of missing required fields."""
        tool = TestTool()
        invalid_input = {"count": 5}  # missing required 'message' field
        
        result = await tool.safe_execute(invalid_input)
        
        assert result.success is False
        assert "Invalid input" in result.message
    
    @pytest.mark.asyncio
    async def test_tool_exception_handling(self):
        """Test handling of ToolException."""
        tool = TestTool()
        input_data = {"message": "fail", "count": 1}
        
        result = await tool.safe_execute(input_data)
        
        assert result.success is False
        assert "Tool execution failed" in result.message
        assert "Intentional test failure" in result.message
    
    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(self):
        """Test handling of unexpected exceptions."""
        tool = FailingTool()
        input_data = {"message": "test", "count": 1}
        
        result = await tool.safe_execute(input_data)
        
        assert result.success is False
        assert "Unexpected error" in result.message
        assert "This tool always fails" in result.message
    
    def test_get_json_schema(self):
        """Test JSON schema generation."""
        tool = TestTool()
        schema = tool.get_json_schema()
        
        assert "properties" in schema
        assert "message" in schema["properties"]
        assert "count" in schema["properties"]
        assert schema["properties"]["message"]["type"] == "string"
        assert schema["properties"]["count"]["type"] == "integer"
    
    def test_get_description_for_llm(self):
        """Test LLM description generation."""
        tool = TestTool()
        description = tool.get_description_for_llm()
        
        assert "Tool: test_tool" in description
        assert "A tool for testing" in description
        assert "Category: test" in description
        assert "tool_name" in description
        assert "tool_args" in description


class TestToolRegistry:
    """Test the ToolRegistry implementation."""
    
    def test_register_tool(self, tool_registry):
        """Test tool registration."""
        tool = TestTool()
        tool_registry.register(tool)
        
        assert "test_tool" in tool_registry.get_tool_names()
        assert tool_registry.get_tool("test_tool") is tool
        assert len(tool_registry.get_tools_by_category("test")) == 1
    
    def test_register_duplicate_tool(self, tool_registry):
        """Test registering duplicate tool names."""
        tool1 = TestTool()
        tool2 = TestTool()
        
        tool_registry.register(tool1)
        tool_registry.register(tool2)  # Should overwrite
        
        assert tool_registry.get_tool("test_tool") is tool2
    
    def test_unregister_tool(self, tool_registry):
        """Test tool unregistration."""
        tool = TestTool()
        tool_registry.register(tool)
        
        assert tool_registry.get_tool("test_tool") is not None
        
        success = tool_registry.unregister("test_tool")
        assert success is True
        assert tool_registry.get_tool("test_tool") is None
        assert len(tool_registry.get_tools_by_category("test")) == 0
    
    def test_unregister_nonexistent_tool(self, tool_registry):
        """Test unregistering tool that doesn't exist."""
        success = tool_registry.unregister("nonexistent_tool")
        assert success is False
    
    def test_get_tools_by_category(self, tool_registry):
        """Test getting tools by category."""
        tool1 = TestTool()
        tool2 = FailingTool()
        
        tool_registry.register(tool1)
        tool_registry.register(tool2)
        
        test_tools = tool_registry.get_tools_by_category("test")
        assert len(test_tools) == 2
        
        empty_tools = tool_registry.get_tools_by_category("nonexistent")
        assert len(empty_tools) == 0
    
    def test_get_all_tools(self, tool_registry):
        """Test getting all tools."""
        tool1 = TestTool()
        tool2 = FailingTool()
        
        tool_registry.register(tool1)
        tool_registry.register(tool2)
        
        all_tools = tool_registry.get_all_tools()
        assert len(all_tools) == 2
        assert tool1 in all_tools
        assert tool2 in all_tools
    
    def test_get_categories(self, tool_registry):
        """Test getting all categories."""
        tool1 = TestTool()
        tool_registry.register(tool1)
        
        categories = tool_registry.get_categories()
        assert "test" in categories
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self, tool_registry):
        """Test successful tool execution through registry."""
        tool = TestTool()
        tool_registry.register(tool)
        
        input_data = {"message": "registry test", "count": 3}
        correlation_id = CorrelationId("registry-test")
        
        result = await tool_registry.execute_tool("test_tool", input_data, correlation_id)
        
        assert result.success is True
        assert "Processed: registry test" in result.message
    
    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self, tool_registry):
        """Test executing tool that doesn't exist."""
        result = await tool_registry.execute_tool("nonexistent_tool", {})
        
        assert result.success is False
        assert "Tool not found: nonexistent_tool" in result.message
        assert "Available tools:" in result.message
    
    def test_validate_tool_call_valid(self, tool_registry):
        """Test validation of valid tool call."""
        tool = TestTool()
        tool_registry.register(tool)
        
        tool_call = {
            "tool_name": "test_tool",
            "tool_args": {"message": "test", "count": 1}
        }
        
        is_valid, error_msg = tool_registry.validate_tool_call(tool_call)
        assert is_valid is True
        assert error_msg == ""
    
    def test_validate_tool_call_invalid_structure(self, tool_registry):
        """Test validation of invalid tool call structure."""
        # Register a test tool first for later validation tests
        tool = TestTool()
        tool_registry.register(tool)
        
        # Not a dictionary
        is_valid, error_msg = tool_registry.validate_tool_call("not a dict")
        assert is_valid is False
        assert "must be a dictionary" in error_msg
        
        # Missing tool_name
        is_valid, error_msg = tool_registry.validate_tool_call({"tool_args": {}})
        assert is_valid is False
        assert "must include 'tool_name'" in error_msg
        
        # Missing tool_args (with valid tool name)
        is_valid, error_msg = tool_registry.validate_tool_call({"tool_name": "test_tool"})
        assert is_valid is False
        assert "must include 'tool_args'" in error_msg
        
        # Invalid tool_args type (with valid tool name)
        is_valid, error_msg = tool_registry.validate_tool_call({
            "tool_name": "test_tool",
            "tool_args": "not a dict"
        })
        assert is_valid is False
        assert "'tool_args' must be a dictionary" in error_msg
    
    def test_validate_tool_call_unknown_tool(self, tool_registry):
        """Test validation of unknown tool."""
        tool_call = {
            "tool_name": "unknown_tool",
            "tool_args": {}
        }
        
        is_valid, error_msg = tool_registry.validate_tool_call(tool_call)
        assert is_valid is False
        assert "Unknown tool: unknown_tool" in error_msg
    
    def test_get_llm_tool_descriptions(self, tool_registry):
        """Test getting tool descriptions for LLM."""
        # Empty registry
        descriptions = tool_registry.get_llm_tool_descriptions()
        assert "No tools available" in descriptions
        
        # With tools
        tool = TestTool()
        tool_registry.register(tool)
        
        descriptions = tool_registry.get_llm_tool_descriptions()
        assert "TEST TOOLS" in descriptions
        assert "test_tool" in descriptions
        assert "A tool for testing" in descriptions