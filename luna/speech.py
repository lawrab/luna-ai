# luna/speech.py
"""
Handles Text-to-Speech (TTS) functionality for the L.U.N.A. assistant.
"""
import asyncio
import subprocess
from . import events

async def speak(text: str):
    """
    Speaks the given text aloud using the espeak-ng command-line tool asynchronously.
    """
    try:
        # Use asyncio.create_subprocess_exec to call espeak-ng non-blockingly
        process = await asyncio.create_subprocess_exec(
            'espeak-ng', text,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await process.wait() # Wait for the command to complete
    except FileNotFoundError:
        events.publish("error", "`espeak-ng` command not found. Is it installed and in your PATH?")
    except Exception as e:
        events.publish("error", f"An unexpected error occurred during speech synthesis: {e}")

async def speak_goodbye():
    """Async wrapper for goodbye message."""
    await speak("Goodbye!")

def register_event_listeners():
    """Subscribes to events from the event bus."""
    events.subscribe("agent_response", speak)
    events.subscribe("system_shutdown", speak_goodbye)
