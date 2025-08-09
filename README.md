# L.U.N.A. (Logical Unified Network Assistant)

L.U.N.A. is a personal AI assistant designed for deep integration with NixOS and Hyprland desktop environments. This is a pet project and learning exercise focused on exploring AI development patterns, async Python architecture, and modern software engineering practices. The project serves as a practical way to understand how to build AI applications while creating a useful daily tool.

## Features

*   **Full Audio Pipeline:** Voice-activated conversations with speech-to-text (Whisper) and text-to-speech (espeak-ng) integration
*   **Conversational AI:** Interact with a local LLM (Llama3 via Ollama) for privacy-focused, offline conversations
*   **Tool Integration:** Execute desktop actions (notifications, system commands) through natural language requests
*   **Event-Driven Architecture:** Modern async Python design with publish-subscribe event system
*   **Dependency Injection:** Clean service lifecycle management with proper resource handling
*   **Reproducible Development:** NixOS flake-based development environment for consistent builds
*   **Auto Device Detection:** Smart audio device detection with fallback mechanisms
*   **Comprehensive Testing:** Full test suite covering async patterns and service integration

## Technologies Used

*   **Core Language:** Python 3.11+ with asyncio-first architecture
*   **Development Environment:** NixOS with flake.nix for reproducible builds
*   **Desktop Environment:** Hyprland window manager integration
*   **AI Stack:** LangChain + Ollama running llama3 model locally
*   **Audio Processing:** OpenAI Whisper (STT) + espeak-ng (TTS) + PyAudio
*   **Architecture Patterns:** Dependency injection, event-driven design, async/await
*   **Testing:** pytest with async support and comprehensive mocking
*   **Configuration:** Pydantic v2 with environment variable support

## Setup and Installation

To set up the development environment, ensure you have Nix installed on your system.

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/luna-ai.git
    cd luna-ai
    ```

2.  **Enter the development shell:**

    This will set up the Python environment and other necessary tools defined in `shell.nix`.

    ```bash
    nix develop
    ```

3.  **Install Python dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Ollama and download the Llama3 model:**

    Follow the instructions on the [Ollama website](https://ollama.com/download) to install Ollama. Once installed, download the `llama3` model:

    ```bash
    ollama run llama3
    ```

5.  **Configure environment (optional):**

    Copy `.env.example` to `.env` and customize settings:

    ```bash
    cp .env.example .env
    ```

## Usage

To start L.U.N.A., run the application as a module:

```bash
python -m luna.main
```

L.U.N.A. will start with voice input enabled if audio devices are available. Simply speak to interact with the assistant. If audio is not available, it will fall back to text input mode.

## Audio Configuration

L.U.N.A. includes automatic audio device detection, but you can manually configure audio settings if needed.

### Automatic Device Detection (Default)

By default, L.U.N.A. automatically scans and selects working audio devices. Leave `LUNA_AUDIO_INPUT_DEVICE_INDEX` empty in your `.env` file for automatic detection.

### Manual Device Configuration

If you experience audio issues, you can manually specify the device:

1. **Check Available Devices:**

   Audio device information is logged during startup, or you can check the console output when L.U.N.A. starts.

2. **Set Device Index:**

   In your `.env` file, set:
   ```
   LUNA_AUDIO_INPUT_DEVICE_INDEX=X
   ```
   Replace `X` with your preferred device index.

### Audio Settings

All audio settings can be configured via environment variables:

- `LUNA_AUDIO_SAMPLE_RATE` - Sample rate (default: 16000)
- `LUNA_AUDIO_SILENCE_THRESHOLD` - Voice activity threshold (default: 3000)  
- `LUNA_AUDIO_SILENCE_LIMIT_SECONDS` - Silence timeout (default: 3)
- `LUNA_AUDIO_WHISPER_MODEL` - Whisper model size (default: base.en)

## Testing

To run the test suite, ensure you are in the `nix develop` shell and have installed the Python dependencies. Then, execute `pytest`:

```bash
pytest
```

## Architecture Overview

L.U.N.A. demonstrates modern async Python architecture patterns with clean separation of concerns and robust error handling.

### Core Architecture Patterns

*   **Async-First Design**: Built on asyncio with proper async/await patterns throughout
*   **Event-Driven Architecture**: Publish-subscribe event system for loose coupling between components  
*   **Dependency Injection**: Service container managing component lifecycles and dependencies
*   **Service-Oriented**: Each major functionality (LLM, Audio, TTS, Agent) is a dedicated service
*   **Configuration Management**: Pydantic-based settings with environment variable support

### Key Components

*   **Event Bus (`luna/core/events.py`)**: Async publish-subscribe system enabling decoupled communication
*   **Service Container (`luna/core/di.py`)**: Dependency injection with lifecycle management
*   **Audio Service (`luna/services/audio.py`)**: Speech-to-text with automatic device detection
*   **TTS Service (`luna/services/tts.py`)**: Text-to-speech integration with event system
*   **Agent Service (`luna/services/agent.py`)**: Core conversation logic with tool orchestration
*   **LLM Service (`luna/services/llm.py`)**: Ollama integration with async support

### Event Flow

1. **Audio Input**: AudioService detects speech → transcribes with Whisper → publishes `user_input`
2. **Processing**: AgentService receives input → processes with LLM → publishes `agent.response`  
3. **Tool Execution**: Agent parses JSON tool calls → executes tools → publishes results
4. **Audio Output**: TTSService receives responses → converts to speech via espeak-ng
5. **UI Updates**: Main application displays all events to console with Rich formatting

### Learning Focus Areas

This project explores several modern Python development concepts:

- **Async Programming**: Event loops, coroutines, async context managers, thread-safe patterns
- **Architecture Patterns**: Dependency injection, event sourcing, service-oriented design  
- **AI Integration**: LangChain patterns, LLM tool calling, audio processing pipelines
- **Configuration**: Environment-based config, Pydantic validation, type safety
- **Testing**: Async test patterns, mocking async services, integration testing
- **Development Environment**: NixOS reproducible builds, flake-based development

## Project Structure

```
luna-ai/
├── flake.nix            # NixOS development environment
├── pyproject.toml       # Python project configuration
├── requirements.txt     # Python dependencies
├── .env.example         # Environment configuration template
├── luna/
│   ├── __init__.py
│   ├── main.py          # Application entry point and orchestration
│   ├── core/            # Core infrastructure
│   │   ├── config.py    # Configuration management with Pydantic
│   │   ├── types.py     # Type definitions and protocols
│   │   ├── events.py    # Async event bus implementation
│   │   ├── di.py        # Dependency injection container
│   │   └── logging.py   # Structured logging setup
│   ├── services/        # Business logic services
│   │   ├── llm.py       # Ollama LLM integration
│   │   ├── audio.py     # Speech-to-text with Whisper
│   │   ├── tts.py       # Text-to-speech with espeak-ng  
│   │   └── agent.py     # Conversation logic and tool orchestration
│   └── tools/           # Available tools for the agent
│       ├── base.py      # Tool registry and base classes
│       └── desktop.py   # Desktop notifications and system commands
└── tests/               # Comprehensive test suite
    ├── conftest.py      # Pytest configuration and fixtures
    ├── core/            # Tests for core infrastructure
    └── tools/           # Tests for tool implementations
```

## License

This project is licensed under the [MIT License](LICENSE).