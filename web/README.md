# Web Module

The `web` module provides a web-based interface for interacting with the RPG game. It allows users to play the game through a standard web browser, offering an alternative to the desktop GUI.

## Architecture

The web interface follows a client-server architecture:

*   **Server (`server/`)**: A Python backend built with the **FastAPI** framework and served using **Uvicorn**. It handles game logic by interacting with the `core` module, manages game sessions, processes player commands, handles saving/loading, manages LLM settings, and provides real-time updates via **WebSockets**.
*   **Client (`client/`)**: A standard frontend built with **HTML**, **CSS**, and **JavaScript**. It communicates with the server via REST API calls for actions and WebSockets for receiving real-time game state updates.

## Key Features & Functionality

*   **Game Interaction**: Start new games, process player commands, and receive game world updates.
*   **Real-time Updates**: Uses WebSockets to push game state changes (player stats, location, game time, messages) to the client in real-time.
*   **Session Management**: Creates and manages unique game sessions for each connected client.
*   **Save/Load**: API endpoints to save the current game state and load previous saves.
*   **LLM Integration**: API endpoints to view and manage LLM provider and agent settings, and toggle LLM functionality per session (interacts with `core.llm.settings_manager`).
*   **Character Creation**: Basic character details (name, race, path, etc.) can be provided when starting a new game. Includes support for selecting character icons.
*   **Static File Serving**: Serves the client-side HTML, CSS, JS files, and images (including character icons from `images/character_icons`).

## Technologies Used

*   **Backend**:
    *   Python 3
    *   FastAPI (Web framework)
    *   Uvicorn (ASGI server)
    *   WebSockets (Real-time communication)
    *   Pydantic (Data validation)
*   **Frontend**:
    *   HTML5
    *   CSS3
    *   JavaScript (Vanilla)

## Setup and Running

1.  **Install Dependencies**: Navigate to the `web/server/` directory and install the required Python packages:
    ```bash
    cd web/server
    pip install -r requirements.txt
    cd ../.. 
    ```
    *(Ensure you are in the project root or have the `core` module accessible in your Python path, as the server imports from it).*

2.  **Run the Server**: From the project root directory (`new project/`), run the server using Uvicorn:
    ```bash
    python web/server/server.py 
    ```
    Alternatively, run Uvicorn directly (also from the project root):
    ```bash
    uvicorn web.server.server:app --reload --host 0.0.0.0 --port 8000
    ```

3.  **Access the Interface**: Open your web browser and navigate to `http://localhost:8000`.

## Interaction with Other Modules

*   **`core/`**: The server heavily relies on the `core` module. It imports and uses:
    *   `core.base.engine.GameEngine`: To manage the main game loop and state.
    *   `core.base.state`: For game state representation.
    *   `core.base.commands`: To process commands.
    *   `core.utils.logging_config`: For logging.
    *   `core.llm.settings_manager`: To manage LLM configurations.
    *   `core.utils.save_manager`: To handle game saving and loading metadata.
*   **`images/`**: The server mounts the `images/` directory (specifically `images/character_icons/`) to serve character portraits to the client.
*   **`config/`**: Indirectly uses configuration files loaded by the `core` module.

## Dependencies

Key Python dependencies (see `web/server/requirements.txt` for full list):
*   `fastapi`
*   `uvicorn`
*   `websockets`
*   `pydantic`
*   `python-dotenv`
