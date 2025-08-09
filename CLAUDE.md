# L.U.N.A. Project Memory

## Project Overview
L.U.N.A. (Logical Unified Network Assistant) is a personal AI assistant built for NixOS with Hyprland desktop environment. The project emphasizes async-first architecture, event-driven design, local AI with Ollama, and reproducible development.

## Core Technologies
- **OS Environment**: NixOS with Hyprland window manager
- **Development Environment**: Managed by `flake.nix` for reproducibility
- **Language**: Python 3.11+ with asyncio
- **AI Framework**: LangChain for LLM orchestration
- **LLM**: Ollama running llama3 model locally
- **Speech**: OpenAI Whisper (STT), espeak-ng (TTS)
- **Audio**: PyAudio for microphone input
- **Testing**: pytest with async support
- **Dependencies**: pip + requirements.txt

## Architecture Overview
```
luna/
├── main.py          # Entry point with App class and asyncio event loop
├── core/            # Core framework components
│   ├── config.py    # Configuration management with Pydantic v2
│   ├── events.py    # Async event bus system
│   ├── di.py        # Dependency injection container
│   ├── logging.py   # Structured logging
│   └── types.py     # Type definitions and protocols
├── services/        # Service layer
│   ├── agent.py     # LunaAgent - core AI logic and tool orchestration
│   ├── audio.py     # Audio service with voice detection
│   └── llm.py       # Ollama LLM service
└── tools/           # Available tools (desktop notifications, system commands)
```

## Major Issues Resolved

### 1. Pydantic v2 Migration
**Problem**: Application failed to start due to incompatible Pydantic imports
**Solution**: 
- Updated `BaseSettings` import from `pydantic-settings`
- Changed `@validator` to `@field_validator` with proper syntax
- Fixed `regex` parameter renamed to `pattern` in Field definitions
- Added `@runtime_checkable` decorator to Service protocol

### 2. Service Lifecycle Bug
**Problem**: Services registered after startup, causing agent to never subscribe to events
**Solution**: 
- Fixed dependency injection container lifecycle flow
- Services now get registered BEFORE starting, not after
- Agent service now properly subscribes to `user_input` events

### 3. Audio System Complete Overhaul
**Problem**: Audio was completely non-functional - no device detection, segfaults, wrong thresholds
**Solution**: Implemented robust audio system with:

#### Device Detection
- Automatic audio device discovery and validation
- Sample rate compatibility testing (16kHz, 22kHz, 44.1kHz, 48kHz)
- Fallback strategy: configured device → default device → scan all devices
- Proper error handling for device unavailability

#### Resource Management
- Simplified PyAudio context management without complex async wrappers
- Singleton Whisper model manager to prevent repeated loading
- Clean resource cleanup without memory leaks
- Thread-safe model loading with proper locking

#### Voice Activity Detection
- Two-level threshold system with hysteresis:
  - Speech start threshold: 800 RMS (prevents false positives)
  - Speech end threshold: 200 RMS (prevents cutting off speech)
- Reduced silence timeout from 3 seconds to 1 second for responsiveness
- Proper background noise handling (~50-70 RMS doesn't trigger)
- Debug logging for RMS values and detection events

#### Configuration
- Added validation for empty device index values (converts "" to None)
- Automatic device configuration without hardcoded indices
- Environment variable support for all audio parameters

## Current State
- ✅ **Application Startup**: All services start correctly and healthily
- ✅ **Event System**: Proper async event bus with working subscriptions
- ✅ **LLM Integration**: Ollama + llama3 working with tool execution
- ✅ **Audio Input**: Complete voice detection and transcription pipeline
- ✅ **Tool System**: Desktop notifications and system commands functional
- ✅ **Error Handling**: Graceful degradation and proper exception handling
- ✅ **Resource Management**: Clean startup/shutdown without leaks

## Architecture Principles Established
1. **Async-first**: All services use proper asyncio patterns
2. **Event-driven**: Loose coupling via publish-subscribe pattern
3. **Dependency Injection**: Services properly managed through DI container
4. **Configuration Management**: Environment-based config with validation
5. **Error Resilience**: Services can start in degraded mode if dependencies unavailable
6. **Resource Cleanup**: Proper lifecycle management for all resources

## Development Workflow
- **Environment**: Use `nix develop` to enter development shell
- **Testing**: `pytest tests/` (async patterns implemented)
- **Dependencies**: Add to `requirements.txt`, install with pip in dev shell
- **Configuration**: Environment variables in `.env` file
- **Debugging**: Structured logging with correlation IDs

## Writing Style Requirements
**IMPORTANT**: Always use UK English spelling and conventions:
- Use "realise" not "realize"  
- Use "colour" not "color"
- Use "organised" not "organized"
- Use "behaviour" not "behavior"
- Use "centre" not "center"
- Use "licence" (noun) / "license" (verb)
- Use other British spelling conventions throughout all documentation, code comments, and commit messages

## TTS Integration Complete
**Latest Addition**: Text-to-speech functionality fully integrated
**Implementation**:
- Created `TTSService` in `luna/services/tts.py` with espeak-ng integration
- Event-driven architecture: subscribes to `agent.response` events
- Automatic speech conversion for conversational responses
- Configurable voice parameters (speed, pitch, volume, voice)
- Clean text processing for better speech synthesis (acronym handling, length limits)
- Proper error handling and service health checking

**Current Pipeline**: Voice Input → Whisper STT → LLM Processing → Tool Execution → espeak-ng TTS Output

## Split Terminal UI (Completed)
**Latest Addition**: Professional split terminal interface for improved user experience
**Implementation**:
- Rich Layout-based split panes (75% debug logs, 25% user interaction)
- Real-time message queuing and display updates using `asyncio.Queue`
- Service status monitoring with emoji indicators
- Custom logging handler that captures all output to prevent console interference
- Fixed screen flickering by completely eliminating direct console output below interface
- Separate logs from interactive messages to reduce spam

**UI Features**:
- Live log streaming with colour-coded severity levels
- Service health status indicators (🟢 healthy, 🟡 degraded, 🔴 failed)
- Interactive message pane with timestamps and emojis
- Graceful startup/shutdown with proper resource cleanup
- 4 FPS refresh rate for smooth updates without performance impact

The system is now production-ready with complete bidirectional audio functionality, professional terminal interface, proper error handling, and clean architecture patterns.