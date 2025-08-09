"""
Text-to-Speech service with proper integration into L.U.N.A.'s event system.
"""
import asyncio
import shutil
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from ..core.types import ServiceStatus, Event, CorrelationId, TTSConfig
from ..core.logging import get_logger, LoggingMixin
from ..core.events import get_event_bus
from ..core.di import Injectable


logger = get_logger(__name__)


# TTSConfig is now imported from types


class TTSEngine(Enum):
    """Available TTS engines."""
    ESPEAK_NG = "espeak-ng"
    ESPEAK = "espeak"


class TTSService(Injectable, LoggingMixin):
    """
    Text-to-Speech service using espeak-ng.
    
    Subscribes to agent responses and converts them to speech.
    """
    
    def __init__(self, config: TTSConfig):
        self.config = config
        self._status = ServiceStatus.INITIALIZING
        self._event_bus = get_event_bus()
        self._engine_available = False
        
    @property
    def name(self) -> str:
        return "tts-service"
    
    @property
    def status(self) -> ServiceStatus:
        return self._status
    
    async def start(self) -> None:
        """Start the TTS service."""
        try:
            if not self.config.enabled:
                self._status = ServiceStatus.DEGRADED
                self.logger.info("TTS service disabled by configuration")
                return
            
            # Check if TTS engine is available
            if not await self._check_engine_availability():
                self._status = ServiceStatus.DEGRADED
                self.logger.warning(f"TTS engine '{self.config.engine}' not available")
                return
            
            self._engine_available = True
            
            # Subscribe to agent response events
            self._event_bus.subscribe("agent.response", self._handle_agent_response)
            
            self._status = ServiceStatus.HEALTHY
            self.logger.info(f"TTS service started successfully with {self.config.engine}")
            
        except Exception as e:
            self._status = ServiceStatus.FAILED
            self.logger.error(f"Failed to start TTS service: {e}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """Stop the TTS service."""
        self._status = ServiceStatus.SHUTDOWN
        self.logger.info("TTS service stopped")
    
    async def health_check(self) -> bool:
        """Check if TTS service is healthy."""
        return self._engine_available and await self._check_engine_availability()
    
    async def speak(self, text: str, correlation_id: Optional[CorrelationId] = None) -> None:
        """Speak the given text using the configured TTS engine."""
        if not self._engine_available or self._status != ServiceStatus.HEALTHY:
            self.logger.warning("TTS service not available, skipping speech")
            return
        
        if not text or not text.strip():
            return
        
        try:
            # Clean the text for better speech
            clean_text = self._clean_text_for_speech(text)
            
            self.logger.info(f"Speaking: '{clean_text[:50]}{'...' if len(clean_text) > 50 else ''}'")
            
            # Build espeak-ng command with configuration
            cmd = [
                self.config.engine,
                "-v", self.config.voice,
                "-s", str(self.config.speed),
                "-p", str(self.config.pitch),
                "-a", str(self.config.volume),
                clean_text
            ]
            
            # Execute TTS command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                self.logger.error(f"TTS command failed: {error_msg}")
            else:
                self.logger.debug("TTS speech completed successfully")
                
        except Exception as e:
            self.logger.error(f"Error during text-to-speech: {e}", exc_info=True)
    
    async def _handle_agent_response(self, event: Event) -> None:
        """Handle agent response events and convert to speech."""
        try:
            response_text = event.payload.get("text", "")
            response_type = event.payload.get("type", "conversation")
            
            # Only speak conversational responses, not tool results
            if response_type == "conversation" and response_text:
                await self.speak(response_text, event.correlation_id)
            
        except Exception as e:
            self.logger.error(f"Error handling agent response for TTS: {e}", exc_info=True)
    
    async def _check_engine_availability(self) -> bool:
        """Check if the TTS engine is available."""
        try:
            # Check if command exists
            engine_path = shutil.which(self.config.engine)
            if not engine_path:
                self.logger.warning(f"TTS engine '{self.config.engine}' not found in PATH")
                return False
            
            # Test the engine with a simple command
            process = await asyncio.create_subprocess_exec(
                self.config.engine, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await asyncio.wait_for(process.communicate(), timeout=5.0)
            return process.returncode == 0
            
        except Exception as e:
            self.logger.warning(f"TTS engine test failed: {e}")
            return False
    
    def _clean_text_for_speech(self, text: str) -> str:
        """Clean text to make it more suitable for speech synthesis."""
        # Remove or replace problematic characters
        text = text.strip()
        
        # Replace some common patterns that don't speak well
        replacements = {
            "L.U.N.A.": "Luna",
            "AI": "A I",
            "API": "A P I",
            "HTTP": "H T T P",
            "JSON": "J son",
            "URL": "U R L",
            "CLI": "C L I",
            "&": "and",
            "@": "at",
            "#": "hash",
            "%": "percent",
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Limit length to prevent very long speech
        if len(text) > 500:
            text = text[:497] + "..."
        
        return text