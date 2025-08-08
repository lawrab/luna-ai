# tests/test_agent.py
import json
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage # Import AIMessage
from langchain_core.output_parsers import StrOutputParser # Import StrOutputParser

from luna.agent import LunaAgent
from luna import events # Import events to mock publish

@pytest.mark.asyncio
async def test_agent_handles_tool_call(mocker):
    """
    Tests that the agent, when given a tool-calling response from the LLM,
    correctly calls the underlying system command asynchronously.
    """
    # Mock asyncio.create_subprocess_exec for the tool execution
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b'', b'') # Mock stdout, stderr
    mock_create_subprocess_exec = mocker.patch(
        'luna.tools.asyncio.create_subprocess_exec',
        return_value=mock_process
    )

    # Mock events.publish
    mock_publish = mocker.patch('luna.events.publish')

    tool_call_dict = {
        "tool_name": "send_desktop_notification",
        "tool_args": {
            "title": "Test from Agent",
            "message": "This is a test."
        }
    }
    
    # Create agent and test the tool execution directly
    agent = LunaAgent(llm=AsyncMock())
    
    # Call the method we are testing directly
    await agent._execute_tool(tool_call_dict)

    # Assert that events were published
    mock_publish.assert_any_call("tool_started", "send_desktop_notification")
    mock_publish.assert_any_call("tool_finished", "Successfully sent notification with title 'Test from Agent'.")

    # Assert that our mock for asyncio.create_subprocess_exec was called correctly
    expected_command = ['notify-send', 'Test from Agent', 'This is a test.']
    mock_create_subprocess_exec.assert_called_once_with(
        *expected_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    mock_process.communicate.assert_called_once()


@pytest.mark.asyncio
async def test_agent_handles_normal_conversation(mocker):
    """
    Tests that the agent returns a simple text response when no tool is called asynchronously.
    """
    # Mock events.publish
    mock_publish = mocker.patch('luna.events.publish')

    chat_response = "Hello! How can I help you today?"
    
    # Create agent and mock its chain directly
    agent = LunaAgent(llm=AsyncMock())
    agent.chain = AsyncMock()
    agent.chain.ainvoke.return_value = chat_response

    # Call the method we are testing
    await agent.process_input("Hello")

    # Assert that the chain.ainvoke was called
    agent.chain.ainvoke.assert_called_once_with({"input": "Hello"})

    # Assert that the agent_response event was published
    mock_publish.assert_called_once_with("agent_response", chat_response)