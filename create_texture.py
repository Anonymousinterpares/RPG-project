#!/usr/bin/env python3
"""
Create a subtle texture image for the game output background.
"""

from PIL import Image, ImageDraw
import random
import os

# Size of the texture tile
width, height = 200, 200

# Create a transparent image
img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
draw = ImageDraw.Draw(img)

# Add subtle noise dots
for _ in range(500):
    x = random.randint(0, width - 1)
    y = random.randint(0, height - 1)
    size = random.randint(1, 2)
    # Use semi-transparent dots
    alpha = random.randint(10, 40)
    color = (0, 0, 0, alpha)
    draw.ellipse((x, y, x + size, y + size), fill=color)

# Add some subtle lines for texture
for _ in range(20):
    x1 = random.randint(0, width - 1)
    y1 = random.randint(0, height - 1)
    x2 = x1 + random.randint(-50, 50)
    y2 = y1 + random.randint(-50, 50)
    # Very subtle lines
    alpha = random.randint(5, 15)
    color = (0, 0, 0, alpha)
    draw.line((x1, y1, x2, y2), fill=color, width=1)

# Ensure the directory exists
os.makedirs(os.path.join("images", "gui"), exist_ok=True)

# Save the texture
output_path = os.path.join("images", "gui", "output_texture.png")
img.save(output_path)

print(f"Created texture at {output_path}")
