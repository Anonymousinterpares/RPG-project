# RPG Text Adventure Game

## Overview

This project is a text-based RPG adventure game framework that combines traditional role-playing elements with modern LLM (Large Language Model) technology. The goal is to create dynamic narratives, interactive characters, and an immersive game world generated and managed with the help of AI.

## Features

*   **Core RPG Gameplay:** Character creation, inventory management, combat system (under development), time system, save/load functionality.
*   **LLM Integration:** Dynamic story generation, NPC interactions, rule checking, and context evaluation powered by configurable LLM providers (OpenAI, Google, OpenRouter).
*   **Graphical User Interface (GUI):** A desktop application built with PySide6 providing a visual way to interact with the game.
*   **Command Line Interface (CLI):** A text-based interface for playing the game in a terminal.
*   **Web Interface:** A web-based frontend (using FastAPI and a simple HTML/JS client) to interact with the game engine remotely.
*   **World Configurator:** A separate tool (also using PySide6) for creating and editing game world data, items, locations, etc.
*   **Modular Design:** Separated components for core logic, UI, configuration, and LLM integration.

## Technology Stack

*   **Language:** Python 3.9+
*   **GUI:** PySide6
*   **Web Framework:** FastAPI
*   **Configuration:** JSON
*   **Core Libraries:** Standard Python libraries

## Project Structure

The project is organized into the following main directories:

*   `config/`: Contains JSON configuration files for game settings, LLM providers, items, locations, etc. ([config/README.md](./config/README.md))
*   `core/`: Houses the core game engine logic, including state management, command processing, LLM integration, character systems, inventory, and utilities. ([core/README.md](./core/README.md))
*   `gui/`: Components for the PySide6-based desktop graphical user interface. ([gui/README.md](./gui/README.md))
*   `web/`: Contains the FastAPI server and basic HTML/JS client for the web interface. ([web/README.md](./web/README.md))
*   `world_configurator/`: The standalone application for editing game world data. ([world_configurator/README.md](./world_configurator/README.md))
*   `tests/`: Unit and integration tests for the project components. ([tests/README.md](./tests/README.md))
*   `images/`: Static image assets used by the GUI and potentially the web interface.
*   `logs/`: Application log files.
*   `saves/`: Default directory for saved game files.
*   `sound/`: Sound effects and music files.

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # Activate the environment
    # Windows (cmd.exe):
    venv\Scripts\activate.bat
    # Windows (PowerShell):
    .\venv\Scripts\Activate.ps1
    # Linux/macOS:
    source venv/bin/activate
    ```
3.  **Install Dependencies:**
    The project uses `setup.py`. Install the project and its dependencies in editable mode:
    ```bash
    pip install -e .
    ```
    *Note: The web server component might have additional dependencies listed in `web/server/requirements.txt`. If you plan to run the web server, install those as well:*
    ```bash
    pip install -r web/server/requirements.txt
    ```

## Running the Application

### Main Game (GUI Mode)

This is the primary way to play the game with the graphical interface.

```bash
python run_gui.py
# or
python main.py
```

### Main Game (CLI Mode)

Run the game purely in your terminal.

```bash
python main.py --cli
```

### World Configurator

Run the tool to edit game world data.

```bash
python world_configurator/main.py
```

### Web Interface

Start the FastAPI web server. By default, it runs on `http://localhost:8000`.

```bash
# Ensure you are in the project root directory
uvicorn web.server.server:app --reload --port 8000
```
*Alternatively, you might be able to use `python start_server.py` if it's configured.*

### Running Tests

Navigate to the `tests` directory and use `pytest` (you might need to install it: `pip install pytest`).

```bash
cd tests
pytest
# Or from the root directory:
python -m pytest tests/
```
Refer to `tests/README.md` for more details on testing.

## Configuration

Game settings, LLM API keys, item definitions, and world data are managed through JSON files in the `config/` directory. The LLM settings can also be managed through the GUI or potentially the web interface.

## Development Status

See `checklist.md` for the current development status, planned features, and roadmap.

## License

This project is intended for personal use and learning purposes.
