# tests/test_tools.py
from unittest.mock import patch
from luna.tools import send_desktop_notification

# The @patch decorator intercepts the call to 'subprocess.run' inside the 'luna.tools' module
# and replaces it with a mock object, which is passed into our test function.
@patch('luna.tools.subprocess.run')
def test_send_notification_success(mock_subprocess_run):
    """
    Tests that the notification function calls subprocess.run with the correct arguments
    and returns a success message.
    """
    title = "Test Title"
    message = "Test Message"
    expected_command = ['notify-send', title, message]

    # 1. Call the function we are testing
    result = send_desktop_notification(title, message)

    # 2. Assert that our mock subprocess was called with the correct command
    mock_subprocess_run.assert_called_once_with(expected_command, check=True)

    # 3. Assert that the function returns the expected success message
    assert "Successfully sent" in result


@patch('luna.tools.subprocess.run')
def test_send_notification_failure_gracefully(mock_subprocess_run):
    """
    Tests that the notification function handles a FileNotFoundError gracefully
    if the 'notify-send' command doesn't exist.
    """
    # 1. Configure the mock to raise an error when it's called
    mock_subprocess_run.side_effect = FileNotFoundError

    # 2. Call the function and expect it to catch the error
    result = send_desktop_notification("any title", "any message")

    # 3. Assert that the function returned a user-friendly error message
    assert "Error" in result
    assert "`notify-send` command not found" in result