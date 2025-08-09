"""
Advanced terminal interface with split panes for L.U.N.A.
"""
import asyncio
import threading
from datetime import datetime
from queue import Queue, Empty
from typing import Optional, List, Dict, Any
from collections import deque

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.padding import Padding
from rich.table import Table

from ..core.types import Event, ServiceStatus
from ..core.logging import get_logger


class LogMessage:
    """Represents a log message with timestamp and formatting."""
    
    def __init__(self, timestamp: datetime, level: str, logger_name: str, message: str):
        self.timestamp = timestamp
        self.level = level
        self.logger_name = logger_name
        self.message = message
        self.formatted = self._format_message()
    
    def _format_message(self) -> str:
        """Format the log message for display."""
        time_str = self.timestamp.strftime("%H:%M:%S")
        # Truncate logger name for cleaner display
        logger_short = self.logger_name.split('.')[-1] if '.' in self.logger_name else self.logger_name
        return f"{time_str} [{self.level:5}] {logger_short}: {self.message}"


class UserMessage:
    """Represents a user-facing interactive message."""
    
    def __init__(self, content: str, style: str = "white", emoji: str = ""):
        self.content = content
        self.style = style
        self.emoji = emoji
        self.timestamp = datetime.now()
    
    @property
    def formatted(self) -> Text:
        """Get formatted text for display."""
        text = Text()
        if self.emoji:
            text.append(f"{self.emoji} ", style=self.style)
        text.append(self.content, style=self.style)
        return text


class SplitTerminalUI:
    """
    Split terminal interface with logs on top and user messages on bottom.
    """
    
    def __init__(self, max_log_lines: int = 100, max_user_messages: int = 50):
        self.console = Console()
        self.max_log_lines = max_log_lines
        self.max_user_messages = max_user_messages
        
        # Message storage
        self.log_messages: deque = deque(maxlen=max_log_lines)
        self.user_messages: deque = deque(maxlen=max_user_messages)
        
        # Threading for live updates
        self.message_queue: Queue = Queue()
        self.running = False
        self.live: Optional[Live] = None
        
        # Application status
        self.app_status = "Initialising..."
        self.services_status: Dict[str, ServiceStatus] = {}
        
        self.logger = get_logger(__name__)
    
    def create_layout(self) -> Layout:
        """Create the split terminal layout."""
        layout = Layout()
        
        # Split into top and bottom
        layout.split_column(
            Layout(name="logs", ratio=3),     # 75% for logs
            Layout(name="interactive", ratio=1)  # 25% for user messages
        )
        
        return layout
    
    def render_logs_pane(self) -> Panel:
        """Render the logs pane."""
        if not self.log_messages:
            log_content = Text("Waiting for log messages...", style="dim white")
        else:
            log_lines = []
            for log_msg in self.log_messages:
                # Colour code by log level
                level_styles = {
                    "DEBUG": "dim white",
                    "INFO": "white", 
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold red"
                }
                style = level_styles.get(log_msg.level, "white")
                log_lines.append(Text(log_msg.formatted, style=style))
            
            log_content = Text()
            for line in log_lines[-20:]:  # Show last 20 lines
                log_content.append(line)
                log_content.append("\n")
        
        return Panel(
            log_content,
            title="🔍 L.U.N.A. Debug Logs",
            title_align="left",
            border_style="dim blue",
            padding=(0, 1)
        )
    
    def render_interactive_pane(self) -> Panel:
        """Render the interactive pane."""
        content = Text()
        
        # Add status line
        status_text = Text()
        status_text.append(f"📡 {self.app_status}", style="bold cyan")
        
        # Add service status indicators
        if self.services_status:
            status_text.append("  |  ", style="dim white")
            service_indicators = []
            for service, status in self.services_status.items():
                emoji = {
                    ServiceStatus.HEALTHY: "🟢",
                    ServiceStatus.DEGRADED: "🟡", 
                    ServiceStatus.FAILED: "🔴",
                    ServiceStatus.INITIALIZING: "🔄",
                    ServiceStatus.SHUTDOWN: "⚫"
                }.get(status, "❓")
                service_indicators.append(f"{emoji} {service.replace('-service', '')}")
            
            status_text.append(" ".join(service_indicators), style="dim white")
        
        content.append(status_text)
        content.append("\n" + "─" * 60 + "\n", style="dim blue")
        
        # Add user messages
        if not self.user_messages:
            content.append("Ready for interaction...", style="dim cyan")
        else:
            for msg in list(self.user_messages)[-10:]:  # Show last 10 messages
                content.append(msg.formatted)
                content.append("\n")
        
        return Panel(
            content,
            title="🤖 L.U.N.A. Interactive",
            title_align="left", 
            border_style="bold cyan",
            padding=(0, 1)
        )
    
    def update_layout(self, layout: Layout) -> None:
        """Update the layout with current content."""
        layout["logs"].update(self.render_logs_pane())
        layout["interactive"].update(self.render_interactive_pane())
    
    def add_log_message(self, level: str, logger_name: str, message: str) -> None:
        """Add a log message to the logs pane."""
        log_msg = LogMessage(datetime.now(), level, logger_name, message)
        self.log_messages.append(log_msg)
        
        # Queue update for live display
        if self.running:
            try:
                self.message_queue.put_nowait(('log', log_msg))
            except:
                pass  # Queue full, skip update
    
    def add_user_message(self, content: str, style: str = "white", emoji: str = "") -> None:
        """Add a user message to the interactive pane."""
        user_msg = UserMessage(content, style, emoji)
        self.user_messages.append(user_msg)
        
        # Queue update for live display
        if self.running:
            try:
                self.message_queue.put_nowait(('user', user_msg))
            except:
                pass  # Queue full, skip update
    
    def update_app_status(self, status: str) -> None:
        """Update application status."""
        self.app_status = status
        if self.running:
            try:
                self.message_queue.put_nowait(('status', status))
            except:
                pass
    
    def update_service_status(self, service_name: str, status: ServiceStatus) -> None:
        """Update service status."""
        self.services_status[service_name] = status
        if self.running:
            try:
                self.message_queue.put_nowait(('service', (service_name, status)))
            except:
                pass
    
    async def start(self) -> None:
        """Start the live terminal interface."""
        layout = self.create_layout()
        self.update_layout(layout)
        
        self.running = True
        
        with Live(layout, console=self.console, refresh_per_second=4, screen=True) as live:
            self.live = live
            
            # Update loop
            while self.running:
                try:
                    # Process queued updates
                    while True:
                        try:
                            update_type, data = self.message_queue.get_nowait()
                            self.update_layout(layout)
                        except Empty:
                            break
                    
                    await asyncio.sleep(0.25)  # 4 FPS update rate
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"Error in UI update loop: {e}")
                    break
        
        self.running = False
        self.live = None
    
    def stop(self) -> None:
        """Stop the terminal interface."""
        self.running = False
    
    def print_startup_banner(self) -> None:
        """Print the L.U.N.A. startup banner."""
        banner = Panel(
            Align.center(
                Text("🤖 L.U.N.A.\nLogical Unified Network Assistant", 
                     style="bold cyan", justify="center")
            ),
            title="Starting Up",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(banner)
        self.console.print()
    
    # Convenience methods for common user messages
    def show_listening(self) -> None:
        """Show listening for speech message."""
        self.add_user_message("Listening for speech...", "green", "🎤")
    
    def show_user_input(self, text: str) -> None:
        """Show transcribed user input."""
        self.add_user_message(f"You said: {text}", "white", "👤")
    
    def show_agent_response(self, text: str) -> None:
        """Show agent response."""
        self.add_user_message(text, "cyan", "🤖")
    
    def show_tool_execution(self, tool_name: str, status: str = "executing") -> None:
        """Show tool execution status."""
        if status == "executing":
            self.add_user_message(f"Executing {tool_name}...", "yellow", "🔄")
        elif status == "completed":
            self.add_user_message(f"{tool_name} completed", "green", "✅")
        elif status == "failed":
            self.add_user_message(f"{tool_name} failed", "red", "❌")
    
    def show_error(self, message: str) -> None:
        """Show error message."""
        self.add_user_message(f"Error: {message}", "red", "❌")
    
    def show_warning(self, message: str) -> None:
        """Show warning message."""
        self.add_user_message(f"Warning: {message}", "yellow", "⚠️")
    
    def show_info(self, message: str) -> None:
        """Show info message."""
        self.add_user_message(message, "blue", "ℹ️")


# Global UI instance
_ui_instance: Optional[SplitTerminalUI] = None


def get_terminal_ui() -> SplitTerminalUI:
    """Get the global terminal UI instance."""
    global _ui_instance
    if _ui_instance is None:
        _ui_instance = SplitTerminalUI()
    return _ui_instance