# tests/test_tools.py
"""
Tests for desktop notification tool integration.
"""
from unittest.mock import patch, AsyncMock
import pytest

from luna.tools.desktop import DesktopNotificationTool, NotificationInput
from luna.core.types import CorrelationId


@pytest.mark.asyncio
@patch('luna.tools.desktop.asyncio.create_subprocess_exec')
async def test_desktop_notification_success(mock_create_subprocess_exec):
    """
    Test successful desktop notification execution.
    """
    # Configure the mock process
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b'', b''))
    mock_create_subprocess_exec.return_value = mock_process

    # Create tool and input
    tool = DesktopNotificationTool()
    input_data = {
        "title": "Test Title",
        "message": "Test Message",
        "urgency": "normal"
    }
    correlation_id = CorrelationId("test-notification")

    # Execute tool
    result = await tool.safe_execute(input_data, correlation_id)

    # Verify execution
    assert result.success is True
    assert "Successfully sent notification" in result.message
    assert "Test Title" in result.message
    assert result.data["title"] == "Test Title"
    assert result.data["message"] == "Test Message"

    # Verify command was called correctly
    mock_create_subprocess_exec.assert_called_once()
    args = mock_create_subprocess_exec.call_args[1:]  # Get positional args
    called_cmd = mock_create_subprocess_exec.call_args[0]
    
    # Should include notify-send, urgency, title, and message
    assert "notify-send" in called_cmd
    assert "Test Title" in called_cmd
    assert "Test Message" in called_cmd


@pytest.mark.asyncio
@patch('luna.tools.desktop.asyncio.create_subprocess_exec')
async def test_desktop_notification_command_not_found(mock_create_subprocess_exec):
    """
    Test handling when notify-send command is not found.
    """
    # Configure mock to raise FileNotFoundError
    mock_create_subprocess_exec.side_effect = FileNotFoundError

    # Create tool and input
    tool = DesktopNotificationTool()
    input_data = {
        "title": "Test Title", 
        "message": "Test Message"
    }

    # Execute tool
    result = await tool.safe_execute(input_data)

    # Verify graceful failure
    assert result.success is False
    assert "notify-send command not found" in result.message
    assert "libnotify" in result.message


@pytest.mark.asyncio
@patch('luna.tools.desktop.asyncio.create_subprocess_exec')
async def test_desktop_notification_process_failure(mock_create_subprocess_exec):
    """
    Test handling when notify-send process fails.
    """
    # Configure mock process to fail
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate = AsyncMock(return_value=(b'', b'Permission denied'))
    mock_create_subprocess_exec.return_value = mock_process

    # Create tool and input
    tool = DesktopNotificationTool()
    input_data = {
        "title": "Test Title",
        "message": "Test Message"
    }

    # Execute tool
    result = await tool.safe_execute(input_data)

    # Verify failure handling
    assert result.success is False
    assert "Failed to send notification" in result.message
    assert "Permission denied" in result.message


def test_notification_input_validation():
    """
    Test input validation for notification tool.
    """
    # Valid input
    valid_input = NotificationInput(
        title="Test Title",
        message="Test Message",
        urgency="critical"
    )
    assert valid_input.title == "Test Title"
    assert valid_input.urgency == "critical"

    # Test urgency validation
    with pytest.raises(ValueError):
        NotificationInput(
            title="Test",
            message="Test",
            urgency="invalid"  # Should fail pattern validation
        )