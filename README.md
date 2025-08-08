# L.U.N.A. (Logical Unified Network Assistant)

L.U.N.A. is a personal AI assistant designed for deep integration with NixOS and Hyprland desktop environments. It's built as a living, evolving application for learning and practical daily use, focusing on robust tool integration and a modular architecture.

## Features

*   **Conversational AI:** Interact with a local LLM (Llama3 via Ollama) for natural language conversations.
*   **Tool Integration:** L.U.N.A. can execute specific actions (e.g., sending desktop notifications) by parsing LLM output, enabling interaction with the desktop environment.
*   **Reproducible Development Environment:** Utilizes NixOS `shell.nix` for consistent environment setup.
*   **Modular Design:** A well-structured Python package with clear separation of concerns (agent, tools, prompts, configuration).
*   **Automated Testing:** Comprehensive unit and integration tests using `pytest` to ensure reliability.

## Technologies Used

*   **Operating System:** NixOS
*   **Window Manager:** Hyprland
*   **Programming Language:** Python
*   **Environment Management:** `shell.nix` (NixOS)
*   **Dependency Management:** `pip` and `requirements.txt`
*   **AI Framework:** LangChain
*   **LLM Runner:** Ollama (running `llama3` locally)
*   **Testing Framework:** `pytest` with `unittest.mock`

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

## Usage

To start L.U.N.A., run the `main.py` script:

```bash
python luna/main.py
```

L.U.N.A. will then be ready to receive your input in the terminal.

## Testing

To run the test suite, ensure you are in the `nix develop` shell and have installed the Python dependencies. Then, execute `pytest`:

```bash
pytest
```

## Application Architecture

L.U.N.A. is built on a modular, event-driven architecture that decouples the core logic from the user interface and other components. This design makes the application more flexible, extensible, and easier to maintain.

### Core Components

*   **Event Bus (`luna/events.py`)**: A simple publish-subscribe system that allows different parts of the application to communicate without being directly coupled. For example, when the agent has a response, it publishes an `agent_response` event, and the UI and speech modules subscribe to this event to act on it.
*   **UI Abstraction (`luna/ui.py`)**: A module that handles all console output. It wraps the `rich` library, so if you ever want to switch to a different UI toolkit (like a graphical one), you'll only need to change this one file.
*   **Agent (`luna/agent.py`)**: The core logic of the assistant. It receives user input, interacts with the LLM, and publishes events with the results.
*   **Speech (`luna/speech.py`)**: Handles text-to-speech functionality. It subscribes to the `agent_response` event to speak the assistant's responses.
*   **Listener (`luna/listen.py`)**: Handles speech-to-text functionality. It listens for user input and publishes a `user_input` event when it detects speech.
*   **Main (`luna/main.py`)**: The entry point of the application. It initializes the core components, registers event listeners, and starts the main application loop.

### Event Flow

1.  The `main.py` module starts the application and the main loop.
2.  The `listen.py` module listens for user input.
3.  When the user speaks, `listen.py` transcribes the speech and publishes a `user_input` event.
4.  The `agent.py` module, which subscribes to the `user_input` event, receives the transcribed text and processes it.
5.  The `agent.py` module interacts with the LLM and publishes an `agent_response` event with the result.
6.  The `ui.py` and `speech.py` modules, which subscribe to the `agent_response` event, receive the response and display it to the user (text and speech).

## Project Structure

```
./
├───.git/
├───.gitignore
├───GEMINI.md
├───LICENSE
├───pytest.ini
├───README.md
├───requirements.txt
├───shell.nix
├───luna/
│   ├───__init__.py
│   ├───agent.py         # Core LunaAgent class encapsulating assistant logic
│   ├───config.py        # Centralized configuration settings
│   ├───events.py        # Event bus for decoupled communication
│   ├───listen.py        # Speech-to-text functionality
│   ├───main.py          # Entry point for the application
│   ├───prompts.py       # Defines system prompts for the LLM
│   ├───speech.py        # Text-to-speech functionality
│   ├───tools.py         # Defines available tools (e.g., send_desktop_notification)
│   └───ui.py            # UI abstraction for console output
└───tests/
    ├───__init__.py
    ├───test_agent.py    # Integration tests for LunaAgent
    └───test_tools.py    # Unit tests for tool functions
```

## License

This project is licensed under the [MIT License](LICENSE).