#!/usr/bin/env python3
"""
Create color swatches for the style settings.
"""

import os
from PIL import Image

# Create the colors directory if it doesn't exist
os.makedirs(os.path.join("images", "gui", "colors"), exist_ok=True)

# Define colors (name, hex)
colors = [
    ("light-brown", "#D2B48C"),  # Light brown (default)
    ("dark-brown", "#8B4513"),   # Dark brown
    ("beige", "#F5F5DC"),        # Beige
    ("cream", "#FFFDD0"),        # Cream
    ("tan", "#D2B48C"),          # Tan
    ("ivory", "#FFFFF0"),        # Ivory
    ("light-gray", "#D3D3D3"),   # Light gray
    ("light-blue", "#ADD8E6"),   # Light blue
    ("light-green", "#90EE90"),  # Light green
    ("light-red", "#FFCCCB"),    # Light red
]

# Define system message colors
system_colors = [
    ("red", "#FF0000"),          # Red (default for system)
    ("orange", "#FFA500"),       # Orange (current)
    ("yellow", "#FFFF00"),       # Yellow
    ("green", "#00FF00"),        # Green
    ("blue", "#0000FF"),         # Blue
    ("purple", "#800080"),       # Purple
    ("pink", "#FFC0CB"),         # Pink
    ("black", "#000000"),        # Black
]

# Create color swatches
for name, hex_code in colors:
    # Convert hex to RGB
    hex_code = hex_code.lstrip('#')
    rgb = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
    
    # Create image
    img = Image.new('RGB', (50, 30), rgb)
    
    # Save image
    img_path = os.path.join("images", "gui", "colors", f"{name}.png")
    img.save(img_path)
    print(f"Created {img_path}")

# Create system message color swatches
for name, hex_code in system_colors:
    # Convert hex to RGB
    hex_code = hex_code.lstrip('#')
    rgb = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
    
    # Create image
    img = Image.new('RGB', (50, 30), rgb)
    
    # Save image
    img_path = os.path.join("images", "gui", "colors", f"system_{name}.png")
    img.save(img_path)
    print(f"Created {img_path}")

print("All color swatches created successfully!")
