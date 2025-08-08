# luna/main.py
"""
The main entry point for running the L.U.N.A. assistant.
"""
import asyncio
import ollama
from . import config, events, speech, ui
from .agent import LunaAgent
from .listen import AudioListener # Import the new AudioListener
from langchain_ollama import ChatOllama

class App:
    def __init__(self):
        self.ui = ui.ConsoleUI()
        self.agent = None
        self.running = True
        self.audio_listener = AudioListener() # Instantiate AudioListener
        self._setup_event_listeners()

    def _setup_event_listeners(self):
        """Connects methods to events from the event bus."""
        events.subscribe("user_input", self.handle_input)
        events.subscribe("agent_response", self.ui.display_message)
        events.subscribe("error", self.ui.display_error)
        events.subscribe("status_update", self.ui.display_status)
        events.subscribe("tool_started", self.ui.display_tool_start)
        events.subscribe("tool_finished", lambda result: self.ui.display_message(f"Tool finished: {result}", style="yellow"))
        events.subscribe("system_shutdown", self.stop)

    async def start(self):
        """Initializes and starts the main application loop."""
        self.ui.display_status("Initializing L.U.N.A. - Logical Unified Network Assistant...")

        if not await self._is_ollama_running():
            self.ui.display_error("Ollama service is not running. Please start it and try again.")
            return

        self.ui.display_status(f"Using model: {config.LLM_MODEL}")
        llm = ChatOllama(model=config.LLM_MODEL)
        self.agent = LunaAgent(llm)
        
        speech.register_event_listeners()
        # Start the audio listener as an asyncio task
        self.audio_listener_task = asyncio.create_task(self.audio_listener.start_listening())

        self.ui.display_status("L.U.N.A. is online. Listening...")
        
        # Check if audio is available, if not provide text input fallback
        from .listen import AUDIO_DEPENDENCIES_AVAILABLE
        if not AUDIO_DEPENDENCIES_AVAILABLE:
            self.ui.display_status("Audio input not available. You can type 'exit' to quit.")
            asyncio.create_task(self._text_input_loop())
        # The main event loop is now managed by asyncio.run()
        
    async def _text_input_loop(self):
        """Fallback text input loop when audio is not available."""
        while self.running:
            try:
                # Use asyncio.to_thread to avoid blocking the event loop
                user_input = await asyncio.to_thread(input, "You: ")
                if user_input.strip():
                    events.publish("user_input", user_input.strip())
                await asyncio.sleep(0.1)  # Small delay to prevent busy loop
            except (EOFError, KeyboardInterrupt):
                await self.stop()
                break
            except Exception as e:
                events.publish("error", f"Text input error: {e}")
                break

    async def handle_input(self, user_input: str):
        """Handles user input from the listener."""
        if not user_input.strip(): # Ignore empty input
            return

        if user_input.lower().strip() == 'exit':
            await self.stop()
        else:
            await self.agent.process_input(user_input)

    async def stop(self, *args):
        """Stops the application."""
        if self.running:
            self.running = False
            # Stop the audio listener task
            if self.audio_listener_task:
                self.audio_listener_task.cancel()
                try:
                    await self.audio_listener_task
                except asyncio.CancelledError:
                    pass # Task was cancelled as expected
            await self.audio_listener.stop()
            events.publish("system_shutdown")

    async def _is_ollama_running(self):
        """Checks if the Ollama service is available."""
        try:
            await asyncio.to_thread(ollama.list)
            return True
        except Exception:
            return False

async def main():
    app = App()
    try:
        await app.start()
        # Keep the main task running until a shutdown event
        await events.wait_for_event("system_shutdown")
    except KeyboardInterrupt:
        await app.stop()
    except Exception as e:
        app.ui.display_error(f"An unexpected critical error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
