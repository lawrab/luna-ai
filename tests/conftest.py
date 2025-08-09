"""
Pytest configuration and fixtures for L.U.N.A. tests.
"""
import asyncio
import logging
import pytest
import pytest_asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncGenerator, Generator

from luna.core.config import ConfigManager, Settings
from luna.core.events import AsyncEventBus
from luna.core.di import Container
from luna.core.types import AppConfig, AudioConfig, LLMConfig, CorrelationId
from luna.tools.base import ToolRegistry


# Configure test logging
logging.basicConfig(level=logging.DEBUG)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def temp_dir() -> AsyncGenerator[Path, None]:
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_settings(temp_dir: Path) -> Settings:
    """Create test settings with temporary directories."""
    return Settings(
        debug=True,
        log_level="DEBUG",
        data_dir=temp_dir,
        llm_model_name="test-model",
        llm_base_url="http://localhost:11434",
        audio_whisper_model="base.en"
    )


@pytest.fixture
def test_config(test_settings: Settings) -> AppConfig:
    """Create test application configuration."""
    return test_settings.to_app_config()


@pytest.fixture
def config_manager(test_settings: Settings) -> ConfigManager:
    """Create a test config manager."""
    config_mgr = ConfigManager(test_settings)
    config_mgr.ensure_directories()
    return config_mgr


@pytest_asyncio.fixture
async def event_bus() -> AsyncGenerator[AsyncEventBus, None]:
    """Create and start a test event bus."""
    bus = AsyncEventBus(name="test-event-bus")
    await bus.start()
    try:
        yield bus
    finally:
        await bus.stop()


@pytest_asyncio.fixture
async def container() -> AsyncGenerator[Container, None]:
    """Create a test dependency injection container."""
    test_container = Container(name="test-container")
    try:
        yield test_container
    finally:
        await test_container.stop_all_services()
        test_container.clear()


@pytest.fixture
def tool_registry() -> ToolRegistry:
    """Create a fresh tool registry for tests."""
    return ToolRegistry()


@pytest.fixture
def correlation_id() -> CorrelationId:
    """Create a test correlation ID."""
    return CorrelationId("test-correlation-id")


@pytest.fixture
def mock_llm() -> AsyncMock:
    """Create a mock LLM for testing."""
    mock = AsyncMock()
    mock.generate.return_value = "Test response"
    mock.health_check.return_value = True
    return mock


@pytest.fixture
def mock_audio_provider() -> AsyncMock:
    """Create a mock audio provider for testing."""
    mock = AsyncMock()
    mock.start_recording.return_value = None
    mock.stop_recording.return_value = None
    mock.transcribe.return_value = "test transcription"
    return mock


@pytest.fixture
def mock_subprocess() -> MagicMock:
    """Create a mock subprocess for command execution tests."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"success", b"")
    
    return mock_process


# Async test markers
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(autouse=True)
def reset_globals():
    """Reset global state between tests."""
    # Reset any global state that might interfere with tests
    yield
    # Cleanup code here if needed


class AsyncTestCase:
    """Base class for async test cases."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, event_bus, container, tool_registry):
        self.event_bus = event_bus
        self.container = container
        self.tool_registry = tool_registry


# Custom assertions for async testing
async def assert_event_published(event_bus: AsyncEventBus, event_type: str, timeout: float = 1.0):
    """Assert that an event was published within timeout."""
    event = await event_bus.wait_for_event(event_type, timeout=timeout)
    assert event is not None, f"Event {event_type} was not published within {timeout}s"
    return event


async def assert_no_event_published(event_bus: AsyncEventBus, event_type: str, timeout: float = 0.1):
    """Assert that an event was NOT published within timeout."""
    event = await event_bus.wait_for_event(event_type, timeout=timeout)
    assert event is None, f"Event {event_type} was unexpectedly published"


# Test data factories
def make_test_event(event_type: str = "test_event", **kwargs):
    """Factory for creating test events."""
    from luna.core.types import Event
    
    return Event(
        type=event_type,
        payload=kwargs
    )


def make_test_tool_call(tool_name: str = "test_tool", **tool_args):
    """Factory for creating test tool calls."""
    return {
        "tool_name": tool_name,
        "tool_args": tool_args
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "requires_audio: marks tests that require audio hardware"
    )
    config.addinivalue_line(
        "markers", "requires_ollama: marks tests that require Ollama service"
    )