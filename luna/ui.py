# luna/ui.py
"""
Handles all user interface rendering for the console.
"""
from rich.console import Console

class ConsoleUI:
    def __init__(self):
        self._console = Console()

    def display_message(self, message: str, style: str = "cyan"):
        """Displays a standard message to the user."""
        self._console.print(f"[bold {style}]L.U.N.A:[/] {message}")

    def display_user_input(self, text: str):
        """Displays the transcribed user input."""
        # Using a simple print here as rich handles the carriage return poorly
        print(f"\rYou: {text}", flush=True)

    def display_error(self, message: str):
        """Displays an error message."""
        self._console.print(f"[bold red]ERROR:[/] {message}")

    def display_warning(self, message: str):
        """Displays a warning message."""
        self._console.print(f"[bold yellow]WARNING:[/] {message}")

    def display_status(self, message: str):
        """Displays a status update, like 'Listening...' or 'Transcribing...'"""
        self._console.print(f"[cyan]{message}[/cyan]")

    def display_tool_start(self, tool_name: str):
        """Informs the user that a tool is being executed."""
        self._console.print(f"[bold yellow]L.U.N.A:[/] Okay, running the `{tool_name}` tool...")

