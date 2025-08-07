"""
Defines the tools available to the L.U.N.A. assistant and a mapping of their names to functions.
"""
import subprocess

def send_desktop_notification(title: str, message: str):
    """Sends a desktop notification to the user."""
    try:
        subprocess.run(['notify-send', title, message], check=True)
        return f"Successfully sent notification with title '{title}'."
    except FileNotFoundError:
        return "Error: `notify-send` command not found. Is libnotify installed?"
    except Exception as e:
        return f"Error sending notification: {e}"

# A dictionary to map tool names to their functions for easy lookup
AVAILABLE_TOOLS = {
    "send_desktop_notification": send_desktop_notification
}