"""
Modern L.U.N.A. main application with split terminal UI and dependency injection.
"""
import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional

from .core.config import get_config_manager
from .core.logging import configure_logging, get_logger, set_correlation_id
from .core.events import initialize_event_bus, shutdown_event_bus, get_event_bus
from .core.di import get_container, register_factory, register_service
from .core.types import CorrelationId, Event, ServiceStatus
from .services.llm import OllamaService
from .services.audio import AudioService
from .services.agent import AgentService
from .services.tts import TTSService
from .tools.desktop import DesktopNotificationTool, SystemCommandTool
from .tools.base import get_tool_registry
from .ui.terminal import get_terminal_ui
from .ui.logging_handler import setup_ui_logging


logger = get_logger(__name__)


class LunaApplication:
    """
    Main L.U.N.A. application with split terminal UI and modern architecture.
    """
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.container = get_container()
        self.event_bus = get_event_bus()
        self.running = True
        self._shutdown_event = asyncio.Event()
        self.ui = get_terminal_ui()
        
    async def initialize(self) -> None:
        """Initialize application components."""
        # Show startup banner
        self.ui.print_startup_banner()
        
        # Setup configuration and directories
        self.config_manager.ensure_directories()
        config = self.config_manager.app_config
        
        # Set up UI logging BEFORE any other logging configuration
        setup_ui_logging(config.log_level.value if hasattr(config.log_level, 'value') else config.log_level)
        
        self.ui.update_app_status("Initialising components...")
        
        logger.info("Starting L.U.N.A. initialization")
        
        # Initialize event bus
        await initialize_event_bus()
        
        # Register service factories
        register_factory(OllamaService, lambda: OllamaService(config.llm))
        register_factory(AudioService, lambda: AudioService(config.audio))
        register_factory(TTSService, lambda: TTSService(config.tts))
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
        
        # Service status updates
        self.event_bus.subscribe("service.status_changed", self._handle_service_status)
    
    async def _handle_agent_response(self, event: Event) -> None:
        """Handle agent response events."""
        response_text = event.payload.get("text", "")
        response_type = event.payload.get("type", "conversation")
        
        if response_type == "tool_result":
            tool_name = event.payload.get("tool_name", "unknown")
            success = event.payload.get("success", False)
            if success:
                self.ui.show_tool_execution(tool_name, "completed")
            else:
                self.ui.show_tool_execution(tool_name, "failed")
        else:
            self.ui.show_agent_response(response_text)
    
    async def _handle_agent_error(self, event: Event) -> None:
        """Handle agent error events."""
        error_msg = event.payload.get("error", "Unknown error")
        self.ui.show_error(error_msg)
    
    async def _handle_tool_started(self, event: Event) -> None:
        """Handle tool started events."""
        tool_name = event.tool_name or "unknown"
        self.ui.show_tool_execution(tool_name, "executing")
    
    async def _handle_tool_completed(self, event: Event) -> None:
        """Handle tool completed events."""
        tool_name = event.tool_name or "unknown"
        self.ui.show_tool_execution(tool_name, "completed")
    
    async def _handle_tool_failed(self, event: Event) -> None:
        """Handle tool failed events."""
        tool_name = event.tool_name or "unknown"
        error = event.payload.get("error", "Unknown error")
        self.ui.show_tool_execution(tool_name, "failed")
    
    async def _handle_audio_started(self, event: Event) -> None:
        """Handle audio recording started."""
        self.ui.show_listening()
    
    async def _handle_transcription(self, event: Event) -> None:
        """Handle speech transcription completed."""
        text = event.payload.get("text", "")
        self.ui.show_user_input(text)
    
    async def _handle_service_status(self, event: Event) -> None:
        """Handle service status change events."""
        service_name = event.payload.get("service_name", "unknown")
        status = event.payload.get("status", ServiceStatus.UNKNOWN)
        self.ui.update_service_status(service_name, status)
    
    async def _handle_shutdown(self, event: Event) -> None:
        """Handle shutdown events."""
        self._shutdown_event.set()
    
    @asynccontextmanager
    async def lifecycle(self):
        """Application lifecycle context manager."""
        try:
            self.ui.update_app_status("Starting services...")
            
            # Get services first to ensure they're registered
            llm_service = await self.container.get(OllamaService)
            audio_service = await self.container.get(AudioService)
            tts_service = await self.container.get(TTSService)
            agent_service = await self.container.get(AgentService)
            
            # Update service statuses
            self.ui.update_service_status("llm", llm_service.status)
            self.ui.update_service_status("audio", audio_service.status)
            self.ui.update_service_status("tts", tts_service.status)
            self.ui.update_service_status("agent", agent_service.status)
            
            # Now start all services
            async with self.container.lifecycle():
                self.ui.update_app_status("L.U.N.A. is online! 🚀")
                
                # Start audio recording if available
                if audio_service.status.value == "healthy":
                    correlation_id = CorrelationId()
                    set_correlation_id(correlation_id)
                    await audio_service.start_recording(correlation_id)
                else:
                    self.ui.show_warning("Audio not available - text input mode")
                    # Start text input task
                    asyncio.create_task(self._text_input_loop())
                
                yield
                
        finally:
            self.ui.update_app_status("Shutting down...")
            await shutdown_event_bus()
            self.ui.stop()
    
    async def _text_input_loop(self) -> None:
        """Text input loop when audio is not available."""
        self.ui.show_info("💬 Type messages (or 'exit' to quit)")
        
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
                    self.ui.show_user_input(user_input.strip())
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
        # Start the UI in the background
        ui_task = asyncio.create_task(self.ui.start())
        
        try:
            async with self.lifecycle():
                # Wait for shutdown signal
                await self._shutdown_event.wait()
        finally:
            # Stop the UI
            self.ui.stop()
            if not ui_task.done():
                ui_task.cancel()
                try:
                    await ui_task
                except asyncio.CancelledError:
                    pass
    
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
        app.ui.show_info("Shutdown requested")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        app.ui.show_error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())