"""
Audio service with robust resource management and proper error handling.

This implementation focuses on:
1. Simple, reliable PyAudio resource management
2. Singleton Whisper model loading
3. Proper async/sync boundaries
4. Graceful error handling and recovery
5. Clear separation of concerns
"""
import asyncio
import threading
from typing import Optional, Any, List
from dataclasses import dataclass
from enum import Enum

try:
    import pyaudio
    import numpy as np
    import whisper
    AUDIO_DEPENDENCIES_AVAILABLE = True
except (ImportError, OSError) as e:
    AUDIO_DEPENDENCIES_AVAILABLE = False
    AUDIO_IMPORT_ERROR = str(e)

from ..core.types import AudioConfig, ServiceStatus, AudioException, Event, AudioEvent, CorrelationId
from ..core.logging import get_logger, LoggingMixin
from ..core.events import get_event_bus
from ..core.di import Injectable


logger = get_logger(__name__)


class AudioState(Enum):
    """Audio service states."""
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass
class AudioStats:
    """Audio processing statistics."""
    chunks_processed: int = 0
    speech_segments: int = 0
    transcription_time_ms: float = 0
    errors: int = 0


class WhisperModelManager:
    """Singleton manager for Whisper model to avoid repeated loading."""
    
    _instance: Optional['WhisperModelManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'WhisperModelManager':
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized') or not self._initialized:
            self._model: Optional[Any] = None
            self._model_name: Optional[str] = None
            self._load_lock = threading.Lock()
            self._initialized = True
    
    def get_model(self, model_name: str = "base.en") -> Any:
        """Get the Whisper model, loading it if necessary."""
        if self._model is None or self._model_name != model_name:
            with self._load_lock:
                # Double-check pattern
                if self._model is None or self._model_name != model_name:
                    logger.info(f"Loading Whisper model: {model_name}")
                    self._model = whisper.load_model(model_name)
                    self._model_name = model_name
                    logger.info("Whisper model loaded successfully")
        return self._model


class AudioDevice:
    """Manages PyAudio device and stream lifecycle with automatic device detection."""
    
    def __init__(self, config: AudioConfig):
        self.config = config
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._selected_device_index: Optional[int] = None
        self._selected_sample_rate: int = config.sample_rate
        self._lock = threading.Lock()
    
    def __enter__(self):
        """Initialize PyAudio and open stream with automatic device/rate selection."""
        if not AUDIO_DEPENDENCIES_AVAILABLE:
            raise AudioException(f"Audio dependencies not available: {AUDIO_IMPORT_ERROR}")
        
        try:
            # Initialize PyAudio
            self._pyaudio = pyaudio.PyAudio()
            
            # Find the best device and sample rate
            device_index, sample_rate = self._find_best_device()
            self._selected_device_index = device_index
            self._selected_sample_rate = sample_rate
            
            # Open audio stream with validated parameters
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=sample_rate,
                input=True,
                frames_per_buffer=self.config.chunk_size,
                input_device_index=device_index
            )
            
            device_name = "default" if device_index is None else self._pyaudio.get_device_info_by_index(device_index).get('name', 'Unknown')
            logger.info(f"Audio stream opened: device='{device_name}', rate={sample_rate}Hz, channels={self.config.channels}")
            return self
            
        except Exception as e:
            self._cleanup()
            raise AudioException(f"Failed to initialize audio device: {e}")
    
    def _find_best_device(self) -> tuple[Optional[int], int]:
        """Find the best available audio input device and sample rate."""
        
        # If user specified a device index, try it first
        if self.config.input_device_index is not None:
            device_index = self.config.input_device_index
            try:
                device_info = self._pyaudio.get_device_info_by_index(device_index)
                if device_info.get('maxInputChannels', 0) > 0:
                    # Try to find a working sample rate for this device
                    sample_rate = self._find_best_sample_rate(device_index, device_info)
                    if sample_rate:
                        logger.info(f"Using configured device {device_index}: {device_info.get('name', 'Unknown')} at {sample_rate}Hz")
                        return device_index, sample_rate
                    else:
                        logger.warning(f"Configured device {device_index} doesn't support any tested sample rates")
                else:
                    logger.warning(f"Configured device {device_index} has no input channels")
            except Exception as e:
                logger.warning(f"Configured device {device_index} failed: {e}")
        
        # Fallback: try the system default device
        try:
            default_sample_rate = self._find_best_sample_rate(None, None)
            if default_sample_rate:
                logger.info(f"Using system default audio device at {default_sample_rate}Hz")
                return None, default_sample_rate
        except Exception as e:
            logger.warning(f"System default device failed: {e}")
        
        # Last resort: scan all available input devices
        logger.info("Scanning all available audio input devices...")
        device_count = self._pyaudio.get_device_count()
        
        for i in range(device_count):
            try:
                device_info = self._pyaudio.get_device_info_by_index(i)
                if device_info.get('maxInputChannels', 0) > 0:
                    sample_rate = self._find_best_sample_rate(i, device_info)
                    if sample_rate:
                        logger.info(f"Found working device {i}: {device_info.get('name', 'Unknown')} at {sample_rate}Hz")
                        return i, sample_rate
            except Exception as e:
                logger.debug(f"Device {i} failed: {e}")
        
        raise AudioException("No suitable audio input device found")
    
    def _find_best_sample_rate(self, device_index: Optional[int], device_info: Optional[dict]) -> Optional[int]:
        """Find the best supported sample rate for a device."""
        
        # Start with preferred rate, then try common rates
        preferred_rate = self.config.sample_rate
        common_rates = [16000, 22050, 44100, 48000, 8000, 11025, 32000, 96000]
        
        # Put preferred rate first if not already in common_rates
        test_rates = [preferred_rate] + [r for r in common_rates if r != preferred_rate]
        
        # If device info is available, try its default rate too
        if device_info and 'defaultSampleRate' in device_info:
            default_rate = int(device_info['defaultSampleRate'])
            if default_rate not in test_rates:
                test_rates.insert(1, default_rate)
        
        for rate in test_rates:
            try:
                # Test if this rate is supported
                if self._pyaudio.is_format_supported(
                    rate,
                    input_device=device_index,
                    input_channels=self.config.channels,
                    input_format=pyaudio.paInt16
                ):
                    return rate
            except Exception:
                continue
        
        return None
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up PyAudio resources."""
        self._cleanup()
    
    def _cleanup(self):
        """Internal cleanup method."""
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                logger.warning(f"Error closing audio stream: {e}")
            finally:
                self._stream = None
        
        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception as e:
                logger.warning(f"Error terminating PyAudio: {e}")
            finally:
                self._pyaudio = None
    
    def read(self, num_frames: int) -> bytes:
        """Read audio data synchronously."""
        if not self._stream:
            raise AudioException("Audio stream not initialized")
        
        return self._stream.read(num_frames, exception_on_overflow=False)
    
    def is_active(self) -> bool:
        """Check if stream is active."""
        return self._stream is not None and self._stream.is_active()


class AudioService(Injectable, LoggingMixin):
    """
    Production-ready audio service with proper resource management.
    
    Key design principles:
    - Simple, reliable resource management
    - Clear async/sync boundaries
    - Singleton model loading
    - Graceful error handling
    """
    
    def __init__(self, config: AudioConfig):
        self.config = config
        self._status = ServiceStatus.INITIALIZING
        self._state = AudioState.IDLE
        self._recording_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._event_bus = get_event_bus()
        self._stats = AudioStats()
        self._model_manager = WhisperModelManager() if AUDIO_DEPENDENCIES_AVAILABLE else None
        
    @property
    def name(self) -> str:
        return "audio-service"
    
    @property
    def status(self) -> ServiceStatus:
        return self._status
    
    @property
    def state(self) -> AudioState:
        return self._state
    
    @property
    def stats(self) -> AudioStats:
        return self._stats
    
    async def start(self) -> None:
        """Start the audio service."""
        try:
            if not AUDIO_DEPENDENCIES_AVAILABLE:
                self._status = ServiceStatus.DEGRADED
                self.logger.warning(f"Audio service degraded: {AUDIO_IMPORT_ERROR}")
                await self._publish_status_event("degraded", "dependencies_unavailable")
                return
            
            # Test audio device availability
            if not await self._test_audio_device():
                self._status = ServiceStatus.DEGRADED
                self.logger.warning("Audio device test failed, service degraded")
                await self._publish_status_event("degraded", "device_unavailable")
                return
            
            self._status = ServiceStatus.HEALTHY
            self._state = AudioState.IDLE
            self.logger.info("Audio service started successfully")
            await self._publish_status_event("healthy")
            
        except Exception as e:
            self._status = ServiceStatus.FAILED
            self._state = AudioState.ERROR
            self.logger.error(f"Failed to start audio service: {e}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """Stop the audio service."""
        self.logger.info("Stopping audio service...")
        
        # Stop recording if active
        if self._recording_task and not self._recording_task.done():
            await self.stop_recording()
        
        self._status = ServiceStatus.SHUTDOWN
        self._state = AudioState.IDLE
        self.logger.info("Audio service stopped")
    
    async def health_check(self) -> bool:
        """Check if audio service is healthy."""
        if not AUDIO_DEPENDENCIES_AVAILABLE:
            return False
        
        return await self._test_audio_device()
    
    async def start_recording(self, correlation_id: Optional[CorrelationId] = None) -> None:
        """Start continuous audio recording and transcription."""
        if self._status not in (ServiceStatus.HEALTHY, ServiceStatus.DEGRADED):
            raise AudioException("Audio service not ready")
        
        if self._state != AudioState.IDLE:
            self.logger.warning(f"Cannot start recording, current state: {self._state}")
            return
        
        if not AUDIO_DEPENDENCIES_AVAILABLE:
            raise AudioException("Audio dependencies not available")
        
        self._stop_event.clear()
        self._state = AudioState.RECORDING
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
        if self._state != AudioState.RECORDING:
            return
        
        self.logger.info("Stopping audio recording...")
        self._stop_event.set()
        
        if self._recording_task and not self._recording_task.done():
            try:
                await asyncio.wait_for(self._recording_task, timeout=5.0)
            except asyncio.TimeoutError:
                self.logger.warning("Recording task did not stop gracefully, cancelling")
                self._recording_task.cancel()
                try:
                    await self._recording_task
                except asyncio.CancelledError:
                    pass
        
        self._state = AudioState.IDLE
        self.logger.info("Audio recording stopped")
        await self._event_bus.publish(AudioEvent(type="audio.recording_stopped"))
    
    async def transcribe_audio(self, audio_data: bytes, correlation_id: Optional[CorrelationId] = None) -> str:
        """Transcribe audio data to text."""
        if not AUDIO_DEPENDENCIES_AVAILABLE or not self._model_manager:
            raise AudioException("Audio transcription not available")
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Convert bytes to numpy array
            audio_np = np.frombuffer(audio_data, dtype=np.int16).flatten().astype(np.float32) / 32768.0
            
            # Transcribe using thread pool to avoid blocking
            model = await asyncio.to_thread(self._model_manager.get_model, self.config.whisper_model)
            result = await asyncio.to_thread(model.transcribe, audio_np, fp16=False)
            
            text = result["text"].strip()
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            self.logger.info(
                f"Transcribed audio",
                extra={"extra_fields": {
                    "text_length": len(text),
                    "audio_length_sec": len(audio_data) / (self.config.sample_rate * 2),  # This will be approximate
                    "transcription_time_ms": duration_ms,
                    "correlation_id": correlation_id.value if correlation_id else None
                }}
            )
            
            self._stats.transcription_time_ms = duration_ms
            return text
            
        except Exception as e:
            self._stats.errors += 1
            error_msg = f"Transcription failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            raise AudioException(error_msg, correlation_id)
    
    async def _test_audio_device(self) -> bool:
        """Test if audio device is available and working."""
        try:
            # Quick test in thread pool
            def test_device():
                with AudioDevice(self.config):
                    pass  # Just test initialization
                return True
            
            return await asyncio.to_thread(test_device)
            
        except Exception as e:
            self.logger.warning(f"Audio device test failed: {e}")
            return False
    
    async def _recording_loop(self, correlation_id: Optional[CorrelationId]) -> None:
        """Main recording loop with voice activity detection."""
        # Will be updated with actual device sample rate once device is initialized
        actual_sample_rate = self.config.sample_rate
        silence_limit_chunks = int(
            self.config.silence_limit_seconds * actual_sample_rate / self.config.chunk_size
        )
        
        # Use a simpler approach - keep the async recording loop
        frames: List[bytes] = []
        silent_chunks = 0
        speaking = False
        
        try:
            # Test device initialization first
            def init_device():
                return AudioDevice(self.config)
            
            device = await asyncio.to_thread(init_device)
            
            # Use context manager manually for better control
            with device:
                # Update actual sample rate used by the device
                actual_sample_rate = device._selected_sample_rate
                silence_limit_chunks = int(
                    self.config.silence_limit_seconds * actual_sample_rate / self.config.chunk_size
                )
                
                logger.debug("Audio recording loop started")
                
                while not self._stop_event.is_set():
                    try:
                        # Read audio chunk in thread pool
                        chunk = await asyncio.to_thread(device.read, self.config.chunk_size)
                        self._stats.chunks_processed += 1
                        
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
                                    await self._handle_speech_segment(frames, correlation_id)
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
                        
                        # Small async sleep to prevent busy loop
                        await asyncio.sleep(0.001)
                        
                    except Exception as e:
                        self._stats.errors += 1
                        logger.error(f"Error in recording loop: {e}", exc_info=True)
                        await self._event_bus.publish(AudioEvent(
                            type="audio.error",
                            payload={"error": str(e)},
                            correlation_id=correlation_id
                        ))
                        break
                        
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"Fatal error in recording loop: {e}", exc_info=True)
            self._state = AudioState.ERROR
        finally:
            self._state = AudioState.IDLE
    
    async def _handle_speech_segment(self, frames: List[bytes], correlation_id: Optional[CorrelationId]) -> None:
        """Handle a detected speech segment."""
        if not frames:
            return
        
        self._stats.speech_segments += 1
        
        try:
            self._state = AudioState.PROCESSING
            
            await self._event_bus.publish(AudioEvent(
                type="audio.transcription_started",
                correlation_id=correlation_id
            ))
            
            # Combine frames and transcribe
            audio_data = b''.join(frames)
            text = await self.transcribe_audio(audio_data, correlation_id)
            
            if text:
                await self._event_bus.publish(AudioEvent(
                    type="audio.transcription_completed", 
                    payload={"text": text, "confidence": 1.0},
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
            self._stats.errors += 1
            self.logger.error(f"Error processing speech: {e}", exc_info=True)
            await self._event_bus.publish(AudioEvent(
                type="audio.transcription_failed",
                payload={"error": str(e)},
                correlation_id=correlation_id
            ))
        finally:
            if self._state == AudioState.PROCESSING:
                self._state = AudioState.RECORDING
    
    async def _publish_status_event(self, status: str, reason: Optional[str] = None) -> None:
        """Publish audio status change event."""
        payload = {"status": status}
        if reason:
            payload["reason"] = reason
            
        await self._event_bus.publish(AudioEvent(
            type="audio.status_changed",
            payload=payload
        ))