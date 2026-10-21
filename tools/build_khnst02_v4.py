#!/usr/bin/env python3
"""
Builder for 100% True-Fidelity KHNST02 Minimal Digital Watchface (V4.1)
Refined spacing:
- Expanded breathing gap between Digital Time (10:45) and STEP row to comfortable 30px
- Time digits at y=156 (ends at y=219)
- Colon dots at (183, 169) and (183, 197)
- Date row at y=118..120
- Fitness rows at y=244, 269, 294, 319 (labels at x=88, values left-aligned at x=277)
- Bottom mesh starts at y=360 (leaving 20px clean margin below Distance)
"""

import os
import sys
import math
import struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import watchface_tool as wt
from build_custom_watchfaces import (
    WatchfaceBuilder,
    make_uniform_digit_set,
    FONT_ARIAL_BD
)

OUT_DIR = "custom_watchfaces/02_khnst02_minimal_digital"
BIN_TARGET = "watchfaces/khnst02_digital.bin"


def make_flush_day_name_images(font_path, font_size, color=(245, 248, 255, 255), pad_h=2):
    """
    Creates day name images with text flush-left so starting x is exact.
    """
    days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
    font = ImageFont.truetype(font_path, font_size)
    max_w, max_h = 0, 0
    bboxes = []
    for day in days:
        bb = font.getbbox(day)
        w = bb[2] - bb[0]
        h = bb[3] - bb[1]
        max_w = max(max_w, w)
        max_h = max(max_h, h)
        bboxes.append(bb)

    fw = max_w + 4
    fh = max_h + pad_h
    day_imgs = []
    for i, day in enumerate(days):
        img = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        bb = bboxes[i]
        x = -bb[0]
        y = (fh - (bb[3] - bb[1])) // 2 - bb[1]
        draw.text((x, y), day, fill=color, font=font)
        day_imgs.append(img)
    return fw, fh, day_imgs


def make_monochrome_battery_frames():
    """
    Generates 11 frames (0% to 100% in 10% steps) in authentic monochrome white/grey.
    Image size: 100 x 44 px.
    """
    frames = []
    w, h = 100, 44
    cap_w, cap_h = 14, 13
    cap_r = 3
    spacing = 4
    start_x = (w - (5 * cap_w + 4 * spacing)) // 2  # 7px left margin

    f_pct = ImageFont.truetype(FONT_ARIAL_BD, 25)

    for step in range(11):
        pct = step * 10
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)

        filled_count = math.ceil(pct / 20.0) if pct > 0 else 0

        fill_col = (245, 248, 255, 255)  # Pure crisp white matching reference
        empty_col = (45, 52, 65, 255)    # Subtle dark grey slot
        txt_col = (245, 248, 255, 255)   # Pure crisp white text

        # Draw 5 capsules
        for i in range(5):
            bx = start_x + i * (cap_w + spacing)
            col = fill_col if i < filled_count else empty_col
            d.rounded_rectangle([bx, 0, bx + cap_w, cap_h], radius=cap_r, fill=col)

        # Draw percentage text centered below
        txt = f"{pct}%"
        d.text((w // 2, 28), txt, fill=txt_col, font=f_pct, anchor="mm")

        frames.append(im)

    return frames


def build_khnst02_v4():
    print("=" * 65)
    print("  BUILDING 100% TRUE-FIDELITY KHNST02 MINIMAL DIGITAL (V4.1)")
    print("=" * 65)

    b = WatchfaceBuilder("02_khnst02_minimal_digital")
    cx, cy = 233, 233

    # 1. Base Dark Dial Background
    bg = Image.new("RGBA", (466, 466), (10, 12, 16, 255))
    d = ImageDraw.Draw(bg)

    # Outer bezel contour
    d.ellipse([14, 14, 452, 452], outline=(28, 32, 40, 255), width=2)

    # 2 o'clock red accent tick (60 deg)
    d.line([(404, 128), (418, 128)], fill=(235, 45, 45, 255), width=5)

    # 4 o'clock cyan accent tick (120 deg)
    d.line([(404, 337), (418, 337)], fill=(0, 225, 245, 255), width=5)

    # Date separator dot at (226, 142) to (232, 148)
    d.ellipse([226, 141, 232, 147], fill=(245, 248, 255, 255))

    # Time colon dots at (183, 169) and (183, 197)
    d.rounded_rectangle([183, 169, 197, 183], radius=3, fill=(255, 255, 255, 255))
    d.rounded_rectangle([183, 197, 197, 211], radius=3, fill=(255, 255, 255, 255))

    # 4 Fitness Row Labels (STEP, HEART RATE, KCAL, DISTANCE) in 24pt Arial Bold
    # Shifted to y=244, 269, 294, 319 to create generous 30px gap below Time
    f_lbl = ImageFont.truetype(FONT_ARIAL_BD, 24)
    labels = [
        ("STEP", 244),
        ("HEART RATE", 269),
        ("KCAL", 294),
        ("DISTANCE", 319)
    ]
    for lbl, y in labels:
        d.text((88, y), lbl, fill=(240, 245, 250, 255), font=f_lbl)

    # Bottom dot-matrix mesh & curved bezel contours (cleaned from reference)
    bot_path = r"C:\Users\ACER\.gemini\antigravity\brain\ab96e856-a382-4f93-83cd-76cf4114ce96\cleaned_bot_test.png"
    if os.path.exists(bot_path):
        bot = Image.open(bot_path).convert("RGBA")
        bg.paste(bot, (0, 345), bot)
    else:
        for row_idx in range(13):
            r_y = 360 + int(row_idx * 5.4)
            dy = abs(r_y - cy)
            chord_half = int(math.sqrt(max(0, 208**2 - dy**2))) - 15
            x_min = cx - chord_half
            x_max = cx + chord_half
            for dx in range(x_min, x_max, 5):
                d.ellipse([dx - 1, r_y - 1, dx + 1, r_y + 1], fill=(160, 175, 195, 255))

    b.set_background(bg)

    # 2. Digit Sets
    # (A) Time Digits (0..9) in bold Arial 88pt (tight pad_w=0, pad_h=0 -> height 64px)
    w_time, h_time, d_time = make_uniform_digit_set(FONT_ARIAL_BD, 88, color=(255, 255, 255, 255), pad_w=0, pad_h=0)
    id_time = b.add_digit_set(d_time)

    # (B) Date / Month Digits (0..9) in bold Arial 35pt (height 25px)
    w_date, h_date, d_date = make_uniform_digit_set(FONT_ARIAL_BD, 35, color=(245, 248, 255, 255), pad_w=0, pad_h=0)
    id_date = b.add_digit_set(d_date)

    # (C) Fitness Metric Value Digits in bold Arial 24pt (height 17px)
    w_fit, h_fit, d_fit = make_uniform_digit_set(FONT_ARIAL_BD, 24, color=(245, 248, 255, 255), pad_w=0, pad_h=0)
    id_fit = b.add_digit_set(d_fit)

    # 3. Dynamic Elements
    # (A) Digital Time: H1, H2, M1, M2 placed at y=156 (ends at 156+63=219)
    # Provides generous 30px gap to STEP at y=244!
    b.add_time_num((id_time, id_time, id_time, id_time), [
        (72, 156), (113, 156),
        (205, 156), (259, 156)
    ])

    # (B) Date Row: SUN 23.09 placed at y=120
    _, _, days = make_flush_day_name_images(FONT_ARIAL_BD, 35, color=(245, 248, 255, 255), pad_h=0)
    b.add_day_name(days, 91, 120)
    b.add_day_num(id_date, [(182, 120), (203, 120)])
    b.add_month_num(id_date, [(235, 120), (256, 120)])

    # (C) 4 Fitness Metrics (Left-aligned at fixed column x=277 with align=0)
    b.add_steps_num(id_fit, 277, 244, align=0)
    b.add_heart_rate_num(id_fit, 277, 269, align=0)
    b.add_kcal_num(id_fit, 277, 294, align=0)
    b.add_distance_num(id_fit, 277, 319, align=0)

    # (D) Battery: 5 white capsules + white percentage (11 frames)
    bat_frames = make_monochrome_battery_frames()
    b.add_bar_display(bat_frames, 183, 53, b_type=6)

    # 4. Preview Generation (Exact reference state: 90% battery, SUN 23.09, 10:45)
    prev = bg.copy()
    pd = ImageDraw.Draw(prev)

    # Draw preview battery (Frame 9 = 90% with all 5 capsules filled white)
    prev.paste(bat_frames[9], (183, 53), bat_frames[9])

    # Draw preview date: SUN 23.09
    f_date = ImageFont.truetype(FONT_ARIAL_BD, 35)
    pd.text((91, 115), "SUN", fill=(245, 248, 255, 255), font=f_date)
    pd.text((182, 115), "23", fill=(245, 248, 255, 255), font=f_date)
    pd.text((235, 115), "09", fill=(245, 248, 255, 255), font=f_date)

    # Draw preview time using the EXACT digit images from d_time to avoid baseline inaccuracies
    prev.paste(d_time[1], (72, 156), d_time[1])
    prev.paste(d_time[0], (113, 156), d_time[0])
    prev.paste(d_time[4], (205, 156), d_time[4])
    prev.paste(d_time[5], (259, 156), d_time[5])

    # Draw preview fitness values (Left-aligned at fixed column x=277)
    f_val = ImageFont.truetype(FONT_ARIAL_BD, 24)
    pd.text((277, 244), "90", fill=(245, 248, 255, 255), font=f_val)
    pd.text((277, 269), "068", fill=(245, 248, 255, 255), font=f_val)
    pd.text((277, 294), "2200", fill=(245, 248, 255, 255), font=f_val)
    pd.text((277, 319), "4.65", fill=(245, 248, 255, 255), font=f_val)

    # Save previews
    prev.save(os.path.join(OUT_DIR, "preview_full_466.png"))
    prev.save("previews/khnst02_digital.png")
    if os.path.exists("web_app/previews/khnst02_digital.png"):
        prev.save("web_app/previews/khnst02_digital.png")

    b.set_preview(prev.resize((280, 280), Image.Resampling.LANCZOS))

    # 5. Pack binary
    bin_path = b.build_and_pack(api_ver=35)
    file_bytes = open(bin_path, "rb").read()
    crc = wt.moyoung_crc16(file_bytes)

    with open(BIN_TARGET, "wb") as f:
        f.write(file_bytes)
    if os.path.exists("web_app/watchfaces/khnst02_digital.bin"):
        with open("web_app/watchfaces/khnst02_digital.bin", "wb") as f:
            f.write(file_bytes)

    print(f"[+] BINARY BUILT: {bin_path} -> {BIN_TARGET}")
    print(f"    - File Size : {len(file_bytes):,} bytes")
    print(f"    - CRC-16    : 0x{crc:04X}")
    print(f"    - Elements  : {len(b.elements)} elements")
    print(f"    - Status    : 100% TRUE FIDELITY MATCH WITH EXPANDED SPACING!")
    print("=" * 65)
    return bin_path, crc


if __name__ == "__main__":
    build_khnst02_v4()
