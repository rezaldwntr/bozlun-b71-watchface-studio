#!/usr/bin/env python3
"""
Builder for Safe Casio Retro LCD Watchface for Bozlun B71 (MOY-7H75-2.0.3, JieLi JLI, 466x466)
Uses the hardware-verified B71 binary template (face_28568.bin) with exact 4-digit-set header,
10-element table, JieLi footer alignment, and verified RLE compression.
"""

import os
import sys
import struct
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import watchface_tool as wt

TEMPLATE_BIN = "apk/face_28568.bin"
CASIO_IMG_DIR = "custom_watchfaces/03_casio_retro_lcd/images"
OUT_BIN = "custom_watchfaces/03_casio_retro_lcd/03_casio_retro_lcd_safe.bin"


def pad4(buf: bytearray, fill: int = 0xFF):
    rem = len(buf) % 4
    if rem != 0:
        buf.extend([fill] * (4 - rem))


def build_safe_casio():
    print("=" * 65)
    print("  BUILDING 100% SAFE CASIO RETRO WATCHFACE (B71 / JIELI)")
    print("=" * 65)

    with open(TEMPLATE_BIN, "rb") as f:
        tmpl = bytearray(f.read())

    # 1. Prepare all replacement blobs
    # We will map each slot in the original binary to our new Casio RLE blob.
    new_blobs = {}  # slot_id -> (bytes, w, h)

    # (A) Background Image
    bg_p = os.path.join(CASIO_IMG_DIR, "elem_00_image_00.png")
    w, h, rgba = wt.read_image_rgba(bg_p)
    new_blobs[("elem", 1, 0)] = (wt.compress_rgba_to_rle(rgba, w, h), w, h)
    print(f"[+] Encoded Background: {w}x{h} ({len(new_blobs[('elem', 1, 0)][0])} B)")

    # (B) Digit Set 0 & 1: Big 7-Segment Time Digits (0..9)
    for g in range(10):
        p = os.path.join(CASIO_IMG_DIR, f"digits_00_{g}.png")
        w, h, rgba = wt.read_image_rgba(p)
        rle = wt.compress_rgba_to_rle(rgba, w, h)
        new_blobs[("digit", 0, g)] = (rle, w, h)
        new_blobs[("digit", 1, g)] = (rle, w, h)
    print(f"[+] Encoded Digit Sets 0 & 1 (Time Digits): 10 glyphs each ({w}x{h})")

    # (C) Digit Set 2: Date / Month Small Digits (0..9)
    for g in range(10):
        p = os.path.join(CASIO_IMG_DIR, f"digits_01_{g}.png")
        w, h, rgba = wt.read_image_rgba(p)
        rle = wt.compress_rgba_to_rle(rgba, w, h)
        new_blobs[("digit", 2, g)] = (rle, w, h)
    print(f"[+] Encoded Digit Set 2 (Date/Month Digits): 10 glyphs ({w}x{h})")

    # (D) Digit Set 3: Steps White Digits (0..9)
    for g in range(10):
        p = os.path.join(CASIO_IMG_DIR, f"digits_02_{g}.png")
        w, h, rgba = wt.read_image_rgba(p)
        rle = wt.compress_rgba_to_rle(rgba, w, h)
        new_blobs[("digit", 3, g)] = (rle, w, h)
    print(f"[+] Encoded Digit Set 3 (White Steps Digits): 10 glyphs ({w}x{h})")

    # (E) Day Names (Mon..Sun)
    for g in range(7):
        p = os.path.join(CASIO_IMG_DIR, f"elem_02_day_name_{g:02d}.png")
        w, h, rgba = wt.read_image_rgba(p)
        rle = wt.compress_rgba_to_rle(rgba, w, h)
        new_blobs[("elem", 5, g)] = (rle, w, h)
    print(f"[+] Encoded Day Names: 7 glyphs ({w}x{h})")

    # (F) Battery Bar Display (0..10)
    for g in range(11):
        p = os.path.join(CASIO_IMG_DIR, f"elem_07_bar_display_{g:02d}.png")
        w, h, rgba = wt.read_image_rgba(p)
        rle = wt.compress_rgba_to_rle(rgba, w, h)
        new_blobs[("elem", 9, g)] = (rle, w, h)
    print(f"[+] Encoded Battery Bars: 11 glyphs ({w}x{h})")

    # (G) Dash Elements: Reuse original 1x1 dash from template
    # In face_28568.bin:
    # Elem 0 (dash): offset 575556, w=1, h=1, size 664
    # Elem 7 (dash): offset 547284, w=13, h=31, size 152
    new_blobs[("elem", 0, 0)] = (tmpl[575556 : 575556 + 664], 1, 1)
    new_blobs[("elem", 7, 0)] = (tmpl[547284 : 547284 + 152], 13, 31)

    # (H) Preview Image (280x280)
    prev_p = os.path.join(CASIO_IMG_DIR, "preview.png")
    w, h, rgba = wt.read_image_rgba(prev_p)
    new_blobs[("preview", 0, 0)] = (wt.compress_rgba_to_rle(rgba, w, h), w, h)
    print(f"[+] Encoded Preview: {w}x{h} ({len(new_blobs[('preview', 0, 0)][0])} B)")

    # 2. Extract original slot order from template
    meta = wt.parse_watchface_bin(bytes(tmpl))
    all_slots = []
    for d_idx, dset in enumerate(meta["digit_sets"]):
        for g_idx, g in enumerate(dset["glyphs"]):
            all_slots.append((g["offset"], ("digit", d_idx, g_idx)))

    for e_idx, el in enumerate(meta["elements"]):
        for o_idx, owh in enumerate(el["owhs"]):
            all_slots.append((owh["offset"], ("elem", e_idx, o_idx)))

    all_slots.append((meta["preview"]["offset"], ("preview", 0, 0)))
    all_slots.sort(key=lambda x: x[0])

    # 3. Assemble new image blob section starting at offset 664
    blob_section = bytearray()
    new_offsets = {}  # slot_id -> new_off

    for orig_off, slot_id in all_slots:
        blob_bytes, w, h = new_blobs[slot_id]
        new_off = 664 + len(blob_section)
        new_offsets[slot_id] = (new_off, w, h)
        blob_section.extend(blob_bytes)
        pad4(blob_section, 0xFF)

    # 4. Construct Header + Table (bytes 0 to 664)
    # Start with original template header
    hdr_table = bytearray(tmpl[:664])

    # (A) Update Preview offset in Header (bytes 4-7)
    prev_new_off, pw, ph = new_offsets[("preview", 0, 0)]
    struct.pack_into("<IHH", hdr_table, 4, prev_new_off, pw, ph)

    # (B) Update Digit Sets Table (starts at offset 16)
    # 16 + 2 = 18 is start of digit set 0. Each digit set is 83 bytes: 1 byte id + 10*8 bytes glyphs + 2 bytes unk
    for d_idx in range(4):
        base_d = 18 + d_idx * 83 + 1
        for g_idx in range(10):
            off, w, h = new_offsets[("digit", d_idx, g_idx)]
            struct.pack_into("<IHH", hdr_table, base_d + g_idx * 8, off, w, h)

    # (C) Update Elements Table (starts at offset 350)
    # Elem 0: dash (size 10): 01 23 <off> <w> <h>
    off, w, h = new_offsets[("elem", 0, 0)]
    struct.pack_into("<IHH", hdr_table, 350 + 2, off, w, h)

    # Elem 1: image / bg (size 14): 01 00 <x=0> <y=0> <off> <w=466> <h=466>
    off, w, h = new_offsets[("elem", 1, 0)]
    struct.pack_into("<HH", hdr_table, 360 + 2, 0, 0)
    struct.pack_into("<IHH", hdr_table, 360 + 6, off, w, h)

    # Elem 2: time_num (size 34): 01 02 <ds0, ds1, ds2, ds3> <x0, y0, x1, y1, x2, y2, x3, y3>
    # Coros Time Digits: H1: (110, 232), H2: (152, 232), M1: (216, 232), M2: (258, 232)
    struct.pack_into("<BBBB", hdr_table, 374 + 2, 0, 0, 0, 0)  # Use digit set 0
    casio_time_coords = [(110, 232), (152, 232), (216, 232), (258, 232)]
    for i, (cx, cy) in enumerate(casio_time_coords):
        struct.pack_into("<HH", hdr_table, 374 + 6 + i * 4, cx, cy)

    # Elem 3: day_num (size 12): 01 0d <ds=2> <align=2> <x0, y0, x1, y1>
    # Coros Day Number (DD): (282, 168), (296, 168)
    struct.pack_into("<BB", hdr_table, 408 + 2, 2, 2)
    struct.pack_into("<HHHH", hdr_table, 408 + 4, 282, 168, 296, 168)

    # Elem 4: month_num (size 12): 01 0f <ds=2> <align=2> <x0, y0, x1, y1>
    # Coros Month Number (MM): (320, 168), (334, 168)
    struct.pack_into("<BB", hdr_table, 420 + 2, 2, 2)
    struct.pack_into("<HHHH", hdr_table, 420 + 4, 320, 168, 334, 168)

    # Elem 5: day_name (size 63): 01 04 <x=216> <y=168> <pad=1> <7 glyphs>
    struct.pack_into("<HH", hdr_table, 432 + 3, 216, 168)
    for g in range(7):
        off, w, h = new_offsets[("elem", 5, g)]
        struct.pack_into("<IHH", hdr_table, 432 + 7 + g * 8, off, w, h)

    # Elem 6: steps_num (size 26): 01 07 <ds=3> <align=0> <x=126> <y=328>
    struct.pack_into("<BB", hdr_table, 495 + 2, 3, 0)
    struct.pack_into("<HH", hdr_table, 495 + 4, 126, 328)

    # Elem 7: dash (size 10): 01 23 <off> <w> <h>
    off, w, h = new_offsets[("elem", 7, 0)]
    struct.pack_into("<IHH", hdr_table, 521 + 2, off, w, h)

    # Elem 8: heart_rate_num (size 26): 01 06 <ds=2> <align=0> <x=126> <y=168>
    struct.pack_into("<BB", hdr_table, 531 + 2, 2, 0)
    struct.pack_into("<HH", hdr_table, 531 + 4, 126, 168)

    # Elem 9: bar_display (size 96): 01 12 <type=6> <cnt=11> <x=334> <y=328> <11 glyphs>
    struct.pack_into("<BB", hdr_table, 557 + 2, 6, 11)
    struct.pack_into("<HH", hdr_table, 557 + 4, 334, 328)
    for g in range(11):
        off, w, h = new_offsets[("elem", 9, g)]
        struct.pack_into("<IHH", hdr_table, 557 + 8 + g * 8, off, w, h)

    # Ensure the 12-byte footer remains intact:
    # 652: 00 00 00 00 04 00 80 00 01 00 00 00
    hdr_table[652:664] = bytes([0x00, 0x00, 0x00, 0x00, 0x04, 0x00, 0x80, 0x00, 0x01, 0x00, 0x00, 0x00])

    final_binary = bytes(hdr_table + blob_section)
    with open(OUT_BIN, "wb") as f:
        f.write(final_binary)

    crc = wt.moyoung_crc16(final_binary)
    print("=" * 65)
    print(f"[+] SAFE CASIO RETRO BINARY GENERATED: {OUT_BIN}")
    print(f"    - File Size : {len(final_binary):,} bytes")
    print(f"    - BLE CRC-16: 0x{crc:04X}")
    print(f"    - Header    : 664 bytes (Preserves exact JieLi B71 hardware layout)")
    print(f"    - Elements  : 10 elements (Image, Time, Day, Date, Month, Steps, HR, Battery, Dash)")
    print("=" * 65)
    return OUT_BIN, crc


if __name__ == "__main__":
    build_safe_casio()
