#!/usr/bin/env python3
"""
Clean and reconstruct the Casio Retro LCD dial background (elem_00_image_00.png).
Completely removes sloppy patchwork rectangles, jagged top notches, ghost pixels,
and restores the smooth, uniform inner bezel shadow and pristine LCD surface.
"""

import os
import shutil
from PIL import Image, ImageDraw

BG_PATH = "custom_watchfaces/03_casio_retro_lcd/images/elem_00_image_00.png"
BACKUP_PATH = "custom_watchfaces/03_casio_retro_lcd/images/elem_00_image_00_backup.png"


def clean_background():
    if not os.path.exists(BACKUP_PATH):
        shutil.copyfile(BG_PATH, BACKUP_PATH)
        print(f"[+] Backup created at {BACKUP_PATH}")

    im = Image.open(BG_PATH).convert("RGBA")
    draw = ImageDraw.Draw(im)

    # 1. Capture pristine vertical inner bezel shadow profile from x=200
    # y=153 to 170 (groove down into LCD surface)
    grad = [im.getpixel((200, y)) for y in range(153, 171)]

    # 2. Reconstruct top shadow across entire width of upper LCD pane (x=92 to 380)
    for x in range(92, 381):
        for idx, y in enumerate(range(153, 171)):
            im.putpixel((x, y), grad[idx])

    # Left corner transition (x=88..91)
    for step, x in enumerate(range(88, 92)):
        factor = (step + 1) / 5.0
        for idx, y in enumerate(range(153, 171)):
            orig = im.getpixel((x, y))
            target = grad[idx]
            blended = tuple(int(orig[c] * (1 - factor) + target[c] * factor) for c in range(4))
            im.putpixel((x, y), blended)

    # Right corner transition (x=381..384)
    for step, x in enumerate(range(381, 385)):
        factor = (4 - step) / 5.0
        for idx, y in enumerate(range(153, 171)):
            orig = im.getpixel((x, y))
            target = grad[idx]
            blended = tuple(int(orig[c] * (1 - factor) + target[c] * factor) for c in range(4))
            im.putpixel((x, y), blended)

    # 3. Clean the LCD panel body (y=171 to 205, x=92 to 380)
    # Wipes all ghost segment artifacts, stray tick marks, and rectangular patches
    lcd_color = (216, 218, 213, 255)
    draw.rectangle([92, 171, 380, 205], fill=lcd_color)

    # 4. Re-draw clean Double Dash '--' between day name and date
    dash_color = (24, 30, 24, 255)
    draw.rectangle([262, 178, 267, 180], fill=dash_color)
    draw.rectangle([271, 176, 276, 178], fill=dash_color)  # Slight Casio offset or parallel
    # Make both parallel at 178..180 for classic LCD look
    draw.rectangle([262, 178, 267, 180], fill=dash_color)
    draw.rectangle([271, 178, 276, 180], fill=dash_color)

    # 5. Re-draw solid crisp Heart Icon '♥' at x=108..122, y=171..183
    heart_pts = [
        (114, 183), (108, 178), (107, 174), (109, 171), (112, 171),
        (114, 174), (116, 171), (119, 171), (121, 174), (120, 178), (114, 183)
    ]
    draw.polygon(heart_pts, fill=dash_color)
    draw.ellipse([107, 171, 113, 176], fill=dash_color)
    draw.ellipse([115, 171, 121, 176], fill=dash_color)

    im.save(BG_PATH)
    print(f"[+] Pristine Casio background saved to {BG_PATH}")


if __name__ == "__main__":
    clean_background()
