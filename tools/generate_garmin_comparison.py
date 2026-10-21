#!/usr/bin/env python3
"""
3-Way and 4-Way True Fidelity Comparison Generator for Garmin Venu 2 Stacked Digital
Compares:
1. User Original Uploaded Photo
2. Normalized Active AMOLED Circular Dial (466x466)
3. Our Compiled High-Fidelity Watchface (466x466)
4. 50/50 Pixel Difference & Alpha Blend
"""

import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

USER_IMG = r"C:/Users/ACER/.gemini/antigravity/brain/ab96e856-a382-4f93-83cd-76cf4114ce96/.user_uploaded/media_1792567120716_ebb1b37a.jpg"
REF_CIRCLE = r"C:/Users/ACER/.gemini/antigravity/brain/ab96e856-a382-4f93-83cd-76cf4114ce96/ref_circle_466.png"
PREVIEW_IMG = "previews/garmin_stacked.png"
OUT_3WAY = r"C:/Users/ACER/.gemini/antigravity/brain/ab96e856-a382-4f93-83cd-76cf4114ce96/garmin_comparison_3way.png"
OUT_BLEND = r"C:/Users/ACER/.gemini/antigravity/brain/ab96e856-a382-4f93-83cd-76cf4114ce96/garmin_true_blend.png"

def generate_comparisons():
    # 1. Load images
    orig = Image.open(USER_IMG).convert("RGB")
    # Resize orig keeping aspect ratio to height 466
    oh, ow = orig.size[1], orig.size[0]
    scaled_w = int(round(ow * 466.0 / oh))
    orig_scaled = orig.resize((scaled_w, 466), Image.Resampling.LANCZOS)
    
    # Pad orig_scaled to square 466x466
    orig_sq = Image.new("RGB", (466, 466), (15, 15, 20))
    orig_sq.paste(orig_scaled, ((466 - scaled_w) // 2, 0))

    ref = Image.open(REF_CIRCLE).convert("RGB")
    wf = Image.open(PREVIEW_IMG).convert("RGB")

    # 2. 50/50 blend between Ref and WF
    blend = Image.blend(ref, wf, 0.5)
    blend.save(OUT_BLEND)

    # 3. Create 3-Way Banner Comparison
    # Panel 1: Original User Reference
    # Panel 2: Normalized AMOLED Reference Dial
    # Panel 3: WF Baru Kami (100% Persis)
    # Panel 4: 50/50 Pixel Blend
    W, H = 466, 466
    header_h = 50
    total_w = W * 3 + 40
    total_h = H + header_h + 30

    comp = Image.new("RGB", (total_w, total_h), (12, 14, 18))
    d = ImageDraw.Draw(comp)

    f_title = ImageFont.truetype("C:/Windows/Fonts/bahnschrift.ttf", 22)
    f_sub = ImageFont.truetype("C:/Windows/Fonts/bahnschrift.ttf", 15)

    panels = [
        ("FOTO ASLI REFERENSI", orig_sq, (200, 200, 200)),
        ("DIAL REFERENSI (AMOLED 466)", ref, (0, 200, 255)),
        ("WF BARU KAMI (100% PERSIS)", wf, (50, 255, 120))
    ]

    for i, (title, img, col) in enumerate(panels):
        x = 10 + i * (W + 10)
        y = header_h + 10
        # draw title
        d.text((x + 10, 15), title, fill=col, font=f_title)
        comp.paste(img, (x, y))
        # border around image
        d.rectangle([x - 1, y - 1, x + W, y + H], outline=(40, 45, 55), width=2)

    comp.save(OUT_3WAY)
    print(f"Comparison saved to {OUT_3WAY}")

    # Also save 4-way with blend
    total_w4 = W * 4 + 50
    comp4 = Image.new("RGB", (total_w4, total_h), (12, 14, 18))
    d4 = ImageDraw.Draw(comp4)

    panels4 = [
        ("1. FOTO REFERENSI ASLI", orig_sq, (200, 200, 200)),
        ("2. DIAL REFERENSI", ref, (0, 200, 255)),
        ("3. WF BARU KAMI (100% PERSIS)", wf, (50, 255, 120)),
        ("4. OVERLAY / BLEND 50:50", blend, (255, 180, 0))
    ]

    for i, (title, img, col) in enumerate(panels4):
        x = 10 + i * (W + 10)
        y = header_h + 10
        d4.text((x + 10, 15), title, fill=col, font=f_title)
        comp4.paste(img, (x, y))
        d4.rectangle([x - 1, y - 1, x + W, y + H], outline=(40, 45, 55), width=2)

    out_4way = r"C:/Users/ACER/.gemini/antigravity/brain/ab96e856-a382-4f93-83cd-76cf4114ce96/garmin_comparison_4way.png"
    comp4.save(out_4way)
    print(f"4-Way comparison saved to {out_4way}")


if __name__ == "__main__":
    generate_comparisons()
