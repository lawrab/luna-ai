"""
Modern L.U.N.A. main application with dependency injection and proper lifecycle management.
"""
import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .core.config import get_config_manager
from .core.logging import configure_logging, get_logger, set_correlation_id
from .core.events import initialize_event_bus, shutdown_event_bus, get_event_bus
from .core.di import get_container, register_factory, register_service
from .core.types import CorrelationId, Event
from .services.llm import OllamaService
from .services.audio import AudioService
from .services.agent import AgentService
from .tools.desktop import DesktopNotificationTool, SystemCommandTool
from .tools.base import get_tool_registry


logger = get_logger(__name__)
console = Console()


class LunaApplication:
    """
    Main L.U.N.A. application with modern architecture.
    """
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.container = get_container()
        self.event_bus = get_event_bus()
        self.running = True
        self._shutdown_event = asyncio.Event()
        
    async def initialize(self) -> None:
        """Initialize application components."""
        console.print(Panel(
            Text("🤖 L.U.N.A. - Logical Unified Network Assistant", style="bold blue"),
            title="Initializing",
            border_style="blue"
        ))
        
        # Setup configuration and directories
        self.config_manager.ensure_directories()
        config = self.config_manager.app_config
        
        # Configure logging
        configure_logging(
            level=config.log_level,
            structured=not config.debug,
            log_file=str(self.config_manager.get_log_file_path()) if not config.debug else None
        )
        
        logger.info("Starting L.U.N.A. initialization")
        
        # Initialize event bus
        await initialize_event_bus()
        
        # Register service factories
        register_factory(OllamaService, lambda: OllamaService(config.llm))
        register_factory(AudioService, lambda: AudioService(config.audio))
        register_factory(AgentService, lambda agent_service_factory: agent_service_factory())
        
        # Custom factory for AgentService that resolves LLM dependency
        async def agent_service_factory():
            llm_service = await self.container.get(OllamaService)
            return AgentService(llm_service)
        
        register_factory(AgentService, agent_service_factory)
        
        # Register tools
        tool_registry = get_tool_registry()
        tool_registry.register(DesktopNotificationTool())
        tool_registry.register(SystemCommandTool())
        
        # Setup event handlers
        self._setup_event_handlers()
        
        logger.info("L.U.N.A. initialization completed")
    
    def _setup_event_handlers(self) -> None:
        """Setup global event handlers."""
        self.event_bus.subscribe("agent.response", self._handle_agent_response)
        self.event_bus.subscribe("agent.error", self._handle_agent_error)
        self.event_bus.subscribe("tool.started", self._handle_tool_started)
        self.event_bus.subscribe("tool.completed", self._handle_tool_completed)
        self.event_bus.subscribe("tool.failed", self._handle_tool_failed)
        self.event_bus.subscribe("audio.recording_started", self._handle_audio_started)
        self.event_bus.subscribe("audio.transcription_completed", self._handle_transcription)
        self.event_bus.subscribe("system.shutdown", self._handle_shutdown)
    
    async def _handle_agent_response(self, event: Event) -> None:
        """Handle agent response events."""
        response_text = event.payload.get("text", "")
        response_type = event.payload.get("type", "conversation")
        
        if response_type == "tool_result":
            tool_name = event.payload.get("tool_name", "unknown")
            success = event.payload.get("success", False)
            style = "green" if success else "red"
            console.print(f"🔧 [{tool_name}] {response_text}", style=style)
        else:
            console.print(f"🤖 {response_text}", style="cyan")
    
    async def _handle_agent_error(self, event: Event) -> None:
        """Handle agent error events."""
        error_msg = event.payload.get("error", "Unknown error")
        console.print(f"❌ Error: {error_msg}", style="red")
    
    async def _handle_tool_started(self, event: Event) -> None:
        """Handle tool started events."""
        tool_name = event.tool_name or "unknown"
        console.print(f"🔄 Executing {tool_name}...", style="yellow")
    
    async def _handle_tool_completed(self, event: Event) -> None:
        """Handle tool completed events."""
        tool_name = event.tool_name or "unknown"
        console.print(f"✅ {tool_name} completed", style="green")
    
    async def _handle_tool_failed(self, event: Event) -> None:
        """Handle tool failed events."""
        tool_name = event.tool_name or "unknown"
        error = event.payload.get("error", "Unknown error")
        console.print(f"❌ {tool_name} failed: {error}", style="red")
    
    async def _handle_audio_started(self, event: Event) -> None:
        """Handle audio recording started."""
        console.print("🎤 Listening for speech...", style="green")
    
    async def _handle_transcription(self, event: Event) -> None:
        """Handle speech transcription completed."""
        text = event.payload.get("text", "")
        console.print(f"👤 You said: {text}", style="white")
    
    async def _handle_shutdown(self, event: Event) -> None:
        """Handle shutdown events."""
        self._shutdown_event.set()
    
    @asynccontextmanager
    async def lifecycle(self):
        """Application lifecycle context manager."""
        try:
            # Get services first to ensure they're registered
            llm_service = await self.container.get(OllamaService)
            audio_service = await self.container.get(AudioService)
            agent_service = await self.container.get(AgentService)
            
            # Now start all services
            async with self.container.lifecycle():
                
                console.print("🚀 L.U.N.A. is online!", style="bold green")
                
                # Start audio recording if available
                if audio_service.status.value == "healthy":
                    correlation_id = CorrelationId()
                    set_correlation_id(correlation_id)
                    await audio_service.start_recording(correlation_id)
                else:
                    console.print("⚠️  Audio not available - text input mode", style="yellow")
                    # Start text input task
                    asyncio.create_task(self._text_input_loop())
                
                yield
                
        finally:
            await shutdown_event_bus()
            console.print("👋 L.U.N.A. shutdown complete", style="blue")
    
    async def _text_input_loop(self) -> None:
        """Text input loop when audio is not available."""
        console.print("💬 Type messages (or 'exit' to quit):", style="cyan")
        
        while self.running and not self._shutdown_event.is_set():
            try:
                # Get user input
                user_input = await asyncio.to_thread(
                    input, 
                    "You: "
                )
                
                if user_input.strip().lower() in ["exit", "quit", "bye"]:
                    break
                
                if user_input.strip():
                    correlation_id = CorrelationId()
                    await self.event_bus.publish(Event(
                        type="user_input",
                        payload={"text": user_input.strip(), "source": "text"},
                        correlation_id=correlation_id
                    ))
                
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                logger.error(f"Error in text input loop: {e}")
                break
        
        # Trigger shutdown
        await self.event_bus.publish(Event(type="system.shutdown"))
    
    async def run(self) -> None:
        """Run the main application."""
        async with self.lifecycle():
            # Wait for shutdown signal
            await self._shutdown_event.wait()
    
    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.running = False
            # Create task to publish shutdown event
            asyncio.create_task(self.event_bus.publish(Event(type="system.shutdown")))
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main() -> None:
    """Main entry point."""
    app = LunaApplication()
    app.setup_signal_handlers()
    
    try:
        await app.initialize()
        await app.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        console.print(f"💥 Fatal error: {e}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())