from setuptools import setup, find_packages

setup(
    name="world_configurator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PySide6",
    ],
    entry_points={
        "console_scripts": [
            "world-configurator=world_configurator.main:main",
        ],
    },
)
