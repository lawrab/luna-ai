"""
Audio service with proper resource management and error handling.
"""
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator
import tempfile
from pathlib import Path

try:
    import pyaudio
    import numpy as np
    import whisper
    AUDIO_DEPENDENCIES_AVAILABLE = True
except (ImportError, OSError) as e:
    AUDIO_DEPENDENCIES_AVAILABLE = False
    AUDIO_IMPORT_ERROR = str(e)

from ..core.types import AudioProvider, AudioConfig, ServiceStatus, AudioException, Event, AudioEvent, CorrelationId
from ..core.logging import get_logger, LoggingMixin
from ..core.events import get_event_bus
from ..core.di import Injectable


logger = get_logger(__name__)


class AudioResource:
    """RAII wrapper for audio resources."""
    
    def __init__(self, config: AudioConfig):
        self.config = config
        self.pyaudio_instance: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        self.whisper_model: Optional[Any] = None
    
    async def __aenter__(self):
        if not AUDIO_DEPENDENCIES_AVAILABLE:
            raise AudioException(f"Audio dependencies not available: {AUDIO_IMPORT_ERROR}")
        
        # Initialize PyAudio
        self.pyaudio_instance = pyaudio.PyAudio()
        
        # Load Whisper model
        self.whisper_model = await asyncio.to_thread(
            whisper.load_model, 
            self.config.whisper_model
        )
        
        # Open audio stream
        self.stream = await asyncio.to_thread(
            self.pyaudio_instance.open,
            format=pyaudio.paInt16,
            channels=self.config.channels,
            rate=self.config.sample_rate,
            input=True,
            frames_per_buffer=self.config.chunk_size,
            input_device_index=self.config.input_device_index
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Stop and close stream
        if self.stream:
            try:
                await asyncio.to_thread(self.stream.stop_stream)
                await asyncio.to_thread(self.stream.close)
            except Exception as e:
                logger.warning(f"Error closing audio stream: {e}")
        
        # Terminate PyAudio
        if self.pyaudio_instance:
            try:
                await asyncio.to_thread(self.pyaudio_instance.terminate)
            except Exception as e:
                logger.warning(f"Error terminating PyAudio: {e}")
    
    async def read_chunk(self, chunk_size: int) -> bytes:
        """Read a chunk of audio data."""
        if not self.stream:
            raise AudioException("Audio stream not initialized")
        
        return await asyncio.to_thread(
            self.stream.read,
            chunk_size,
            exception_on_overflow=False
        )
    
    async def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcribe audio data to text."""
        if not self.whisper_model:
            raise AudioException("Whisper model not loaded")
        
        result = await asyncio.to_thread(
            self.whisper_model.transcribe,
            audio_data,
            fp16=False
        )
        
        return result["text"].strip()


class AudioService(Injectable, LoggingMixin):
    """
    Production-ready audio service with proper resource management.
    """
    
    def __init__(self, config: AudioConfig):
        self.config = config
        self._status = ServiceStatus.INITIALIZING
        self._recording_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._event_bus = get_event_bus()
        
    @property
    def name(self) -> str:
        return "audio-service"
    
    @property
    def status(self) -> ServiceStatus:
        return self._status
    
    async def start(self) -> None:
        """Start the audio service."""
        if not AUDIO_DEPENDENCIES_AVAILABLE:
            self._status = ServiceStatus.DEGRADED
            self.logger.warning(f"Audio service degraded: {AUDIO_IMPORT_ERROR}")
            await self._event_bus.publish(AudioEvent(
                type="audio.status_changed",
                payload={"status": "degraded", "reason": "dependencies_unavailable"}
            ))
            return
        
        try:
            self._status = ServiceStatus.HEALTHY
            self.logger.info("Audio service started successfully")
            
            await self._event_bus.publish(AudioEvent(
                type="audio.status_changed",
                payload={"status": "healthy"}
            ))
            
        except Exception as e:
            self._status = ServiceStatus.FAILED
            self.logger.error(f"Failed to start audio service: {e}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """Stop the audio service."""
        self._stop_event.set()
        
        if self._recording_task and not self._recording_task.done():
            self._recording_task.cancel()
            try:
                await self._recording_task
            except asyncio.CancelledError:
                pass
        
        self._status = ServiceStatus.SHUTDOWN
        self.logger.info("Audio service stopped")
    
    async def health_check(self) -> bool:
        """Check if audio service is healthy."""
        if not AUDIO_DEPENDENCIES_AVAILABLE:
            return False
        
        try:
            # Quick test of PyAudio availability
            p = pyaudio.PyAudio()
            p.terminate()
            return True
        except Exception:
            return False
    
    async def start_recording(self, correlation_id: Optional[CorrelationId] = None) -> None:
        """Start continuous audio recording and transcription."""
        if self._status != ServiceStatus.HEALTHY:
            raise AudioException("Audio service not healthy")
        
        if self._recording_task and not self._recording_task.done():
            self.logger.warning("Recording already in progress")
            return
        
        self._stop_event.clear()
        self._recording_task = asyncio.create_task(
            self._recording_loop(correlation_id),
            name="audio-recording"
        )
        
        self.logger.info("Started audio recording")
        await self._event_bus.publish(AudioEvent(
            type="audio.recording_started",
            correlation_id=correlation_id
        ))
    
    async def stop_recording(self) -> None:
        """Stop audio recording."""
        if self._recording_task and not self._recording_task.done():
            self._stop_event.set()
            try:
                await self._recording_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Stopped audio recording")
        await self._event_bus.publish(AudioEvent(
            type="audio.recording_stopped"
        ))
    
    async def transcribe(self, audio_data: bytes, correlation_id: Optional[CorrelationId] = None) -> str:
        """Transcribe audio data to text."""
        if self._status != ServiceStatus.HEALTHY:
            raise AudioException("Audio service not healthy")
        
        try:
            # Convert bytes to numpy array
            audio_np = np.frombuffer(audio_data, dtype=np.int16).flatten().astype(np.float32) / 32768.0
            
            # Load model and transcribe
            model = await asyncio.to_thread(whisper.load_model, self.config.whisper_model)
            result = await asyncio.to_thread(model.transcribe, audio_np, fp16=False)
            
            text = result["text"].strip()
            
            self.logger.info(
                f"Transcribed audio to text",
                extra={"extra_fields": {
                    "text_length": len(text),
                    "audio_length_sec": len(audio_data) / (self.config.sample_rate * 2),
                    "correlation_id": correlation_id.value if correlation_id else None
                }}
            )
            
            return text
            
        except Exception as e:
            error_msg = f"Transcription failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            raise AudioException(error_msg, correlation_id)
    
    async def _recording_loop(self, correlation_id: Optional[CorrelationId]) -> None:
        """Main recording loop with voice activity detection."""
        silence_limit_chunks = int(
            self.config.silence_limit_seconds * self.config.sample_rate / self.config.chunk_size
        )
        
        async with AudioResource(self.config) as audio:
            frames = []
            silent_chunks = 0
            speaking = False
            
            self.logger.debug("Started audio recording loop")
            
            while not self._stop_event.is_set():
                try:
                    # Read audio chunk
                    chunk = await audio.read_chunk(self.config.chunk_size)
                    
                    # Calculate RMS for voice activity detection
                    audio_data = np.frombuffer(chunk, dtype=np.int16)
                    rms = np.sqrt(np.mean(np.square(audio_data.astype(np.float32))))
                    
                    # Voice activity detection
                    if rms < self.config.silence_threshold:
                        silent_chunks += 1
                        if speaking and silent_chunks > silence_limit_chunks:
                            # End of speech detected
                            speaking = False
                            if frames:
                                await self._process_speech(frames, audio, correlation_id)
                                frames = []
                            silent_chunks = 0
                    else:
                        silent_chunks = 0
                        if not speaking:
                            # Start of speech detected
                            speaking = True
                            await self._event_bus.publish(AudioEvent(
                                type="audio.speech_started",
                                correlation_id=correlation_id
                            ))
                    
                    if speaking:
                        frames.append(chunk)
                    
                    # Yield control
                    await asyncio.sleep(0.001)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in recording loop: {e}", exc_info=True)
                    await self._event_bus.publish(AudioEvent(
                        type="audio.error",
                        payload={"error": str(e)},
                        correlation_id=correlation_id
                    ))
                    break
    
    async def _process_speech(
        self, 
        frames: list, 
        audio: AudioResource, 
        correlation_id: Optional[CorrelationId]
    ) -> None:
        """Process detected speech frames."""
        if not frames:
            return
        
        try:
            # Combine frames
            audio_data = np.frombuffer(b''.join(frames), dtype=np.int16).flatten().astype(np.float32) / 32768.0
            
            # Transcribe
            await self._event_bus.publish(AudioEvent(
                type="audio.transcription_started",
                correlation_id=correlation_id
            ))
            
            text = await audio.transcribe(audio_data)
            
            if text:
                await self._event_bus.publish(AudioEvent(
                    type="audio.transcription_completed",
                    payload={"text": text, "confidence": 1.0},  # Whisper doesn't provide confidence
                    correlation_id=correlation_id
                ))
                
                # Also publish as user input event
                await self._event_bus.publish(Event(
                    type="user_input",
                    payload={"text": text, "source": "audio"},
                    correlation_id=correlation_id
                ))
                
                self.logger.info(f"Transcribed speech: '{text[:50]}...'")
            
        except Exception as e:
            self.logger.error(f"Error processing speech: {e}", exc_info=True)
            await self._event_bus.publish(AudioEvent(
                type="audio.transcription_failed",
                payload={"error": str(e)},
                correlation_id=correlation_id
            ))