# Tests Directory

This directory contains scripts designed to test various components and functionalities of the RPG project.

## Purpose

The primary goal of these tests is to ensure the correctness and reliability of the core game systems and modules. Currently, the focus is on verifying specific functionalities through dedicated test scripts.

## Testing Approach

Instead of using a standard testing framework like `unittest` or `pytest`, this project currently utilizes standalone Python scripts for testing specific modules. Each script typically focuses on a particular area of the codebase.

## Test Structure

Tests are organized as individual Python scripts within this directory. For example:
- `test_stats_system.py`: Tests the character statistics system (`core.stats`).

As more tests are added, they should follow this pattern, focusing on specific modules or features.

## Running Tests

To run a specific test, execute the corresponding Python script directly from the project's root directory:

```bash
python tests/test_stats_system.py
```

Ensure you are in the main project directory (`new project/`) when running the command, as the scripts might rely on relative paths for configuration or data files (e.g., `config/character/stats_config.json`).

## Writing New Tests

When adding new tests:
1.  Create a new Python script in the `tests/` directory (e.g., `test_inventory_system.py`).
2.  The script should import necessary modules from the `core/`, `gui/`, or other relevant directories. The existing `test_stats_system.py` includes boilerplate code to adjust `sys.path` which can be reused.
3.  Implement test functions or logic within the script to verify the desired functionality. Use assertions or print statements to indicate success or failure.
4.  Ensure the script can be run directly using `python tests/your_test_script.py` from the project root.

## Future Plans

- Expand test coverage to include all critical modules (inventory, combat, character creation, etc.).
- Potentially adopt a standard testing framework (like `pytest`) for better organization, discovery, and reporting.
- Implement integration tests, especially for UI components.
- Add performance benchmarks.
