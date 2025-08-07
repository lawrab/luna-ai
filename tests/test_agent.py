# tests/test_agent.py
import json
from unittest.mock import MagicMock, patch
from luna.agent import LunaAgent

# CORRECTED: We now patch the actual external dependency, 'subprocess.run',
# at the location where it is used ('luna.tools').
@patch('luna.tools.subprocess.run')
def test_agent_handles_tool_call(mock_subprocess_run):
    """
    Tests that the agent, when given a tool-calling response from the LLM,
    correctly calls the underlying system command.
    """
    # 1. Prepare the mock LLM and its fake response
    mock_llm = MagicMock()
    tool_call_json = json.dumps({
        "tool_name": "send_desktop_notification",
        "tool_args": {
            "title": "Test from Agent",
            "message": "This is a test."
        }
    })

    # 2. Create the agent instance and mock its internal chain
    agent = LunaAgent(llm=mock_llm)
    agent.chain = MagicMock()
    agent.chain.invoke.return_value = tool_call_json

    # 3. Call the method we are testing
    agent.process_input("send a test notification")

    # 4. Assert that our mock for subprocess.run was called correctly
    expected_command = ['notify-send', 'Test from Agent', 'This is a test.']
    mock_subprocess_run.assert_called_once_with(expected_command, check=True)


def test_agent_handles_normal_conversation():
    """
    Tests that the agent returns a simple text response when no tool is called.
    """
    mock_llm = MagicMock()
    chat_response = "Hello! How can I help you today?"

    agent = LunaAgent(llm=mock_llm)
    agent.chain = MagicMock()
    agent.chain.invoke.return_value = chat_response

    result = agent.process_input("Hello")

    assert result == chat_response