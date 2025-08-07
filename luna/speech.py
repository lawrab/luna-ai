# luna/speech.py
"""
Handles Text-to-Speech (TTS) functionality for the L.U.N.A. assistant.
"""
import subprocess

def speak(text: str):
    """
    Speaks the given text aloud using the espeak-ng command-line tool.
    """
    try:
        # Use subprocess to call espeak-ng directly
        subprocess.run(['espeak-ng', text], check=True)
    except FileNotFoundError:
        print("Error: `espeak-ng` command not found. Is it installed and in your PATH?")
    except subprocess.CalledProcessError as e:
        print(f"Error during speech synthesis (espeak-ng exited with error): {e}")
    except Exception as e:
        print(f"An unexpected error occurred during speech synthesis: {e}")