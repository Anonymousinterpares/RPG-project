#!/usr/bin/env python3
"""
Create various texture images for the game output background.
"""

from PIL import Image, ImageDraw, ImageFilter
import random
import os
import math

# Create directory if it doesn't exist
texture_dir = os.path.join("images", "gui", "textures")
os.makedirs(texture_dir, exist_ok=True)

def create_noise_texture(name, width=800, height=800, density=2000, size_range=(1, 3), alpha_range=(10, 30)):
    """Create a basic noise texture with dots."""
    # Create a transparent image
    img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Add noise dots
    for _ in range(density):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        size = random.randint(size_range[0], size_range[1])
        # Use semi-transparent dots
        alpha = random.randint(alpha_range[0], alpha_range[1])
        color = (0, 0, 0, alpha)
        draw.ellipse((x, y, x + size, y + size), fill=color)
    
    # Save the texture
    output_path = os.path.join(texture_dir, f"{name}.png")
    img.save(output_path)
    print(f"Created {name} texture at {output_path}")
    return img

def create_parchment_texture(name, width=800, height=800):
    """Create a parchment-like texture."""
    # Start with a base cream color
    img = Image.new('RGBA', (width, height), (255, 248, 220, 255))
    draw = ImageDraw.Draw(img)
    
    # Add some random blotches
    for _ in range(200):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        radius = random.randint(10, 50)
        # Slightly darker or lighter than base
        variation = random.randint(-20, 20)
        r = max(0, min(255, 255 + variation))
        g = max(0, min(255, 248 + variation))
        b = max(0, min(255, 220 + variation))
        alpha = random.randint(20, 80)
        color = (r, g, b, alpha)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    
    # Add some "aging" lines
    for _ in range(40):
        x1 = random.randint(0, width - 1)
        y1 = random.randint(0, height - 1)
        length = random.randint(50, 200)
        angle = random.random() * 2 * math.pi
        x2 = int(x1 + length * math.cos(angle))
        y2 = int(y1 + length * math.sin(angle))
        # Brownish lines for aging effect
        color = (139, 69, 19, random.randint(10, 30))
        draw.line((x1, y1, x2, y2), fill=color, width=random.randint(1, 3))
    
    # Apply slight blur for a more natural look
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
    
    # Save the texture
    output_path = os.path.join(texture_dir, f"{name}.png")
    img.save(output_path)
    print(f"Created {name} texture at {output_path}")
    return img

def create_leather_texture(name, width=800, height=800):
    """Create a leather-like texture."""
    # Dark brown base
    img = Image.new('RGBA', (width, height), (101, 67, 33, 255))
    draw = ImageDraw.Draw(img)
    
    # Add a grid of slightly raised "grain" areas
    cell_size = 20
    for x in range(0, width, cell_size):
        for y in range(0, height, cell_size):
            if random.random() > 0.3:  # Skip some cells for variation
                cell_x = x + random.randint(0, cell_size // 2)
                cell_y = y + random.randint(0, cell_size // 2)
                cell_width = random.randint(cell_size // 2, cell_size)
                cell_height = random.randint(cell_size // 2, cell_size)
                
                # Lighter than base for "grain"
                variation = random.randint(10, 40)
                color = (min(255, 101 + variation), 
                         min(255, 67 + variation), 
                         min(255, 33 + variation), 
                         random.randint(100, 200))
                
                draw.ellipse(
                    (cell_x, cell_y, cell_x + cell_width, cell_y + cell_height),
                    fill=color
                )
    
    # Add some scratches
    for _ in range(50):
        x1 = random.randint(0, width - 1)
        y1 = random.randint(0, height - 1)
        length = random.randint(20, 100)
        angle = random.random() * 2 * math.pi
        x2 = int(x1 + length * math.cos(angle))
        y2 = int(y1 + length * math.sin(angle))
        # Lighter scratches
        color = (150, 120, 90, random.randint(30, 70))
        draw.line((x1, y1, x2, y2), fill=color, width=random.randint(1, 2))
    
    # Apply slight blur
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
    
    # Save the texture
    output_path = os.path.join(texture_dir, f"{name}.png")
    img.save(output_path)
    print(f"Created {name} texture at {output_path}")
    return img

def create_stone_texture(name, width=800, height=800):
    """Create a stone-like texture."""
    # Gray base
    img = Image.new('RGBA', (width, height), (180, 180, 180, 255))
    draw = ImageDraw.Draw(img)
    
    # Add stone "cells"
    cell_size = 60
    for x in range(0, width, cell_size):
        for y in range(0, height, cell_size):
            cell_width = random.randint(cell_size - 10, cell_size + 10)
            cell_height = random.randint(cell_size - 10, cell_size + 10)
            cell_x = x + random.randint(-5, 5)
            cell_y = y + random.randint(-5, 5)
            
            # Vary the gray
            gray_value = random.randint(150, 220)
            color = (gray_value, gray_value, gray_value, 255)
            
            draw.rectangle(
                (cell_x, cell_y, cell_x + cell_width, cell_y + cell_height),
                fill=color,
                outline=(100, 100, 100, 150),
                width=1
            )
    
    # Add some cracks
    for _ in range(30):
        x1 = random.randint(0, width - 1)
        y1 = random.randint(0, height - 1)
        points = [(x1, y1)]
        
        # Create a jagged line
        for i in range(random.randint(3, 8)):
            angle = random.random() * 2 * math.pi
            dist = random.randint(20, 60)
            x1 = int(x1 + dist * math.cos(angle))
            y1 = int(y1 + dist * math.sin(angle))
            points.append((x1, y1))
        
        # Draw the crack
        draw.line(points, fill=(60, 60, 60, random.randint(50, 150)), width=random.randint(1, 3))
    
    # Apply slight blur
    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
    
    # Save the texture
    output_path = os.path.join(texture_dir, f"{name}.png")
    img.save(output_path)
    print(f"Created {name} texture at {output_path}")
    return img

# Create a blank (no texture) image as fallback
img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
output_path = os.path.join(texture_dir, "none.png")
img.save(output_path)
print(f"Created blank texture at {output_path}")

# Create several textures for variety
create_noise_texture("subtle_noise")
create_parchment_texture("parchment")
create_leather_texture("leather")
create_stone_texture("stone")

# Create a smaller copy for the main GUI folder (for backward compatibility)
noise = create_noise_texture("output_texture", width=800, height=800)
output_path = os.path.join("images", "gui", "output_texture.png")
noise.save(output_path)
print(f"Created backward compatible texture at {output_path}")

print("All textures created successfully!")
