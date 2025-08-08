# luna/speech.py
"""
Handles Text-to-Speech (TTS) functionality for the L.U.N.A. assistant.
"""
# luna/speech.py
"""
Handles Text-to-Speech (TTS) functionality for the L.U.N.A. assistant.
"""
import subprocess
from . import events

def speak(text: str):
    """
    Speaks the given text aloud using the espeak-ng command-line tool.
    """
    try:
        # Use subprocess to call espeak-ng directly
        subprocess.run(['espeak-ng', text], check=True, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        events.publish("error", "`espeak-ng` command not found. Is it installed and in your PATH?")
    except subprocess.CalledProcessError as e:
        events.publish("error", f"Speech synthesis failed: {e}")
    except Exception as e:
        events.publish("error", f"An unexpected error occurred during speech synthesis: {e}")

def register_event_listeners():
    """Subscribes to events from the event bus."""
    events.subscribe("agent_response", speak)
    events.subscribe("system_shutdown", lambda: speak("Goodbye!"))
