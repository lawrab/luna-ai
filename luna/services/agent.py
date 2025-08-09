"""
AI Agent service with LLM integration and tool orchestration.
"""
import asyncio
import json
from typing import Dict, List, Optional, Any

from ..core.types import Service, ServiceStatus, Event, AgentEvent, ToolEvent, CorrelationId
from ..core.logging import get_logger, LoggingMixin
from ..core.events import get_event_bus
from ..core.di import Injectable, get_service
from ..tools.base import get_tool_registry
from .llm import OllamaService


logger = get_logger(__name__)


class AgentService(Injectable, LoggingMixin):
    """
    AI Agent service that processes user input and orchestrates tool usage.
    """
    
    def __init__(self, llm_service: OllamaService):
        self.llm_service = llm_service
        self._status = ServiceStatus.INITIALIZING
        self._event_bus = get_event_bus()
        self._tool_registry = get_tool_registry()
        self._conversation_history: List[Dict[str, str]] = []
        
    @property
    def name(self) -> str:
        return "agent-service"
    
    @property
    def status(self) -> ServiceStatus:
        return self._status
    
    async def start(self) -> None:
        """Start the agent service."""
        try:
            # Subscribe to user input events
            self._event_bus.subscribe("user_input", self._handle_user_input)
            
            self._status = ServiceStatus.HEALTHY
            self.logger.info("Agent service started successfully")
            
        except Exception as e:
            self._status = ServiceStatus.FAILED
            self.logger.error(f"Failed to start agent service: {e}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """Stop the agent service."""
        self._status = ServiceStatus.SHUTDOWN
        self.logger.info("Agent service stopped")
    
    async def health_check(self) -> bool:
        """Check if agent service is healthy."""
        return (
            self._status == ServiceStatus.HEALTHY and
            await self.llm_service.health_check()
        )
    
    async def _handle_user_input(self, event: Event) -> None:
        """Handle user input events."""
        if event.type != "user_input":
            return
        
        user_text = event.payload.get("text", "")
        if not user_text.strip():
            return
        
        correlation_id = event.correlation_id or CorrelationId()
        
        try:
            await self.process_input(user_text, correlation_id)
        except Exception as e:
            self.logger.error(f"Error processing user input: {e}", exc_info=True)
            await self._event_bus.publish(AgentEvent(
                type="agent.error",
                payload={"error": str(e), "user_input": user_text},
                correlation_id=correlation_id
            ))
    
    async def process_input(self, user_input: str, correlation_id: CorrelationId) -> None:
        """
        Process user input and generate response with tool usage.
        """
        self.logger.info(
            f"Processing user input",
            extra={"extra_fields": {
                "input_length": len(user_input),
                "correlation_id": correlation_id.value
            }}
        )
        
        # Add to conversation history
        self._conversation_history.append({"role": "user", "content": user_input})
        
        # Build messages for LLM
        messages = await self._build_messages()
        
        try:
            # Get response from LLM
            response = await self.llm_service.generate(
                messages=messages,
                correlation_id=correlation_id
            )
            
            # Try to parse as tool call first
            if await self._try_execute_tool_call(response, correlation_id):
                return
            
            # Regular conversation response
            self._conversation_history.append({"role": "assistant", "content": response})
            
            await self._event_bus.publish(AgentEvent(
                type="agent.response",
                payload={"text": response, "type": "conversation"},
                correlation_id=correlation_id
            ))
            
        except Exception as e:
            error_msg = f"Error generating agent response: {e}"
            self.logger.error(error_msg, exc_info=True)
            
            await self._event_bus.publish(AgentEvent(
                type="agent.error",
                payload={"error": error_msg},
                correlation_id=correlation_id
            ))
    
    async def _build_messages(self) -> List[Dict[str, str]]:
        """Build messages for LLM including system prompt and conversation history."""
        system_prompt = await self._create_system_prompt()
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add recent conversation history (keep last 10 exchanges)
        recent_history = self._conversation_history[-20:]  # 10 user + 10 assistant
        messages.extend(recent_history)
        
        return messages
    
    async def _create_system_prompt(self) -> str:
        """Create system prompt with available tools."""
        tool_descriptions = self._tool_registry.get_llm_tool_descriptions()
        
        base_prompt = f"""You are L.U.N.A., an AI assistant that helps users with various tasks.

You have access to tools that can perform actions for the user. When the user's request can be fulfilled by a tool, respond with ONLY a JSON object containing the tool call - no additional text.

AVAILABLE TOOLS:
{tool_descriptions}

TOOL USAGE RULES:
1. If the user's request can be fulfilled by a tool, respond with ONLY valid JSON:
   {{
       "tool_name": "exact_tool_name",
       "tool_args": {{
           "param1": "value1",
           "param2": "value2"
       }}
   }}

2. Do NOT include any explanatory text, introductions, or commentary with tool calls.

3. If the request is conversational or doesn't require a tool, respond normally with text.

4. Always validate that you're using the correct tool name and required parameters.

Examples of CORRECT tool responses:
User: "Remind me to take out the trash"
Assistant: {{"tool_name": "send_desktop_notification", "tool_args": {{"title": "Reminder", "message": "Take out the trash"}}}}

User: "What's the weather like?"  
Assistant: I don't have access to weather information. You could check a weather website or app for current conditions in your area.
"""
        
        return base_prompt
    
    async def _try_execute_tool_call(self, response: str, correlation_id: CorrelationId) -> bool:
        """
        Try to parse response as tool call and execute it.
        Returns True if it was a tool call, False otherwise.
        """
        try:
            # Try to parse as JSON
            tool_call = json.loads(response.strip())
            
            # Validate tool call structure
            is_valid, error_msg = self._tool_registry.validate_tool_call(tool_call)
            if not is_valid:
                self.logger.warning(f"Invalid tool call: {error_msg}")
                return False
            
            # Execute tool
            await self._execute_tool(tool_call, correlation_id)
            return True
            
        except json.JSONDecodeError:
            # Not a JSON response, treat as regular conversation
            return False
    
    async def _execute_tool(self, tool_call: dict, correlation_id: CorrelationId) -> None:
        """Execute a validated tool call."""
        tool_name = tool_call["tool_name"]
        tool_args = tool_call["tool_args"]
        
        self.logger.info(
            f"Executing tool: {tool_name}",
            extra={"extra_fields": {
                "tool_name": tool_name,
                "tool_args": tool_args,
                "correlation_id": correlation_id.value
            }}
        )
        
        # Publish tool started event
        await self._event_bus.publish(ToolEvent(
            type="tool.started",
            tool_name=tool_name,
            tool_args=tool_args,
            correlation_id=correlation_id
        ))
        
        try:
            # Execute tool
            result = await self._tool_registry.execute_tool(
                tool_name=tool_name,
                input_data=tool_args,
                correlation_id=correlation_id
            )
            
            # Add tool result to conversation history
            tool_result_msg = f"Tool '{tool_name}' executed. Result: {result.message}"
            self._conversation_history.append({"role": "assistant", "content": tool_result_msg})
            
            # Publish tool completed event
            await self._event_bus.publish(ToolEvent(
                type="tool.completed",
                tool_name=tool_name,
                payload={"result": result.dict()},
                correlation_id=correlation_id
            ))
            
            # Publish agent response
            await self._event_bus.publish(AgentEvent(
                type="agent.response",
                payload={
                    "text": result.message,
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "success": result.success
                },
                correlation_id=correlation_id
            ))
            
        except Exception as e:
            error_msg = f"Tool execution failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            
            # Publish tool failed event
            await self._event_bus.publish(ToolEvent(
                type="tool.failed",
                tool_name=tool_name,
                payload={"error": str(e)},
                correlation_id=correlation_id
            ))
            
            # Publish error response
            await self._event_bus.publish(AgentEvent(
                type="agent.error",
                payload={"error": error_msg, "tool_name": tool_name},
                correlation_id=correlation_id
            ))
    
    def clear_conversation_history(self) -> None:
        """Clear the conversation history."""
        self._conversation_history.clear()
        self.logger.info("Conversation history cleared")
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history."""
        return self._conversation_history.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            "conversation_length": len(self._conversation_history),
            "status": self._status.value,
            "tools_available": len(self._tool_registry.get_tool_names())
        }