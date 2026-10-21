#!/usr/bin/env python3
"""
Generates the comprehensive 3-way visual comparison:
1. Foto Referensi Asli (cropped from screenshot)
2. WF Terdahulu (V3: font kecil, nilai fitness di kanan, bawah hanya 3 baris)
3. WF Terbaru (V4: font 100% persis, susunan x=277, bawah full dot-matrix mesh 12 baris)
Plus 5 high-resolution zoomed section comparisons.
"""

import os
from PIL import Image, ImageDraw, ImageFont

BRAIN_DIR = r"C:\Users\ACER\.gemini\antigravity\brain\ab96e856-a382-4f93-83cd-76cf4114ce96"
FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"
FONT_TITLE = ImageFont.truetype(FONT_PATH, 28)
FONT_SUB = ImageFont.truetype(FONT_PATH, 18)
FONT_ZOOM = ImageFont.truetype(FONT_PATH, 16)

# Load images (all 466x466)
im_ref = Image.open(os.path.join(BRAIN_DIR, "khnst02_ref_466.png")).convert("RGB")
im_prev = Image.open("scratch_v3_wf.png").convert("RGB")
im_new = Image.open("previews/khnst02_digital.png").convert("RGB")

w, h = 466, 466
pad = 30
header_h = 100
dials_h = h + 60
zoom_h = 240
total_w = pad * 4 + w * 3
total_h = header_h + dials_h + zoom_h * 5 + 80

comp = Image.new("RGB", (total_w, total_h), (12, 15, 20))
d = ImageDraw.Draw(comp)

# Main Title Header
d.text((total_w // 2, 40), "PERBANDINGAN VISUAL 100% KHNST02 MINIMAL DIGITAL", fill=(255, 255, 255), font=FONT_TITLE, anchor="mm")
d.text((total_w // 2, 75), "Bozlun B71 (AMOLED 466x466) | Evaluasi Forensik Piksel Presisi Tinggi", fill=(160, 175, 195), font=FONT_SUB, anchor="mm")

# 3 Main Dials
columns = [
    ("1. 📷 FOTO REFERENSI ASLI", "(Crop Asli Screenshot B71)", (0, 220, 255), im_ref),
    ("2. ⚠️ WF TERDAHULU (V3)", "(Font kecil, nilai di kanan, bawah 3 baris)", (255, 120, 100), im_prev),
    ("3. ✨ WF TERBARU (V4 - 100% PERSIS)", "(Font 88/35/24pt, x=277, bawah mesh 12 baris)", (100, 255, 150), im_new)
]

for i, (title, sub, color, img) in enumerate(columns):
    x = pad + i * (w + pad)
    y = header_h + 10
    d.text((x + w // 2, y), title, fill=color, font=FONT_SUB, anchor="mm")
    d.text((x + w // 2, y + 25), sub, fill=(180, 190, 205), font=FONT_ZOOM, anchor="mm")
    comp.paste(img, (x, y + 45))
    # Outer border
    d.rectangle([x - 2, y + 43, x + w + 1, y + 45 + h + 1], outline=color, width=2)

# 5 Zoomed Slices Comparison
zooms = [
    ("BATTERY & PERSENTASE (Top Bezel)", (160, 50, 310, 105), "Monokrom 5 kapsul putih (14x13px) + persentase 90% (25pt) presisi di tengah"),
    ("TANGGAL & HARI (SUN 23.09)", (80, 115, 290, 158), "Font 35pt Arial Bold persis (26px height), 'SUN' rata kiri x=91, titik pemisah x=226"),
    ("JAM DIGITAL (10:45)", (70, 155, 320, 235), "Font 88pt Arial Bold persis (64px height), titik dua ':' presisi x=183"),
    ("FITNESS DATA ROWS (Step, HR, KCal, Dist)", (75, 230, 350, 340), "Font 24pt Arial Bold persis (20px height), semua nilai rata kiri di kolom tetap x=277!"),
    ("BOTTOM DOT-MATRIX MESH", (40, 350, 426, 460), "Mesh melengkung rapat 12 baris (dx=5, dy=5.5) + kontur bezel + arc aksen bawah")
]

start_zoom_y = header_h + dials_h + 20

for z_idx, (z_title, crop_box, z_desc) in enumerate(zooms):
    zy = start_zoom_y + z_idx * zoom_h
    # Section Header
    d.rectangle([pad, zy, total_w - pad, zy + 30], fill=(22, 28, 38))
    d.text((pad + 15, zy + 15), f"ZOOM {z_idx+1}: {z_title}", fill=(255, 215, 0), font=FONT_ZOOM, anchor="lm")
    d.text((total_w - pad - 15, zy + 15), z_desc, fill=(180, 200, 225), font=FONT_ZOOM, anchor="rm")

    cw = crop_box[2] - crop_box[0]
    ch = crop_box[3] - crop_box[1]
    slice_w = w
    slice_h = zoom_h - 45

    for i, (_, _, color, img) in enumerate(columns):
        x = pad + i * (w + pad)
        slice_crop = img.crop(crop_box)
        # Resize to fit slot with aspect ratio preserved
        aspect = cw / ch
        target_h = slice_h
        target_w = int(target_h * aspect)
        if target_w > slice_w:
            target_w = slice_w
            target_h = int(target_w / aspect)
        resized_slice = slice_crop.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        # Center in column slot
        off_x = x + (slice_w - target_w) // 2
        off_y = zy + 35 + (slice_h - target_h) // 2
        comp.paste(resized_slice, (off_x, off_y))
        d.rectangle([off_x - 1, off_y - 1, off_x + target_w, off_y + target_h], outline=color, width=1)

output_path = os.path.join(BRAIN_DIR, "khnst02_true_comparison_3way.png")
comp.save(output_path)
print(f"[+] Saved 3-way visual comparison -> {output_path}")
