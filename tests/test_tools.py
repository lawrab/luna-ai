# tests/test_tools.py
from unittest.mock import patch, AsyncMock
import pytest
import pytest_asyncio # Import pytest_asyncio
import asyncio
from luna.tools import send_desktop_notification

@pytest.mark.asyncio
@patch('luna.tools.asyncio.create_subprocess_exec') # Patch the async subprocess call
async def test_send_notification_success(mock_create_subprocess_exec):
    """
    Tests that the notification function calls asyncio.create_subprocess_exec with the correct arguments
    and returns a success message asynchronously.
    """
    # Configure the mock for asyncio.create_subprocess_exec
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b'', b'') # Mock stdout, stderr
    mock_create_subprocess_exec.return_value = mock_process

    title = "Test Title"
    message = "Test Message"
    expected_command = ['notify-send', title, message]

    # 1. Call the function we are testing
    result = await send_desktop_notification(title, message) # Await the call

    # 2. Assert that our mock subprocess was called with the correct command
    mock_create_subprocess_exec.assert_called_once_with(
        *expected_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    mock_process.communicate.assert_called_once() # Ensure communicate was called

    # 3. Assert that the function returns the expected success message
    assert "Successfully sent" in result


@pytest.mark.asyncio
@patch('luna.tools.asyncio.create_subprocess_exec') # Patch the async subprocess call
async def test_send_notification_failure_gracefully(mock_create_subprocess_exec):
    """
    Tests that the notification function handles a FileNotFoundError gracefully
    if the 'notify-send' command doesn't exist asynchronously.
    """
    # 1. Configure the mock to raise an error when it's called
    mock_create_subprocess_exec.side_effect = FileNotFoundError

    # 2. Call the function and expect it to catch the error
    result = await send_desktop_notification("any title", "any message") # Await the call

    # 3. Assert that the function returned a user-friendly error message
    assert "Error" in result
    assert "`notify-send` command not found" in result