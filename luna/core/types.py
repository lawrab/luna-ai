"""
Core type definitions and domain models for L.U.N.A.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Generic, List, Optional, Protocol, TypeVar, Union, runtime_checkable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, ConfigDict


# Base Types
T = TypeVar('T')
EventHandler = Callable[..., Union[None, Awaitable[None]]]


class LogLevel(str, Enum):
    """Structured logging levels."""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ServiceStatus(str, Enum):
    """Service lifecycle status."""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


@dataclass(frozen=True)
class CorrelationId:
    """Correlation ID for request tracing."""
    value: str = field(default_factory=lambda: str(uuid4()))


# Event System Types
class Event(BaseModel):
    """Base event model."""
    id: UUID = Field(default_factory=uuid4)
    type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[CorrelationId] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class AudioEvent(Event):
    """Audio-related events."""
    type: str = "audio"


class AgentEvent(Event):
    """Agent-related events."""  
    type: str = "agent"


class ToolEvent(Event):
    """Tool execution events."""
    type: str = "tool"
    tool_name: Optional[str] = None
    tool_args: Dict[str, Any] = Field(default_factory=dict)


class SystemEvent(Event):
    """System lifecycle events."""
    type: str = "system"
    status: Optional[ServiceStatus] = None


# Tool System Types
class ToolInput(BaseModel):
    """Base class for tool inputs with validation."""
    pass


class ToolResult(BaseModel):
    """Base class for tool execution results."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None


class ToolMetadata(BaseModel):
    """Tool metadata for discovery and validation."""
    name: str
    description: str
    input_schema: type[ToolInput]
    output_schema: type[ToolResult] = ToolResult
    category: str = "general"
    tags: List[str] = Field(default_factory=list)


# Service Interfaces
@runtime_checkable
class Service(Protocol):
    """Protocol for all L.U.N.A. services."""
    
    @property
    def name(self) -> str:
        """Service name."""
        ...
        
    @property 
    def status(self) -> ServiceStatus:
        """Current service status."""
        ...
        
    async def start(self) -> None:
        """Start the service."""
        ...
        
    async def stop(self) -> None:
        """Stop the service gracefully."""
        ...
        
    async def health_check(self) -> bool:
        """Check if service is healthy."""
        ...


class EventBus(Protocol):
    """Event bus interface."""
    
    async def publish(self, event: Event) -> None:
        """Publish an event."""
        ...
        
    def subscribe(self, event_type: str, handler: EventHandler) -> str:
        """Subscribe to events, returns subscription ID."""
        ...
        
    def unsubscribe(self, subscription_id: str) -> None:
        """Remove subscription."""
        ...
        
    async def wait_for_event(self, event_type: str, timeout: Optional[float] = None) -> Optional[Event]:
        """Wait for a specific event."""
        ...


class Tool(Protocol):
    """Protocol for L.U.N.A. tools."""
    
    @property
    def metadata(self) -> ToolMetadata:
        """Tool metadata."""
        ...
        
    async def execute(self, input_data: ToolInput) -> ToolResult:
        """Execute the tool with given input."""
        ...


class LLMProvider(Protocol):
    """Protocol for LLM providers."""
    
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a response from the LLM."""
        ...
        
    async def health_check(self) -> bool:
        """Check if LLM is available."""
        ...


class AudioProvider(Protocol):
    """Protocol for audio services."""
    
    async def start_recording(self) -> None:
        """Start audio recording."""
        ...
        
    async def stop_recording(self) -> None:
        """Stop audio recording."""
        ...
        
    async def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio to text."""
        ...


# Configuration Types
class AudioConfig(BaseModel):
    """Audio configuration."""
    input_device_index: Optional[int] = None
    sample_rate: int = 16000
    chunk_size: int = 1024
    channels: int = 1
    silence_threshold: int = 3000
    silence_limit_seconds: int = 3
    whisper_model: str = "base.en"


class LLMConfig(BaseModel):
    """LLM configuration."""
    model_name: str = "llama3"
    base_url: str = "http://localhost:11434"
    timeout_seconds: int = 30
    max_retries: int = 3
    temperature: float = 0.7


class TTSConfig(BaseModel):
    """TTS configuration."""
    enabled: bool = True
    engine: str = "espeak-ng"
    voice: str = "en"
    speed: int = 175
    pitch: int = 50
    volume: int = 100


class AppConfig(BaseModel):
    """Application configuration."""
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    audio: AudioConfig = Field(default_factory=AudioConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    
    @field_validator('log_level', mode='before')
    @classmethod 
    def validate_log_level(cls, v):
        if isinstance(v, str):
            return LogLevel(v.upper())
        return v


# Exceptions
class LunaException(Exception):
    """Base exception for L.U.N.A."""
    def __init__(self, message: str, correlation_id: Optional[CorrelationId] = None):
        super().__init__(message)
        self.correlation_id = correlation_id


class ServiceException(LunaException):
    """Service-related exceptions."""
    pass


class ToolException(LunaException):
    """Tool execution exceptions."""
    pass


class AudioException(LunaException):
    """Audio-related exceptions."""
    pass


class LLMException(LunaException):
    """LLM provider exceptions."""
    pass