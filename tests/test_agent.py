# tests/test_agent.py
"""
Tests for the agent service.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch

from luna.services.agent import AgentService
from luna.tools.desktop import DesktopNotificationTool
from luna.core.types import CorrelationId, ToolResult


@pytest.mark.asyncio
async def test_agent_service_creation():
    """
    Test basic agent service creation and properties.
    """
    # Mock LLM service
    mock_llm = AsyncMock()
    
    # Create agent service
    agent_service = AgentService(mock_llm)
    
    # Verify basic properties
    assert agent_service.name == "agent-service"
    assert agent_service.llm_service is mock_llm


@pytest.mark.asyncio
async def test_agent_processes_normal_conversation():
    """
    Test that the agent processes normal conversation correctly.
    """
    # Mock LLM service
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = "Hello! How can I help you today?"
    
    # Create agent service
    agent_service = AgentService(mock_llm)
    
    # Mock event bus to capture published events
    events_published = []
    
    async def capture_event(event):
        events_published.append(event)
    
    with patch.object(agent_service._event_bus, 'publish', side_effect=capture_event):
        # Process input
        correlation_id = CorrelationId("test-conversation")
        await agent_service.process_input("Hello", correlation_id)
        
        # Verify LLM was called
        mock_llm.generate.assert_called_once()
        
        # Verify response event was published
        assert len(events_published) == 1
        response_event = events_published[0]
        assert response_event.type == "agent.response"
        assert response_event.payload["text"] == "Hello! How can I help you today?"
        assert response_event.payload["type"] == "conversation"
        assert response_event.correlation_id == correlation_id


@pytest.mark.asyncio 
async def test_agent_handles_tool_call():
    """
    Test that the agent can process a valid tool call.
    """
    # Mock LLM service to return a tool call
    mock_llm = AsyncMock()
    tool_response = json.dumps({
        "tool_name": "send_desktop_notification",
        "tool_args": {
            "title": "Test Title",
            "message": "Test Message"
        }
    })
    mock_llm.generate.return_value = tool_response
    
    # Create agent service
    agent_service = AgentService(mock_llm)
    
    # Register a tool in the global registry
    from luna.tools.base import get_tool_registry
    registry = get_tool_registry()
    tool = DesktopNotificationTool()
    registry.register(tool)
    
    try:
        # Mock the tool execution to avoid subprocess calls
        events_published = []
        
        async def capture_event(event):
            events_published.append(event)
        
        with patch.object(agent_service._event_bus, 'publish', side_effect=capture_event):
            with patch.object(tool, 'safe_execute') as mock_execute:
                mock_execute.return_value = ToolResult(
                    success=True,
                    message="Successfully sent notification: 'Test Title'",
                    data={"title": "Test Title", "message": "Test Message"}
                )
                
                # Process input that should trigger tool call
                correlation_id = CorrelationId("test-tool-call")
                await agent_service.process_input("Send notification", correlation_id)
                
                # Verify LLM was called
                mock_llm.generate.assert_called_once()
                
                # Verify tool was executed
                mock_execute.assert_called_once()
                
                # Verify events were published (tool start, tool complete, agent response)
                assert len(events_published) >= 1
                
    finally:
        # Clean up the registry
        registry.unregister("send_desktop_notification")