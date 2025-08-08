"""
Defines the tools available to the L.U.N.A. assistant and a mapping of their names to functions.
"""
import asyncio
import subprocess

async def send_desktop_notification(title: str, message: str):
    """Sends a desktop notification to the user asynchronously."""
    try:
        process = await asyncio.create_subprocess_exec(
            'notify-send', title, message,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_message = stderr.decode().strip() if stderr else f"Process exited with code {process.returncode}"
            return f"Error sending notification: {error_message}"
        
        return f"Successfully sent notification with title '{title}'."
    except FileNotFoundError:
        return "Error: `notify-send` command not found. Is libnotify installed?"
    except Exception as e:
        return f"Error sending notification: {e}"

# A dictionary to map tool names to their functions for easy lookup
AVAILABLE_TOOLS = {
    "send_desktop_notification": send_desktop_notification
}