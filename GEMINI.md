# RPG Text Adventure Game

## Project Overview

This project is a text-based RPG adventure game framework that combines traditional role-playing elements with modern LLM (Large Language Model) technology. The goal is to create dynamic narratives, interactive characters, and an immersive game world generated and managed with the help of AI.

The project is a Python-based RPG with a core engine, a PySide6 GUI for playing, a PySide6 GUI for world editing, and a FastAPI web interface.

## Building and Running

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

### Running Tests

Navigate to the `tests` directory and use `pytest`.

```bash
cd tests
pytest
# Or from the root directory:
python -m pytest tests/
```

## Development Conventions

The project follows a modular design with separated components for core logic, UI, configuration, and LLM integration. The codebase is well-structured and includes README files in key directories, providing specific information about each component.
