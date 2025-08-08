# luna/main.py
"""
The main entry point for running the L.U.N.A. assistant.
"""
import ollama
from . import config, events, speech, listen, ui
from .agent import LunaAgent
from langchain_ollama import ChatOllama

class App:
    def __init__(self):
        self.ui = ui.ConsoleUI()
        self.agent = None
        self.running = True
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

    def start(self):
        """Initializes and starts the main application loop."""
        self.ui.display_status("Initializing L.U.N.A. - Logical Unified Network Assistant...")

        if not self._is_ollama_running():
            self.ui.display_error("Ollama service is not running. Please start it and try again.")
            return

        self.ui.display_status(f"Using model: {config.LLM_MODEL}")
        llm = ChatOllama(model=config.LLM_MODEL)
        self.agent = LunaAgent(llm)
        
        speech.register_event_listeners()

        self.ui.display_status("L.U.N.A. is online. Listening...")
        self.main_loop()

    def main_loop(self):
        """The main event loop where the application listens for input."""
        while self.running:
            listen.listen_and_transcribe()

    def handle_input(self, user_input: str):
        """Handles user input from the listener."""
        if not user_input.strip(): # Ignore empty input
            return

        if user_input.lower().strip() == 'exit':
            self.stop()
        else:
            self.agent.process_input(user_input)

    def stop(self, *args):
        """Stops the application."""
        if self.running:
            self.running = False
            events.publish("system_shutdown")

    def _is_ollama_running(self):
        """Checks if the Ollama service is available."""
        try:
            ollama.list()
            return True
        except Exception:
            return False

def main():
    app = App()
    try:
        app.start()
    except KeyboardInterrupt:
        app.stop()
    except Exception as e:
        app.ui.display_error(f"An unexpected critical error occurred: {e}")

if __name__ == "__main__":
    main()
