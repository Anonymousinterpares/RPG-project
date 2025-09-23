#!/usr/bin/env python3
"""
Startup script for the RPG game web server.
This ensures proper module imports by adding the project root to the Python path.
"""

import os
import sys
import subprocess
import importlib.util
import webbrowser

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Check if required packages are installed
def check_dependencies():
    """Check if the required dependencies are installed."""
    requirements_file = os.path.join(project_root, 'web', 'server', 'requirements.txt')
    
    if not os.path.exists(requirements_file):
        print("Warning: requirements.txt not found at", requirements_file)
        return True
    
    with open(requirements_file, 'r') as f:
        requirements = f.read().splitlines()
    
    missing_packages = []
    for req in requirements:
        if req and not req.startswith('#'):
            # Extract package name before version specifier
            package_name = req.split('>=')[0].split('==')[0].split('[')[0].strip()
            if not importlib.util.find_spec(package_name):
                missing_packages.append(req)
    
    if missing_packages:
        print("Missing dependencies found. Installing required packages...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("Dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            print("Please run: pip install -r web/server/requirements.txt")
            return False
    
    return True

def start_server():
    """Start the FastAPI server."""
    if not check_dependencies():
        return
    
    try:
        # Import necessary modules
        try:
            # Check core modules can be imported
            from core.base.engine import GameEngine
            print("Core modules imported successfully.")
        except ImportError as e:
            print(f"Error importing core modules: {e}")
            print("Make sure the project structure is correct and __init__.py files exist in all package directories.")
            return
        
        # Launch server
        server_script = os.path.join(project_root, 'web', 'server', 'server.py')
        if not os.path.exists(server_script):
            print(f"Error: Server script not found at {server_script}")
            return
        
        print("\nStarting the web server...")
        print("=" * 50)
        print("The server will be available at: http://localhost:8000")
        print("API documentation at: http://localhost:8000/docs")
        print("=" * 50)
        print("Press Ctrl+C to stop the server.")

        # Try to open the browser automatically
        try:
            webbrowser.open("http://localhost:8000")
        except Exception:
            pass
        
        try:
            # Run the server script as a module using subprocess
            # This ensures proper module imports and variable scope
            subprocess.run([sys.executable, server_script], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running server script: {e}")
        
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"Error starting server: {e}")

if __name__ == "__main__":
    start_server()