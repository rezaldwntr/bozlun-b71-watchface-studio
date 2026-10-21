#!/usr/bin/env python3
"""
Builder for Casio Retro LCD Watchface (V2 - Dynamic 12/24H & AM/PM)
1. Removes the static frozen '00' digits from the bottom right of the LCD panel.
2. Implements authentic Casio 12H / 24H switching:
   - In 24-Hour mode: '24 H' indicator is visible on the LCD.
   - In 12-Hour mode: Dynamic AM/PM (Element Type 17) covers '24 H' and displays 'AM' or 'PM'!
3. Retains all authentic Casio photorealistic bezels, buttons, mineral glass reflections,
   and 7-segment LCD digits for Time, Date, Month, Day, Steps, Heart Rate, and Battery.
"""

import os
import sys
import struct
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import watchface_tool as wt
from build_custom_watchfaces import (
    WatchfaceBuilder,
    FONT_ARIAL_BD,
    FONT_BAHNSCHRIFT
)

CASIO_IMG_DIR = "custom_watchfaces/03_casio_retro_lcd/images"
OUT_BIN_LOCAL = "custom_watchfaces/03_casio_retro_lcd/03_casio_retro_lcd.bin"
OUT_BIN_MAIN = "watchfaces/casio_retro.bin"
OUT_BIN_WEB = "web_app/watchfaces/casio_retro.bin"
PREV_MAIN = "previews/casio_retro.png"
PREV_WEB = "web_app/previews/casio_retro.png"


def clean_casio_background():
    """
    Cleans the background image:
    - Erases the static '00' digits at x=316..370, y=220..265.
    - Draws clean, crisp '24 H' text at x=330, y=209.
    """
    bg_path = os.path.join(CASIO_IMG_DIR, "elem_00_image_00.png")
    backup_path = os.path.join(CASIO_IMG_DIR, "elem_00_image_00_orig.png")
    if not os.path.exists(backup_path):
        import shutil
        shutil.copyfile(bg_path, backup_path)

    bg = Image.open(bg_path).convert("RGBA")
    d = ImageDraw.Draw(bg)
    lcd_col = (216, 218, 213, 255)

    # 1. Clean the static '00' area completely
    d.rectangle([316, 220, 370, 265], fill=lcd_col)

    # 2. Clean and redraw crisp '24 H' text
    d.rectangle([315, 202, 345, 216], fill=lcd_col)
    f_24h = ImageFont.truetype(FONT_BAHNSCHRIFT, 11)
    txt_col = (24, 34, 24, 255)
    d.text((330, 209), "24 H", fill=txt_col, font=f_24h, anchor="mm")

    bg.save(bg_path)
    return bg


def make_casio_ampm_images():
    """
    Creates dynamic AM and PM images (36x16 px) with opaque LCD background.
    When 12-hour mode is active, they cleanly cover '24 H' and display 'AM' or 'PM'.
    When 24-hour mode is active, the smartwatch hides them, revealing '24 H'.
    """
    w, h = 36, 16
    lcd_col = (216, 218, 213, 255)
    txt_col = (24, 34, 24, 255)
    f_ampm = ImageFont.truetype(FONT_BAHNSCHRIFT, 12)

    im_am = Image.new("RGBA", (w, h), lcd_col)
    d_am = ImageDraw.Draw(im_am)
    d_am.text((w // 2, h // 2), "AM", fill=txt_col, font=f_ampm, anchor="mm")

    im_pm = Image.new("RGBA", (w, h), lcd_col)
    d_pm = ImageDraw.Draw(im_pm)
    d_pm.text((w // 2, h // 2), "PM", fill=txt_col, font=f_ampm, anchor="mm")

    return im_am, im_pm


def build_casio_v2():
    print("=" * 65)
    print("  BUILDING CASIO RETRO LCD V2 (DYNAMIC 12/24H & AM/PM)")
    print("=" * 65)

    b = WatchfaceBuilder("03_casio_retro_lcd")

    # 1. Background Image
    bg = clean_casio_background()
    b.set_background(bg)

    # 2. Load existing 7-segment digit sets
    # Digit Set 0: Big Time Digits (0..9, 36x68)
    d_time = []
    for g in range(10):
        d_time.append(Image.open(os.path.join(CASIO_IMG_DIR, f"digits_00_{g}.png")))
    id_time = b.add_digit_set(d_time)

    # Digit Set 1: Date/Month/HR Small Digits (0..9, 14x26)
    d_small = []
    for g in range(10):
        d_small.append(Image.open(os.path.join(CASIO_IMG_DIR, f"digits_01_{g}.png")))
    id_small = b.add_digit_set(d_small)

    # Digit Set 2: White Steps Digits (0..9, 14x26)
    d_steps = []
    for g in range(10):
        d_steps.append(Image.open(os.path.join(CASIO_IMG_DIR, f"digits_02_{g}.png")))
    id_steps = b.add_digit_set(d_steps)

    # 3. Dynamic Elements
    # (A) Time Digits (10:08)
    b.add_time_num((id_time, id_time, id_time, id_time), [
        (110, 232), (152, 232),
        (216, 232), (258, 232)
    ])

    # (B) Day Name (Mon..Sun)
    days = []
    for g in range(7):
        days.append(Image.open(os.path.join(CASIO_IMG_DIR, f"elem_02_day_name_{g:02d}.png")))
    b.add_day_name(days, 216, 168)

    # (C) Day Number (DD)
    b.add_day_num(id_small, [(282, 168), (296, 168)], align=2)

    # (D) Month Number (MM)
    b.add_month_num(id_small, [(320, 168), (334, 168)], align=2)

    # (E) Heart Rate Number
    b.add_heart_rate_num(id_small, 126, 168, align=0)

    # (F) Steps Number (White LCD font)
    b.add_steps_num(id_steps, 126, 328, align=0)

    # (G) Battery Bar Display
    bars = []
    for g in range(11):
        bars.append(Image.open(os.path.join(CASIO_IMG_DIR, f"elem_07_bar_display_{g:02d}.png")))
    b.add_bar_display(bars, 334, 328, b_type=6)

    # (H) Dynamic AM/PM Element (Type 17) at (316, 202)
    im_am, im_pm = make_casio_ampm_images()
    b.add_ampm(im_am, im_pm, 316, 202)

    # 4. Preview Generation (24H state by default, clean no-seconds LCD)
    prev = bg.copy()
    prev.paste(d_time[1], (110, 232), d_time[1])
    prev.paste(d_time[0], (152, 232), d_time[0])
    prev.paste(d_time[0], (216, 232), d_time[0])
    prev.paste(d_time[8], (258, 232), d_time[8])
    prev.paste(days[5], (216, 168), days[5])
    prev.paste(d_small[2], (282, 168), d_small[2])
    prev.paste(d_small[1], (296, 168), d_small[1])
    prev.paste(d_small[1], (320, 168), d_small[1])
    prev.paste(d_small[0], (334, 168), d_small[0])
    prev.paste(d_small[7], (126, 168), d_small[7])
    prev.paste(d_small[8], (140, 168), d_small[8])
    prev.paste(d_steps[4], (126, 328), d_steps[4])
    prev.paste(d_steps[8], (140, 328), d_steps[8])
    prev.paste(d_steps[2], (154, 328), d_steps[2])
    prev.paste(d_steps[0], (168, 328), d_steps[0])
    prev.paste(bars[8], (334, 328), bars[8])

    b.set_preview(prev.resize((280, 280), Image.Resampling.LANCZOS))
    prev.save("custom_watchfaces/03_casio_retro_lcd/preview_full_466.png")
    prev.save(PREV_MAIN)
    if os.path.exists("web_app"):
        prev.save(PREV_WEB)

    # 5. Build and Pack
    bin_path = b.build_and_pack(api_ver=35)
    file_bytes = open(bin_path, "rb").read()
    crc = wt.moyoung_crc16(file_bytes)

    with open(OUT_BIN_MAIN, "wb") as f:
        f.write(file_bytes)
    if os.path.exists("web_app/watchfaces"):
        with open(OUT_BIN_WEB, "wb") as f:
            f.write(file_bytes)

    print(f"[+] CASIO RETRO LCD V2 BINARY BUILT: {bin_path} -> {OUT_BIN_MAIN}")
    print(f"    - File Size : {len(file_bytes):,} bytes")
    print(f"    - CRC-16    : 0x{crc:04X}")
    print(f"    - Elements  : {len(b.elements)} elements (Includes Dynamic AM/PM Type 17)")
    print("=" * 65)
    return bin_path, crc


if __name__ == "__main__":
    build_casio_v2()
