#!/usr/bin/env python3
"""
Generator for 8 Custom Bozlun B71 (MOY-7H75-2.0.3, JieLi JLI, 466x466) Watchfaces
Faithfully constructed from reference designs in referensi/
"""

import os
import sys
import json
import math
import struct
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import watchface_tool as wt

OUT_ROOT = os.path.abspath("custom_watchfaces")
FONT_BAHNSCHRIFT = "C:/Windows/Fonts/bahnschrift.ttf"
FONT_CONSOLA = "C:/Windows/Fonts/consolab.ttf"
FONT_ARIAL_BD = "C:/Windows/Fonts/arialbd.ttf"
FONT_TIMES_BD = "C:/Windows/Fonts/timesbd.ttf"

os.makedirs(OUT_ROOT, exist_ok=True)

# ============================================================================
# HELPER: UNIFORM DIGIT SET BUILDER
# ============================================================================

def make_uniform_digit_set(font_path, font_size, color=(255, 255, 255, 255), pad_w=4, pad_h=4):
    font = ImageFont.truetype(font_path, font_size)
    max_w, max_h = 0, 0
    bboxes = []
    for d in "0123456789":
        bb = font.getbbox(d)
        w = bb[2] - bb[0]
        h = bb[3] - bb[1]
        max_w = max(max_w, w)
        max_h = max(max_h, h)
        bboxes.append(bb)
    
    fw = max_w + pad_w
    fh = max_h + pad_h
    glyphs = []
    for i, d in enumerate("0123456789"):
        img = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        bb = bboxes[i]
        w = bb[2] - bb[0]
        h = bb[3] - bb[1]
        x = (fw - w) // 2 - bb[0]
        y = (fh - h) // 2 - bb[1]
        draw.text((x, y), d, fill=color, font=font)
        glyphs.append(img)
    return fw, fh, glyphs


def render_7segment_digit(w, h, digit_char, color=(20, 28, 20, 255), ghost_color=(150, 160, 145, 60), slant=0.06, t=None, pad=1):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if t is None:
        t = max(2, int(w * 0.17))
    
    seg_map = {
        '0': (1,1,1,1,1,1,0),
        '1': (0,1,1,0,0,0,0),
        '2': (1,1,0,1,1,0,1),
        '3': (1,1,1,1,0,0,1),
        '4': (0,1,1,0,0,1,1),
        '5': (1,0,1,1,0,1,1),
        '6': (1,0,1,1,1,1,1),
        '7': (1,1,1,0,0,0,0),
        '8': (1,1,1,1,1,1,1),
        '9': (1,1,1,1,0,1,1),
        ' ': (0,0,0,0,0,0,0),
        '-': (0,0,0,0,0,0,1),
    }
    active = seg_map.get(str(digit_char), (0,0,0,0,0,0,0))
    
    def pt(px, py):
        s = (h - py) * slant
        return (px + s, py)
    
    mid_y = h / 2.0
    half_t = t / 2.0
    
    # pa (top horizontal)
    pa = [pt(pad + half_t, 0), pt(w - pad - half_t, 0), pt(w - pad - t, t), pt(pad + t, t)]
    # pd (bottom horizontal)
    pd = [pt(pad + t, h - t), pt(w - pad - t, h - t), pt(w - pad - half_t, h), pt(pad + half_t, h)]
    # pg (middle horizontal)
    pg = [pt(pad + half_t, mid_y), pt(pad + t, mid_y - half_t), pt(w - pad - t, mid_y - half_t), pt(w - pad - half_t, mid_y), pt(w - pad - t, mid_y + half_t), pt(pad + t, mid_y + half_t)]
    # pb (top-right vertical)
    pb = [pt(w - pad - t, pad + t), pt(w - pad, pad + half_t), pt(w - pad, mid_y - half_t), pt(w - pad - t, mid_y - pad)]
    # pc (bottom-right vertical)
    pc = [pt(w - pad - t, mid_y + pad), pt(w - pad, mid_y + half_t), pt(w - pad, h - pad - half_t), pt(w - pad - t, h - pad - t)]
    # pf (top-left vertical)
    pf = [pt(pad, pad + half_t), pt(pad + t, pad + t), pt(pad + t, mid_y - pad), pt(pad, mid_y - half_t)]
    # pe (bottom-left vertical)
    pe = [pt(pad, mid_y + half_t), pt(pad + t, mid_y + pad), pt(pad + t, h - pad - t), pt(pad, h - pad - half_t)]
    
    segs = [pa, pb, pc, pd, pe, pf, pg]
    for i, poly in enumerate(segs):
        if ghost_color:
            d.polygon(poly, fill=ghost_color)
        if active[i]:
            d.polygon(poly, fill=color)
    return img


def make_7segment_digit_set(w, h, color=(20, 28, 20, 255), ghost_color=(150, 160, 145, 60), slant=0.06, t=None, pad=1):
    glyphs = []
    for d in "0123456789":
        glyphs.append(render_7segment_digit(w, h, d, color, ghost_color, slant, t, pad))
    return w, h, glyphs


def make_day_name_images(font_path, font_size, color=(255, 255, 255, 255), days=None, pad_w=8, pad_h=4):
    if days is None:
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
    
    fw = max_w + pad_w
    fh = max_h + pad_h
    day_imgs = []
    for i, day in enumerate(days):
        img = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        bb = bboxes[i]
        w = bb[2] - bb[0]
        h = bb[3] - bb[1]
        x = (fw - w) // 2 - bb[0]
        y = (fh - h) // 2 - bb[1]
        draw.text((x, y), day, fill=color, font=font)
        day_imgs.append(img)
    return fw, fh, day_imgs


def get_weather_icons(target_w=34, target_h=34, tint=None):
    icons = []
    for i in range(9):
        p = f"unpacked_3000/images/elem_01_weather_{i:02d}.png"
        if os.path.exists(p):
            im = Image.open(p).convert("RGBA")
            if im.size != (target_w, target_h):
                im = im.resize((target_w, target_h), Image.Resampling.LANCZOS)
            if tint:
                r_t, g_t, b_t = tint[:3]
                pixels = im.load()
                for y in range(im.height):
                    for x in range(im.width):
                        r, g, b, a = pixels[x, y]
                        if a > 0:
                            pixels[x, y] = (r_t, g_t, b_t, a)
            icons.append(im)
        else:
            im = Image.new("RGBA", (target_w, target_h), (255, 255, 255, 180))
            icons.append(im)
    return icons


def make_temp_symbols(font_path, font_size, color=(255, 255, 255, 255)):
    font = ImageFont.truetype(font_path, font_size)
    syms = ["-", "°C", "°F"]
    imgs = []
    for s in syms:
        bb = font.getbbox(s)
        w = max(4, bb[2] - bb[0] + 4)
        h = max(4, bb[3] - bb[1] + 4)
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.text((2 - bb[0], 2 - bb[1]), s, fill=color, font=font)
        imgs.append(im)
    return imgs


def make_battery_bars(w=68, h=20, border_color=(120, 120, 120, 255), fill_color=(40, 180, 80, 255)):
    imgs = []
    for lvl in range(11):
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        body_w = w - 6
        d.rounded_rectangle([0, 1, body_w, h - 2], radius=3, outline=border_color, width=2)
        d.rounded_rectangle([body_w, h // 2 - 4, w - 1, h // 2 + 4], radius=1, fill=border_color)
        if lvl > 0:
            fw = max(2, int((body_w - 6) * (lvl / 10.0)))
            lvl_col = (235, 50, 50, 255) if lvl <= 1 else ((245, 175, 25, 255) if lvl <= 3 else fill_color)
            d.rounded_rectangle([3, 4, 3 + fw, h - 5], radius=1, fill=lvl_col)
        imgs.append(im)
    return imgs


def make_dauphine_hand(w=18, l_tip=130, l_tail=26, fill_color=(240, 240, 245, 255), shadow_color=(170, 175, 185, 255)):
    h = l_tip + l_tail
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = w // 2
    poly_l = [(cx, 2), (1, l_tip - 25), (cx - 1, l_tip), (cx - 1, h - 3), (cx, h - 1)]
    poly_r = [(cx, 2), (w - 2, l_tip - 25), (cx + 1, l_tip), (cx + 1, h - 3), (cx, h - 1)]
    d.polygon(poly_l, fill=fill_color)
    d.polygon(poly_r, fill=shadow_color)
    d.line([(cx, 2), (cx, h - 1)], fill=(255, 255, 255, 220), width=1)
    return im, l_tip


def make_tactical_hand(w=20, l_tip=125, l_tail=25, body_color=(50, 55, 60, 255), tip_color=(245, 245, 245, 255)):
    h = l_tip + l_tail
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = w // 2
    poly_outer = [(cx, 2), (w - 2, 25), (w - 3, l_tip), (w - 4, h - 4), (cx, h - 1), (3, h - 4), (2, l_tip), (1, 25)]
    d.polygon(poly_outer, fill=body_color, outline=(90, 95, 105, 255), width=1)
    poly_tip = [(cx, 4), (w - 4, 25), (cx + 2, 28), (cx - 2, 28), (3, 25)]
    d.polygon(poly_tip, fill=tip_color)
    poly_cut = [(cx, 36), (w - 5, 42), (w - 5, l_tip - 15), (cx, l_tip - 5), (4, l_tip - 15), (4, 42)]
    d.polygon(poly_cut, fill=(0, 0, 0, 0))
    return im, l_tip


def make_neon_hand(w=16, l_tip=130, l_tail=26, glow_color=(44, 245, 125, 255), core_color=(220, 255, 230, 255)):
    h = l_tip + l_tail
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = w // 2
    d.rounded_rectangle([2, 2, w - 3, l_tip + 5], radius=cx - 1, fill=glow_color)
    d.rounded_rectangle([cx - 2, l_tip + 5, cx + 2, h - 2], radius=1, fill=glow_color)
    d.rounded_rectangle([4, 6, w - 5, l_tip - 2], radius=cx - 2, fill=core_color)
    return im, l_tip


def make_needle_hand(w=8, l_tip=215, l_tail=55, color=(230, 40, 40, 255)):
    h = l_tip + l_tail
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = w // 2
    d.line([(cx, 2), (cx, l_tip + 5)], fill=color, width=2)
    # Counterweight tail
    d.rounded_rectangle([cx - 3, l_tip + 5, cx + 3, h - 4], radius=2, fill=color)
    return im, l_tip


def make_center_cap(size=20, fill_color=(40, 44, 50, 255), ring_color=(180, 185, 195, 255), pip_color=None):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, size - 1, size - 1], fill=fill_color, outline=ring_color, width=2)
    if pip_color:
        d.ellipse([size // 2 - 3, size // 2 - 3, size // 2 + 3, size // 2 + 3], fill=pip_color)
    return im


# ============================================================================
# WATCHFACE JSON & BIN BUILDER
# ============================================================================

class WatchfaceBuilder:
    def __init__(self, name, width=466, height=466):
        self.name = name
        self.width = width
        self.height = height
        self.out_dir = os.path.join(OUT_ROOT, name)
        self.img_dir = os.path.join(self.out_dir, "images")
        os.makedirs(self.img_dir, exist_ok=True)
        self.digit_sets = []
        self.elements = []
        self.preview_img = None
        self.bg_img = None

    def add_digit_set(self, glyph_imgs):
        d_id = len(self.digit_sets)
        glyphs_meta = []
        for g_idx, g_img in enumerate(glyph_imgs):
            fname = f"digits_{d_id:02d}_{g_idx}.png"
            rel_file = f"images/{fname}"
            g_img.save(os.path.join(self.img_dir, fname))
            glyphs_meta.append({
                "offset": 0,
                "w": g_img.width,
                "h": g_img.height,
                "image": {
                    "file": rel_file,
                    "w": g_img.width,
                    "h": g_img.height
                }
            })
        self.digit_sets.append({
            "digit_set_id": d_id,
            "unknown": 257,
            "glyphs": glyphs_meta
        })
        return d_id

    def set_background(self, img):
        self.bg_img = img
        fname = "elem_00_image_00.png"
        img.save(os.path.join(self.img_dir, fname))
        raw_b = struct.pack("<BBHH IHH", 1, 0, 0, 0, 0, img.width, img.height)
        self.elements.insert(0, {
            "e_type": 0,
            "name": "image",
            "size": 14,
            "raw_hex": raw_b.hex(),
            "owhs": [{
                "rel_offset": 6,
                "offset": 0,
                "w": img.width,
                "h": img.height,
                "image": {
                    "file": f"images/{fname}",
                    "w": img.width,
                    "h": img.height
                }
            }],
            "x": 0,
            "y": 0
        })

    def add_overlay_image(self, img, x, y):
        e_idx = len(self.elements)
        fname = f"elem_{e_idx:02d}_image_00.png"
        img.save(os.path.join(self.img_dir, fname))
        raw_b = struct.pack("<BBHH IHH", 1, 0, x, y, 0, img.width, img.height)
        self.elements.append({
            "e_type": 0,
            "name": "image",
            "size": 14,
            "raw_hex": raw_b.hex(),
            "owhs": [{
                "rel_offset": 6,
                "offset": 0,
                "w": img.width,
                "h": img.height,
                "image": {
                    "file": f"images/{fname}",
                    "w": img.width,
                    "h": img.height
                }
            }],
            "x": x,
            "y": y
        })

    def add_time_num(self, d_sets, coords):
        d0, d1, d2, d3 = d_sets
        x0, y0 = coords[0]
        x1, y1 = coords[1]
        x2, y2 = coords[2]
        x3, y3 = coords[3]
        raw_b = struct.pack("<BB BBBB 8H 12B", 1, 2, d0, d1, d2, d3, x0, y0, x1, y1, x2, y2, x3, y3, *([0]*12))
        self.elements.append({
            "e_type": 2,
            "name": "time_num",
            "size": 34,
            "raw_hex": raw_b.hex(),
            "owhs": [],
            "digit_sets": list(d_sets),
            "coords": [{"x": c[0], "y": c[1]} for c in coords]
        })

    def add_day_name(self, day_imgs, x, y):
        e_idx = len(self.elements)
        owhs = []
        for i, dim in enumerate(day_imgs):
            fname = f"elem_{e_idx:02d}_day_name_{i:02d}.png"
            dim.save(os.path.join(self.img_dir, fname))
            owhs.append({
                "rel_offset": 7 + i * 8,
                "offset": 0,
                "w": dim.width,
                "h": dim.height,
                "image": {
                    "file": f"images/{fname}",
                    "w": dim.width,
                    "h": dim.height
                }
            })
        raw_b = struct.pack("<BB B HH 7Q", 1, 4, 1, x, y, *([0]*7))
        self.elements.append({
            "e_type": 4,
            "name": "day_name",
            "size": 63,
            "raw_hex": raw_b.hex(),
            "owhs": owhs,
            "x": x,
            "y": y
        })

    def add_day_num(self, d_id, coords, align=2):
        x0, y0 = coords[0]
        x1, y1 = coords[1]
        raw_b = struct.pack("<BB BB 4H", 1, 13, d_id, align, x0, y0, x1, y1)
        self.elements.append({
            "e_type": 13,
            "name": "day_num",
            "size": 12,
            "raw_hex": raw_b.hex(),
            "owhs": [],
            "digit_set": d_id,
            "align": align,
            "coords": [{"x": c[0], "y": c[1]} for c in coords]
        })

    def add_month_num(self, d_id, coords, align=2):
        x0, y0 = coords[0]
        x1, y1 = coords[1]
        raw_b = struct.pack("<BB BB 4H", 1, 15, d_id, align, x0, y0, x1, y1)
        self.elements.append({
            "e_type": 15,
            "name": "month_num",
            "size": 12,
            "raw_hex": raw_b.hex(),
            "owhs": [],
            "digit_set": d_id,
            "align": align,
            "coords": [{"x": c[0], "y": c[1]} for c in coords]
        })

    def add_steps_num(self, d_id, x, y, align=0):
        raw_b = struct.pack("<BB BB HH 18B", 1, 7, d_id, align, x, y, *([0]*18))
        self.elements.append({
            "e_type": 7,
            "name": "steps_num",
            "size": 26,
            "raw_hex": raw_b.hex(),
            "owhs": [],
            "digit_set": d_id,
            "align": align,
            "x": x,
            "y": y
        })

    def add_heart_rate_num(self, d_id, x, y, align=0):
        raw_b = struct.pack("<BB BB HH 18B", 1, 6, d_id, align, x, y, *([0]*18))
        self.elements.append({
            "e_type": 6,
            "name": "heart_rate_num",
            "size": 26,
            "raw_hex": raw_b.hex(),
            "owhs": [],
            "digit_set": d_id,
            "align": align,
            "x": x,
            "y": y
        })

    def add_distance_num(self, d_id, x, y, align=0):
        raw_b = struct.pack("<BB BB HH 18B", 1, 8, d_id, align, x, y, *([0]*18))
        self.elements.append({
            "e_type": 8,
            "name": "distance_num",
            "size": 26,
            "raw_hex": raw_b.hex(),
            "owhs": [],
            "digit_set": d_id,
            "align": align,
            "x": x,
            "y": y
        })

    def add_kcal_num(self, d_id, x, y, align=0):
        raw_b = struct.pack("<BB BB HH 9B", 1, 9, d_id, align, x, y, *([0]*9))
        self.elements.append({
            "e_type": 9,
            "name": "kcal_num",
            "size": 17,
            "raw_hex": raw_b.hex(),
            "owhs": [],
            "digit_set": d_id,
            "align": align,
            "x": x,
            "y": y
        })

    def add_bar_display(self, bar_imgs, x, y, b_type=6):
        e_idx = len(self.elements)
        count = len(bar_imgs)
        owhs = []
        for i, bim in enumerate(bar_imgs):
            fname = f"elem_{e_idx:02d}_bar_display_{i:02d}.png"
            bim.save(os.path.join(self.img_dir, fname))
            owhs.append({
                "rel_offset": 8 + i * 8,
                "offset": 0,
                "w": bim.width,
                "h": bim.height,
                "image": {
                    "file": f"images/{fname}",
                    "w": bim.width,
                    "h": bim.height
                }
            })
        raw_b = struct.pack(f"<BB BB HH {count}Q", 1, 18, b_type, count, x, y, *([0]*count))
        self.elements.append({
            "e_type": 18,
            "name": "bar_display",
            "size": 8 + count * 8,
            "raw_hex": raw_b.hex(),
            "owhs": owhs,
            "x": x,
            "y": y
        })

    def add_weather(self, weather_imgs, x, y):
        e_idx = len(self.elements)
        count = len(weather_imgs)
        owhs = []
        for i, wim in enumerate(weather_imgs):
            fname = f"elem_{e_idx:02d}_weather_{i:02d}.png"
            wim.save(os.path.join(self.img_dir, fname))
            owhs.append({
                "rel_offset": 7 + i * 8,
                "offset": 0,
                "w": wim.width,
                "h": wim.height,
                "image": {
                    "file": f"images/{fname}",
                    "w": dim.width if 'dim' in locals() else wim.width,
                    "h": dim.height if 'dim' in locals() else wim.height
                }
            })
            owhs[-1]["image"]["w"] = wim.width
            owhs[-1]["image"]["h"] = wim.height
        raw_b = struct.pack(f"<BB B HH {count}Q", 1, 27, count, x, y, *([0]*count))
        self.elements.append({
            "e_type": 27,
            "name": "weather",
            "size": 7 + count * 8,
            "raw_hex": raw_b.hex(),
            "owhs": owhs,
            "x": x,
            "y": y
        })

    def add_temp_num(self, d_id, sym_imgs, x, y):
        e_idx = len(self.elements)
        owhs = []
        for i, sim in enumerate(sym_imgs):
            fname = f"elem_{e_idx:02d}_decor_multi_{i:02d}.png"
            sim.save(os.path.join(self.img_dir, fname))
            owhs.append({
                "rel_offset": 8 + i * 8,
                "offset": 0,
                "w": sim.width,
                "h": sim.height,
                "image": {
                    "file": f"images/{fname}",
                    "w": sim.width,
                    "h": sim.height
                }
            })
        raw_b = struct.pack("<BB BB HH 3Q", 1, 28, d_id, 0, x, y, 0, 0, 0)
        self.elements.append({
            "e_type": 28,
            "name": "decor_multi",
            "size": 32,
            "raw_hex": raw_b.hex(),
            "owhs": owhs,
            "x": x,
            "y": y
        })

    def add_time_hand(self, hand_img, hand_type, center_x=233, center_y=233, pivot_from_top=None):
        e_idx = len(self.elements)
        fname = f"elem_{e_idx:02d}_time_hand_00.png"
        hand_img.save(os.path.join(self.img_dir, fname))
        w = hand_img.width
        h = hand_img.height
        if pivot_from_top is None:
            pivot_from_top = h - 25
        top_left_x = center_x - (w // 2)
        top_left_y = center_y - pivot_from_top
        raw_b = struct.pack("<BB B HH IHH 4B", 1, 10, hand_type, top_left_x, top_left_y, 0, w, h, 0xFF, 0xFF, 0xFF, 0xFF)
        self.elements.append({
            "e_type": 10,
            "name": "time_hand",
            "size": 19,
            "raw_hex": raw_b.hex(),
            "owhs": [{
                "rel_offset": 7,
                "offset": 0,
                "w": w,
                "h": h,
                "image": {
                    "file": f"images/{fname}",
                    "w": w,
                    "h": h
                }
            }],
            "hand_type": hand_type,
            "pivot_x": top_left_x,
            "pivot_y": top_left_y
        })

    def set_preview(self, preview_img):
        self.preview_img = preview_img
        fname = "preview.png"
        preview_img.save(os.path.join(self.img_dir, fname))

    def build_and_pack(self, api_ver=35):
        d_offset = 16
        num_d = len(self.digit_sets)
        e_offset = d_offset + (2 + num_d * 83 if num_d > 0 else 0)
        
        meta = {
            "format": "watchface_bin",
            "file_size": 0,
            "api_ver": api_ver,
            "unknown": 65535,
            "preview": {
                "offset": 0,
                "w": self.preview_img.width if self.preview_img else 280,
                "h": self.preview_img.height if self.preview_img else 280,
                "image": {
                    "file": "images/preview.png",
                    "w": self.preview_img.width if self.preview_img else 280,
                    "h": self.preview_img.height if self.preview_img else 280
                }
            },
            "d_offset": d_offset,
            "e_offset": e_offset,
            "digit_sets": self.digit_sets,
            "elements": self.elements
        }
        
        json_path = os.path.join(self.out_dir, "watchface.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
            
        bin_path = os.path.join(self.out_dir, f"{self.name}.bin")
        wt.pack_watchface(self.out_dir, bin_path)
        
        prev_copy_path = os.path.join(OUT_ROOT, f"{self.name}_preview.png")
        if self.preview_img:
            self.preview_img.save(prev_copy_path)
            
        print(f"[+] Watchface {self.name} built -> {bin_path}")
        return bin_path


# ============================================================================
# WATCHFACE 1: RASTER · SWISS GRID
# ============================================================================

def build_01_raster_swiss_grid():
    b = WatchfaceBuilder("01_raster_swiss_grid")
    
    # Background
    bg = Image.new("RGBA", (466, 466), (242, 239, 232, 255))
    d = ImageDraw.Draw(bg)
    d.ellipse([10, 10, 456, 456], outline=(220, 215, 205, 255), width=2)
    d.line([(232, 75), (232, 340)], fill=(205, 198, 188, 255), width=2)
    d.line([(65, 345), (401, 345)], fill=(205, 198, 188, 255), width=2)
    d.line([(232, 348), (232, 415)], fill=(205, 198, 188, 255), width=2)
    
    font_lbl = ImageFont.truetype(FONT_BAHNSCHRIFT, 14)
    font_brand = ImageFont.truetype(FONT_BAHNSCHRIFT, 16)
    d.text((120, 355), "STEPS", fill=(130, 122, 112, 255), font=font_lbl)
    d.text((280, 355), "BATTERY", fill=(130, 122, 112, 255), font=font_lbl)
    d.text((233, 435), "· RASTER ·", fill=(160, 152, 142, 255), font=font_brand, anchor="mm")
    b.set_background(bg)
    
    # Digits
    _, _, d_hour = make_uniform_digit_set(FONT_BAHNSCHRIFT, 94, color=(24, 25, 28, 255), pad_w=2, pad_h=4)
    _, _, d_min = make_uniform_digit_set(FONT_BAHNSCHRIFT, 94, color=(216, 43, 43, 255), pad_w=2, pad_h=4)
    _, _, d_date = make_uniform_digit_set(FONT_BAHNSCHRIFT, 40, color=(24, 25, 28, 255), pad_w=2, pad_h=2)
    _, _, d_small = make_uniform_digit_set(FONT_BAHNSCHRIFT, 24, color=(24, 25, 28, 255), pad_w=2, pad_h=2)
    
    id_h = b.add_digit_set(d_hour)
    id_m = b.add_digit_set(d_min)
    id_date = b.add_digit_set(d_date)
    id_small = b.add_digit_set(d_small)
    
    # Time Num
    b.add_time_num((id_h, id_h, id_m, id_m), [
        (88, 100), (150, 100),
        (88, 210), (150, 210)
    ])
    
    # Day Name
    _, _, days = make_day_name_images(FONT_BAHNSCHRIFT, 24, color=(216, 43, 43, 255), pad_w=6, pad_h=2)
    b.add_day_name(days, 252, 105)
    
    # Day Num & Month Num
    b.add_day_num(id_date, [(252, 140), (276, 140)])
    b.add_month_num(id_date, [(310, 140), (334, 140)])
    
    # Weather & Temp
    weather_icons = get_weather_icons(38, 38, tint=(40, 42, 45, 255))
    b.add_weather(weather_icons, 252, 195)
    temp_syms = make_temp_symbols(FONT_BAHNSCHRIFT, 24, color=(40, 42, 45, 255))
    b.add_temp_num(id_small, temp_syms, 300, 202)
    
    # Steps
    b.add_steps_num(id_small, 95, 378, align=0)
    
    # Battery Bar
    bars = make_battery_bars(w=76, h=22, border_color=(140, 134, 124, 255), fill_color=(40, 160, 70, 255))
    b.add_bar_display(bars, 255, 378)
    
    # Preview
    prev = bg.copy()
    pd = ImageDraw.Draw(prev)
    pd.text((88, 100), "12", fill=(24, 25, 28, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 94))
    pd.text((88, 210), "35", fill=(216, 43, 43, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 94))
    pd.text((252, 105), "TUE", fill=(216, 43, 43, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 24))
    pd.text((252, 140), "01", fill=(24, 25, 28, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 40))
    pd.text((310, 140), "09", fill=(24, 25, 28, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 40))
    prev.paste(weather_icons[0], (252, 195), weather_icons[0])
    pd.text((300, 202), "30°C", fill=(40, 42, 45, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 24))
    pd.text((95, 378), "3140", fill=(24, 25, 28, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 24))
    prev.paste(bars[9], (255, 378), bars[9])
    
    b.set_preview(prev.resize((280, 280), Image.Resampling.LANCZOS))
    return b.build_and_pack(api_ver=35)


# ============================================================================
# WATCHFACE 2: KHNST02 MINIMAL DIGITAL
# ============================================================================

def build_02_khnst02_minimal_digital():
    b = WatchfaceBuilder("02_khnst02_minimal_digital")
    
    # Background
    bg = Image.new("RGBA", (466, 466), (0, 0, 0, 255))
    d = ImageDraw.Draw(bg)
    d.ellipse([6, 6, 460, 460], outline=(35, 35, 40, 255), width=2)
    
    def draw_tick(deg, color, length=10, width=3):
        rad = math.radians(deg)
        x1 = 233 + 225 * math.cos(rad)
        y1 = 233 + 225 * math.sin(rad)
        x2 = 233 + (225 - length) * math.cos(rad)
        y2 = 233 + (225 - length) * math.sin(rad)
        d.line([(x1, y1), (x2, y2)], fill=color, width=width)
        
    draw_tick(-30, (255, 60, 60, 255), length=10, width=3)  # 2 o'clock red
    draw_tick(30, (0, 229, 255, 255), length=10, width=3)   # 4 o'clock cyan
    draw_tick(180, (200, 200, 200, 255), length=8, width=2) # 9 o'clock white
    
    for dx in [213, 223, 233, 243, 253]:
        d.ellipse([dx - 2, 70, dx + 2, 74], fill=(160, 160, 160, 255))
        
    d.polygon([(216, 96), (222, 96), (218, 102), (223, 102), (215, 110), (217, 104), (213, 104)], fill=(255, 255, 255, 255))
    d.ellipse([231, 195, 236, 200], fill=(255, 255, 255, 255))
    d.ellipse([231, 215, 236, 220], fill=(255, 255, 255, 255))
    d.ellipse([246, 148, 249, 151], fill=(255, 255, 255, 255))
    
    font_lbl = ImageFont.truetype(FONT_BAHNSCHRIFT, 17)
    d.text((130, 272), "STEP", fill=(130, 130, 130, 255), font=font_lbl)
    d.text((130, 302), "HEART RATE", fill=(130, 130, 130, 255), font=font_lbl)
    d.text((130, 332), "KCAL", fill=(130, 130, 130, 255), font=font_lbl)
    d.text((130, 362), "DISTANCE", fill=(130, 130, 130, 255), font=font_lbl)
    
    d.line([(100, 392), (366, 392)], fill=(30, 30, 30, 255), width=2)
    for gy in range(402, 450, 4):
        half_w = int(math.sqrt(max(0, 210**2 - (gy - 233)**2)))
        x_start = max(110, 233 - half_w + 10)
        x_end = min(356, 233 + half_w - 10)
        for gx in range(x_start, x_end, 5):
            d.point((gx, gy), fill=(70, 70, 75, 255))
            
    b.set_background(bg)
    
    # Digits
    _, _, d_time = make_uniform_digit_set(FONT_BAHNSCHRIFT, 78, color=(255, 255, 255, 255), pad_w=2, pad_h=2)
    _, _, d_date = make_uniform_digit_set(FONT_BAHNSCHRIFT, 22, color=(255, 255, 255, 255), pad_w=2, pad_h=2)
    _, _, d_val = make_uniform_digit_set(FONT_CONSOLA, 19, color=(255, 255, 255, 255), pad_w=2, pad_h=2)
    
    id_t = b.add_digit_set(d_time)
    id_date = b.add_digit_set(d_date)
    id_val = b.add_digit_set(d_val)
    
    b.add_time_num((id_t, id_t, id_t, id_t), [
        (118, 172), (168, 172),
        (248, 172), (298, 172)
    ])
    
    _, _, days = make_day_name_images(FONT_BAHNSCHRIFT, 22, color=(255, 255, 255, 255), pad_w=6, pad_h=2)
    b.add_day_name(days, 155, 134)
    b.add_day_num(id_date, [(222, 134), (234, 134)])
    b.add_month_num(id_date, [(254, 134), (266, 134)])
    
    b.add_steps_num(id_val, 305, 272, align=0)
    b.add_heart_rate_num(id_val, 305, 302, align=0)
    b.add_kcal_num(id_val, 305, 332, align=0)
    b.add_distance_num(id_val, 305, 362, align=0)
    
    bars = make_battery_bars(w=48, h=16, border_color=(120, 120, 120, 255), fill_color=(0, 230, 118, 255))
    b.add_bar_display(bars, 228, 96)
    
    # Preview
    prev = bg.copy()
    pd = ImageDraw.Draw(prev)
    pd.text((118, 172), "10", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 78))
    pd.text((248, 172), "45", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 78))
    pd.text((155, 134), "SUN", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 22))
    pd.text((222, 134), "23", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 22))
    pd.text((254, 134), "09", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 22))
    f_val = ImageFont.truetype(FONT_CONSOLA, 19)
    pd.text((305, 272), "   90", fill=(255, 255, 255, 255), font=f_val)
    pd.text((305, 302), "  068", fill=(255, 255, 255, 255), font=f_val)
    pd.text((305, 332), " 2200", fill=(255, 255, 255, 255), font=f_val)
    pd.text((305, 362), " 4.65", fill=(255, 255, 255, 255), font=f_val)
    prev.paste(bars[8], (228, 96), bars[8])
    
    b.set_preview(prev.resize((280, 280), Image.Resampling.LANCZOS))
    return b.build_and_pack(api_ver=35)


# ============================================================================
# WATCHFACE 3: CASIO RETRO CLASSIC LCD
# ============================================================================

def build_03_casio_retro_lcd():
    b = WatchfaceBuilder("03_casio_retro_lcd")
    
    bg = Image.new("RGBA", (466, 466), (20, 22, 24, 255))
    d = ImageDraw.Draw(bg)
    d.ellipse([10, 10, 456, 456], outline=(35, 38, 42, 255), width=3)
    d.rounded_rectangle([52, 90, 414, 376], radius=40, outline=(37, 99, 235, 255), width=3)
    
    f_casio = ImageFont.truetype(FONT_ARIAL_BD, 20)
    f_gold = ImageFont.truetype(FONT_BAHNSCHRIFT, 13)
    f_wr = ImageFont.truetype(FONT_ARIAL_BD, 14)
    
    d.text((233, 102), "CASIO", fill=(240, 240, 240, 255), font=f_casio, anchor="mm")
    d.text((233, 122), "ALARM CHRONOGRAPH", fill=(234, 179, 8, 255), font=f_gold, anchor="mm")
    
    d.rounded_rectangle([212, 346, 254, 366], radius=3, fill=(185, 28, 28, 255))
    d.text((233, 356), "WR", fill=(255, 255, 255, 255), font=f_wr, anchor="mm")
    d.text((160, 356), "WATER", fill=(220, 220, 220, 255), font=f_gold, anchor="mm")
    d.text((306, 356), "RESIST", fill=(220, 220, 220, 255), font=f_gold, anchor="mm")
    
    lx, ly, lw, lh = 75, 136, 316, 196
    d.rounded_rectangle([lx, ly, lx + lw, ly + lh], radius=16, fill=(221, 229, 215, 255), outline=(150, 160, 145, 255), width=2)
    d.rounded_rectangle([lx+2, ly+2, lx + lw - 2, ly + lh - 2], radius=14, outline=(190, 200, 185, 255), width=1)
    
    # Icons inside LCD
    d.polygon([(92, 154), (96, 149), (101, 154), (96, 161)], fill=(30, 40, 30, 255))
    d.polygon([(97, 154), (102, 149), (107, 154), (102, 161)], fill=(30, 40, 30, 255))
    d.line([(258, 154), (266, 154)], fill=(30, 40, 30, 255), width=2)
    d.line([(258, 158), (266, 158)], fill=(30, 40, 30, 255), width=2)
    d.text((330, 210), "24 H", fill=(30, 40, 30, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 12), anchor="mm")
    d.rectangle([223, 218, 227, 224], fill=(30, 40, 30, 255))
    d.rectangle([223, 238, 227, 244], fill=(30, 40, 30, 255))
    d.ellipse([92, 298, 97, 303], fill=(30, 40, 30, 255))
    d.ellipse([99, 298, 104, 303], fill=(30, 40, 30, 255))
    d.ellipse([94, 305, 102, 311], fill=(30, 40, 30, 255))
    d.polygon([(290, 298), (295, 298), (292, 304), (296, 304), (289, 312), (291, 306), (288, 306)], fill=(30, 40, 30, 255))
    
    b.set_background(bg)
    
    # 7-Segment Digits
    _, _, d_time = make_7segment_digit_set(36, 68, color=(24, 34, 24, 255), ghost_color=(175, 185, 170, 70), slant=0.06, t=6)
    _, _, d_small = make_7segment_digit_set(14, 26, color=(24, 34, 24, 255), ghost_color=(175, 185, 170, 70), slant=0.06, t=3)
    
    id_t = b.add_digit_set(d_time)
    id_s = b.add_digit_set(d_small)
    
    b.add_time_num((id_t, id_t, id_t, id_t), [
        (120, 198), (170, 198),
        (240, 198), (290, 198)
    ])
    
    _, _, days = make_day_name_images(FONT_BAHNSCHRIFT, 20, color=(24, 34, 24, 255), pad_w=4, pad_h=2)
    b.add_day_name(days, 210, 144)
    b.add_day_num(id_s, [(272, 144), (288, 144)])
    b.add_month_num(id_s, [(312, 144), (328, 144)])
    
    b.add_heart_rate_num(id_s, 115, 144, align=0)
    b.add_steps_num(id_s, 112, 294, align=0)
    
    # Retro LCD battery bars
    def make_bars():
        imgs = []
        for lvl in range(11):
            im = Image.new("RGBA", (44, 18), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.rectangle([0, 1, 39, 16], outline=(30, 40, 30, 255), width=2)
            d.rectangle([39, 5, 42, 12], fill=(30, 40, 30, 255))
            if lvl > 0:
                fw = max(2, int(33 * (lvl / 10.0)))
                d.rectangle([3, 4, 3 + fw, 13], fill=(30, 40, 30, 255))
            imgs.append(im)
        return imgs
    b.add_bar_display(make_bars(), 304, 296)
    
    # Preview
    prev = bg.copy()
    prev.paste(d_time[2], (120, 198), d_time[2])
    prev.paste(d_time[0], (170, 198), d_time[0])
    prev.paste(d_time[3], (240, 198), d_time[3])
    prev.paste(d_time[1], (290, 198), d_time[1])
    prev.paste(days[5], (210, 144), days[5])
    prev.paste(d_small[1], (272, 144), d_small[1])
    prev.paste(d_small[8], (288, 144), d_small[8])
    prev.paste(d_small[0], (312, 144), d_small[0])
    prev.paste(d_small[9], (328, 144), d_small[9])
    prev.paste(d_small[9], (115, 144), d_small[9])
    prev.paste(d_small[6], (131, 144), d_small[6])
    prev.paste(d_small[8], (112, 294), d_small[8])
    prev.paste(d_small[4], (128, 294), d_small[4])
    prev.paste(d_small[2], (144, 294), d_small[2])
    prev.paste(d_small[0], (160, 294), d_small[0])
    bars = make_bars()
    prev.paste(bars[8], (304, 296), bars[8])
    
    b.set_preview(prev.resize((280, 280), Image.Resampling.LANCZOS))
    return b.build_and_pack(api_ver=35)


# ============================================================================
# WATCHFACE 4: MINIMALIST ROMAN ANALOG
# ============================================================================

def build_04_minimalist_roman_analog():
    b = WatchfaceBuilder("04_minimalist_roman_analog")
    
    cx, cy = 233, 233
    bg = Image.new("RGBA", (466, 466), (12, 14, 20, 255))
    d = ImageDraw.Draw(bg)
    
    for m in range(60):
        rad = math.radians(m * 6 - 90)
        is_5m = (m % 5 == 0)
        r_outer = 216
        r_inner = 206 if is_5m else 211
        col = (220, 225, 235, 255) if is_5m else (100, 105, 120, 255)
        w = 2 if is_5m else 1
        x1 = cx + r_outer * math.cos(rad)
        y1 = cy + r_outer * math.sin(rad)
        x2 = cx + r_inner * math.cos(rad)
        y2 = cy + r_inner * math.sin(rad)
        d.line([(x1, y1), (x2, y2)], fill=col, width=w)

    # 12 o'clock double baton
    d.line([(cx - 4, cy - 204), (cx - 4, cy - 176)], fill=(230, 235, 245, 255), width=3)
    d.line([(cx + 4, cy - 204), (cx + 4, cy - 176)], fill=(230, 235, 245, 255), width=3)
    d.ellipse([cx - 3, cy - 214, cx + 3, cy - 208], fill=(239, 68, 68, 255))

    # 1 & 2 o'clock single batons
    for hour in [1, 2]:
        rad = math.radians(hour * 30 - 90)
        x1 = cx + 204 * math.cos(rad)
        y1 = cy + 204 * math.sin(rad)
        x2 = cx + 176 * math.cos(rad)
        y2 = cy + 176 * math.sin(rad)
        d.line([(x1, y1), (x2, y2)], fill=(230, 235, 245, 255), width=3)

    # 3 o'clock Day-Date Window frame
    wx, wy, ww, wh = 296, 218, 92, 30
    d.rounded_rectangle([wx, wy, wx + ww, wy + wh], radius=3, outline=(180, 185, 195, 255), fill=(20, 24, 32, 255), width=2)
    d.ellipse([wx + ww + 6, cy - 3, wx + ww + 12, cy + 3], fill=(59, 130, 246, 255))

    # Roman numerals 4 to 11
    romans = {4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X", 11: "XI"}
    f_roman = ImageFont.truetype(FONT_TIMES_BD, 26)
    for h_idx, rom in romans.items():
        rad = math.radians(h_idx * 30 - 90)
        rx = cx + 176 * math.cos(rad)
        ry = cy + 176 * math.sin(rad)
        d.text((rx, ry), rom, fill=(230, 235, 245, 255), font=f_roman, anchor="mm")

    b.set_background(bg)
    
    # Complications inside Day-Date window
    _, _, d_date = make_uniform_digit_set(FONT_BAHNSCHRIFT, 20, color=(240, 240, 245, 255), pad_w=2, pad_h=2)
    id_date = b.add_digit_set(d_date)
    
    _, _, days = make_day_name_images(FONT_BAHNSCHRIFT, 18, color=(240, 240, 245, 255), pad_w=4, pad_h=2)
    b.add_day_name(days, 302, 222)
    b.add_day_num(id_date, [(350, 222), (362, 222)])
    
    # Analog Hands
    im_h, p_h = make_dauphine_hand(w=18, l_tip=130, l_tail=26)
    im_m, p_m = make_dauphine_hand(w=14, l_tip=190, l_tail=32)
    im_s, p_s = make_needle_hand(w=8, l_tip=215, l_tail=55, color=(210, 215, 225, 255))
    
    b.add_time_hand(im_h, 0, center_x=cx, center_y=cy, pivot_from_top=p_h)
    b.add_time_hand(im_m, 1, center_x=cx, center_y=cy, pivot_from_top=p_m)
    b.add_time_hand(im_s, 2, center_x=cx, center_y=cy, pivot_from_top=p_s)
    
    # Center Cap Overlay
    cap = make_center_cap(size=22, fill_color=(40, 44, 52, 255), ring_color=(200, 205, 215, 255), pip_color=(255, 255, 255, 255))
    b.add_overlay_image(cap, cx - 11, cy - 11)
    
    # Preview
    prev = bg.copy()
    pd = ImageDraw.Draw(prev)
    pd.text((302, 222), "MON", fill=(240, 240, 245, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 18))
    pd.text((350, 222), "06", fill=(240, 240, 245, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 20))
    # Draw sample hands (10:10)
    for ang, hand, piv in [(305, im_h, p_h), (60, im_m, p_m), (160, im_s, p_s)]:
        rot = hand.rotate(-ang, expand=True, resample=Image.Resampling.BICUBIC)
        # compute center offset
        rot_cx = rot.width / 2.0
        rot_cy = rot.height / 2.0
        # original pivot relative to center: (0, piv - hand.height/2.0)
        orig_dy = piv - (hand.height / 2.0)
        rad = math.radians(ang)
        # rotated delta
        r_dx = -orig_dy * math.sin(rad)
        r_dy = orig_dy * math.cos(rad)
        top_x = int(cx - (rot_cx + r_dx))
        top_y = int(cy - (rot_cy + r_dy))
        prev.paste(rot, (top_x, top_y), rot)
    prev.paste(cap, (cx - 11, cy - 11), cap)
    
    b.set_preview(prev.resize((280, 280), Image.Resampling.LANCZOS))
    return b.build_and_pack(api_ver=35)


# ============================================================================
# WATCHFACE 5: EASY G1 SPORT RING
# ============================================================================

def build_05_easy_g1_sport_ring():
    b = WatchfaceBuilder("05_easy_g1_sport_ring")
    
    cx, cy = 233, 233
    bg = Image.new("RGBA", (466, 466), (0, 0, 0, 255))
    d = ImageDraw.Draw(bg)
    
    # Neon progress rings
    d.arc([16, 16, 450, 450], start=-90, end=190, fill=(0, 229, 255, 255), width=5)
    d.arc([24, 24, 442, 442], start=-90, end=120, fill=(0, 230, 118, 255), width=4)
    
    # Complication icons
    # Top battery bolt
    d.polygon([(218, 55), (223, 55), (220, 61), (225, 61), (217, 69), (219, 63), (215, 63)], fill=(255, 214, 0, 255))
    # Left red heart
    d.polygon([(78, 226), (82, 221), (87, 226), (82, 233)], fill=(255, 23, 68, 255))
    d.polygon([(83, 226), (88, 221), (93, 226), (88, 233)], fill=(255, 23, 68, 255))
    # Bottom footsteps
    d.ellipse([192, 375, 197, 380], fill=(0, 229, 255, 255))
    d.ellipse([198, 375, 203, 380], fill=(0, 229, 255, 255))
    d.ellipse([194, 382, 202, 388], fill=(0, 229, 255, 255))
    
    # Date dot
    d.ellipse([246, 102, 249, 105], fill=(255, 255, 255, 255))
    
    b.set_background(bg)
    
    # Digits
    _, _, d_h = make_uniform_digit_set(FONT_BAHNSCHRIFT, 88, color=(255, 255, 255, 255), pad_w=2, pad_h=4)
    _, _, d_m = make_uniform_digit_set(FONT_BAHNSCHRIFT, 88, color=(0, 229, 255, 255), pad_w=2, pad_h=4)
    _, _, d_date = make_uniform_digit_set(FONT_BAHNSCHRIFT, 22, color=(255, 255, 255, 255), pad_w=2, pad_h=2)
    _, _, d_data = make_uniform_digit_set(FONT_BAHNSCHRIFT, 24, color=(255, 255, 255, 255), pad_w=2, pad_h=2)
    
    id_h = b.add_digit_set(d_h)
    id_m = b.add_digit_set(d_m)
    id_date = b.add_digit_set(d_date)
    id_data = b.add_digit_set(d_data)
    
    # Big Stacked Time
    b.add_time_num((id_h, id_h, id_m, id_m), [
        (155, 125), (220, 125),
        (155, 230), (220, 230)
    ])
    
    # Day Name & Date
    _, _, days = make_day_name_images(FONT_BAHNSCHRIFT, 22, color=(255, 255, 255, 255), pad_w=4, pad_h=2)
    b.add_day_name(days, 155, 88)
    b.add_day_num(id_date, [(222, 88), (234, 88)])
    b.add_month_num(id_date, [(254, 88), (266, 88)])
    
    # Complications
    bars = make_battery_bars(w=48, h=16, border_color=(120, 120, 120, 255), fill_color=(255, 214, 0, 255))
    b.add_bar_display(bars, 230, 56)
    
    b.add_heart_rate_num(id_data, 100, 220, align=0)
    b.add_steps_num(id_data, 215, 370, align=0)
    
    weather_icons = get_weather_icons(32, 32)
    b.add_weather(weather_icons, 320, 215)
    temp_syms = make_temp_symbols(FONT_BAHNSCHRIFT, 22, color=(255, 255, 255, 255))
    b.add_temp_num(id_data, temp_syms, 355, 220)
    
    # Preview
    prev = bg.copy()
    pd = ImageDraw.Draw(prev)
    pd.text((155, 125), "09", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 88))
    pd.text((155, 230), "28", fill=(0, 229, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 88))
    pd.text((155, 88), "VR", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 22))
    pd.text((222, 88), "12", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 22))
    pd.text((254, 88), "06", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 22))
    prev.paste(bars[7], (230, 56), bars[7])
    pd.text((100, 220), "80", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 24))
    prev.paste(weather_icons[0], (320, 215), weather_icons[0])
    pd.text((355, 220), "28°C", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 22))
    pd.text((215, 370), "8532", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 24))
    
    b.set_preview(prev.resize((280, 280), Image.Resampling.LANCZOS))
    return b.build_and_pack(api_ver=35)


# ============================================================================
# WATCHFACE 6: CAZZIO CHRONOGRAPH RETRO DATA
# ============================================================================

def build_06_cazzio_chronograph_retro():
    b = WatchfaceBuilder("06_cazzio_chronograph_retro")
    
    bg = Image.new("RGBA", (466, 466), (18, 20, 22, 255))
    d = ImageDraw.Draw(bg)
    d.ellipse([10, 10, 456, 456], outline=(36, 40, 45, 255), width=3)
    
    # Header
    f_cazzio = ImageFont.truetype(FONT_ARIAL_BD, 22)
    f_chrono = ImageFont.truetype(FONT_BAHNSCHRIFT, 13)
    d.text((233, 48), "CAZZIO", fill=(255, 255, 255, 255), font=f_cazzio, anchor="mm")
    d.text((233, 70), "CHRONOGRAPH", fill=(255, 160, 0, 255), font=f_chrono, anchor="mm")
    
    # Upper twin stripes
    d.line([(100, 85), (366, 85)], fill=(255, 45, 45, 255), width=3)
    d.line([(100, 91), (366, 91)], fill=(0, 229, 255, 255), width=3)
    
    # Weekday text ribbon
    f_rib = ImageFont.truetype(FONT_BAHNSCHRIFT, 12)
    d.text((233, 108), "MON  TUE  WED  THU  FRI  SAT  SUN", fill=(140, 145, 150, 255), font=f_rib, anchor="mm")
    
    # LCD Box
    lx, ly, lw, lh = 85, 126, 296, 160
    d.rounded_rectangle([lx, ly, lx + lw, ly + lh], radius=14, fill=(238, 242, 236, 255), outline=(60, 65, 70, 255), width=2)
    
    # LCD labels
    d.text((345, 145), "12H", fill=(30, 35, 30, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 11), anchor="mm")
    d.text((100, 205), "PROGRESS", fill=(70, 75, 70, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 9))
    d.rectangle([223, 202, 227, 208], fill=(30, 35, 30, 255))
    d.rectangle([223, 220, 227, 226], fill=(30, 35, 30, 255))
    
    # Lower twin stripes
    d.line([(100, 298), (366, 298)], fill=(0, 229, 255, 255), width=3)
    d.line([(100, 304), (366, 304)], fill=(255, 45, 45, 255), width=3)
    
    # Dashboard column labels
    f_dash_lbl = ImageFont.truetype(FONT_BAHNSCHRIFT, 14)
    d.text((115, 320), "KCAL", fill=(255, 160, 0, 255), font=f_dash_lbl, anchor="mm")
    d.text((195, 320), "KM", fill=(255, 160, 0, 255), font=f_dash_lbl, anchor="mm")
    d.text((275, 320), "STEP", fill=(255, 160, 0, 255), font=f_dash_lbl, anchor="mm")
    d.text((355, 320), "PULS", fill=(255, 160, 0, 255), font=f_dash_lbl, anchor="mm")
    
    d.text((233, 420), "GARMIN", fill=(100, 105, 110, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 14), anchor="mm")
    b.set_background(bg)
    
    # 7-segment time digits
    _, _, d_time = make_7segment_digit_set(32, 58, color=(20, 25, 20, 255), ghost_color=(190, 198, 185, 70), slant=0.06, t=5)
    _, _, d_small = make_7segment_digit_set(13, 22, color=(20, 25, 20, 255), ghost_color=(190, 198, 185, 70), slant=0.06, t=2)
    _, _, d_dash = make_uniform_digit_set(FONT_BAHNSCHRIFT, 22, color=(255, 255, 255, 255), pad_w=2, pad_h=2)
    
    id_t = b.add_digit_set(d_time)
    id_s = b.add_digit_set(d_small)
    id_dash = b.add_digit_set(d_dash)
    
    b.add_time_num((id_t, id_t, id_t, id_t), [
        (128, 185), (170, 185),
        (238, 185), (280, 185)
    ])
    
    # Day indicator bar / box on ribbon
    def make_day_ribbon():
        days_code = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
        order = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        xs = [118, 156, 195, 233, 272, 310, 348]
        imgs = []
        for d_name in days_code:
            im = Image.new("RGBA", (24, 18), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle([0, 0, 23, 17], radius=3, outline=(0, 229, 255, 255), fill=(0, 229, 255, 60), width=1)
            imgs.append(im)
        return imgs
    
    rib_imgs = make_day_ribbon()
    # Day name element positioned over active day
    b.add_day_name(rib_imgs, 221, 99)
    
    # Date inside LCD
    b.add_day_num(id_s, [(180, 138), (194, 138)])
    b.add_month_num(id_s, [(212, 138), (226, 138)])
    
    # Battery bar
    bars = make_battery_bars(w=42, h=15, border_color=(40, 45, 40, 255), fill_color=(40, 160, 60, 255))
    b.add_bar_display(bars, 102, 138)
    
    # Dashboard 4 columns
    b.add_kcal_num(id_dash, 100, 344, align=0)
    b.add_distance_num(id_dash, 180, 344, align=0)
    b.add_steps_num(id_dash, 258, 344, align=0)
    b.add_heart_rate_num(id_dash, 342, 344, align=0)
    
    # Preview
    prev = bg.copy()
    pd = ImageDraw.Draw(prev)
    prev.paste(d_time[1], (128, 185), d_time[1])
    prev.paste(d_time[2], (170, 185), d_time[2])
    prev.paste(d_time[3], (238, 185), d_time[3])
    prev.paste(d_time[8], (280, 185), d_time[8])
    prev.paste(rib_imgs[1], (144, 99), rib_imgs[1]) # TUE
    prev.paste(bars[5], (102, 138), bars[5])
    prev.paste(d_small[2], (180, 138), d_small[2])
    prev.paste(d_small[9], (194, 138), d_small[9])
    prev.paste(d_small[0], (212, 138), d_small[0])
    prev.paste(d_small[9], (226, 138), d_small[9])
    f_dash = ImageFont.truetype(FONT_BAHNSCHRIFT, 22)
    pd.text((115, 344), "0", fill=(255, 255, 255, 255), font=f_dash, anchor="mm")
    pd.text((195, 344), "0.0", fill=(255, 255, 255, 255), font=f_dash, anchor="mm")
    pd.text((275, 344), "0", fill=(255, 255, 255, 255), font=f_dash, anchor="mm")
    pd.text((355, 344), "80", fill=(255, 255, 255, 255), font=f_dash, anchor="mm")
    
    b.set_preview(prev.resize((280, 280), Image.Resampling.LANCZOS))
    return b.build_and_pack(api_ver=35)


# ============================================================================
# WATCHFACE 7: SKMEI HYBRID ANA-DIGI
# ============================================================================

def build_07_skmei_hybrid_anadigi():
    b = WatchfaceBuilder("07_skmei_hybrid_anadigi")
    
    cx, cy = 233, 233
    bg = Image.new("RGBA", (466, 466), (18, 22, 26, 255))
    d = ImageDraw.Draw(bg)
    
    # Outer tachymeter track
    d.ellipse([10, 10, 456, 456], outline=(35, 42, 50, 255), width=3)
    for m in range(60):
        rad = math.radians(m * 6 - 90)
        is_5m = (m % 5 == 0)
        r_out = 218
        r_in = 202 if is_5m else 210
        col = (240, 245, 255, 255) if is_5m else (100, 110, 125, 255)
        w = 3 if is_5m else 1
        d.line([(cx + r_out * math.cos(rad), cy + r_out * math.sin(rad)), (cx + r_in * math.cos(rad), cy + r_in * math.sin(rad))], fill=col, width=w)
    
    # Top trapezoid LCD window (y=70..135)
    poly_top = [(190, 70), (276, 70), (315, 135), (151, 135)]
    d.polygon(poly_top, fill=(220, 228, 218, 255), outline=(70, 80, 90, 255), width=2)
    # Flame icon
    d.polygon([(175, 95), (178, 88), (182, 95), (179, 102)], fill=(30, 35, 30, 255))
    # Heart icon
    d.polygon([(242, 95), (246, 88), (251, 95), (246, 102)], fill=(30, 35, 30, 255))
    d.text((233, 122), "WEEK DAY", fill=(50, 55, 50, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 11), anchor="mm")
    
    # Left teal polygon LCD window (x=75..185, y=150..215)
    poly_left = [(75, 175), (160, 150), (185, 215), (95, 215)]
    d.polygon(poly_left, fill=(195, 230, 226, 255), outline=(70, 80, 90, 255), width=2)
    d.text((110, 185), "KM", fill=(30, 45, 45, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 12))
    
    # Right silver polygon LCD window (x=281..391, y=150..215)
    poly_right = [(306, 150), (391, 175), (371, 215), (281, 215)]
    d.polygon(poly_right, fill=(220, 228, 218, 255), outline=(70, 80, 90, 255), width=2)
    d.text((345, 162), "SKMEI", fill=(30, 35, 30, 255), font=ImageFont.truetype(FONT_ARIAL_BD, 12), anchor="mm")
    d.text((345, 202), "25°C", fill=(40, 45, 40, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 12), anchor="mm")
    
    # Bottom curved LCD window (y=255..375)
    poly_bot = [(135, 255), (331, 255), (300, 370), (166, 370)]
    d.polygon(poly_bot, fill=(220, 228, 218, 255), outline=(70, 80, 90, 255), width=2)
    d.rectangle([223, 275, 227, 281], fill=(30, 35, 30, 255))
    d.rectangle([223, 293, 227, 299], fill=(30, 35, 30, 255))
    d.text((233, 358), "WR 50M", fill=(50, 55, 50, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 12), anchor="mm")
    
    b.set_background(bg)
    
    # Digits
    _, _, d_time = make_7segment_digit_set(34, 56, color=(20, 28, 20, 255), ghost_color=(185, 195, 180, 70), slant=0.06, t=5)
    _, _, d_small = make_7segment_digit_set(13, 22, color=(20, 28, 20, 255), ghost_color=(185, 195, 180, 70), slant=0.06, t=2)
    
    id_t = b.add_digit_set(d_time)
    id_s = b.add_digit_set(d_small)
    
    # Bottom LCD Digital Time
    b.add_time_num((id_t, id_t, id_t, id_t), [
        (142, 264), (180, 264),
        (238, 264), (276, 264)
    ])
    
    # Sub-dial metrics
    b.add_kcal_num(id_s, 190, 88, align=0)
    b.add_heart_rate_num(id_s, 256, 88, align=0)
    b.add_distance_num(id_s, 125, 180, align=0)
    b.add_steps_num(id_s, 310, 178, align=0)
    
    # Date on bottom LCD
    _, _, days = make_day_name_images(FONT_BAHNSCHRIFT, 16, color=(20, 28, 20, 255), pad_w=4, pad_h=2)
    b.add_day_name(days, 270, 328)
    b.add_month_num(id_s, [(185, 328), (198, 328)])
    b.add_day_num(id_s, [(216, 328), (229, 328)])
    
    # Tactical Analog Hands
    im_h, p_h = make_tactical_hand(w=20, l_tip=125, l_tail=25)
    im_m, p_m = make_tactical_hand(w=16, l_tip=180, l_tail=30)
    im_s, p_s = make_needle_hand(w=8, l_tip=215, l_tail=55, color=(235, 45, 45, 255))
    
    b.add_time_hand(im_h, 0, center_x=cx, center_y=cy, pivot_from_top=p_h)
    b.add_time_hand(im_m, 1, center_x=cx, center_y=cy, pivot_from_top=p_m)
    b.add_time_hand(im_s, 2, center_x=cx, center_y=cy, pivot_from_top=p_s)
    
    # Center Cap Overlay
    cap = make_center_cap(size=22, fill_color=(45, 50, 58, 255), ring_color=(120, 130, 140, 255), pip_color=(200, 205, 215, 255))
    b.add_overlay_image(cap, cx - 11, cy - 11)
    
    # Preview
    prev = bg.copy()
    pd = ImageDraw.Draw(prev)
    prev.paste(d_time[0], (142, 264), d_time[0])
    prev.paste(d_time[9], (180, 264), d_time[9])
    prev.paste(d_time[2], (238, 264), d_time[2])
    prev.paste(d_time[2], (276, 264), d_time[2])
    prev.paste(days[4], (270, 328), days[4]) # THU
    prev.paste(d_small[0], (185, 328), d_small[0])
    prev.paste(d_small[6], (198, 328), d_small[6])
    prev.paste(d_small[1], (216, 328), d_small[1])
    prev.paste(d_small[7], (229, 328), d_small[7])
    # Subdials
    prev.paste(d_small[0], (190, 88), d_small[0])
    prev.paste(d_small[7], (256, 88), d_small[7])
    prev.paste(d_small[2], (270, 88), d_small[2])
    prev.paste(d_small[0], (125, 180), d_small[0])
    prev.paste(d_small[0], (310, 178), d_small[0])
    # Hands (10:10)
    for ang, hand, piv in [(305, im_h, p_h), (60, im_m, p_m), (160, im_s, p_s)]:
        rot = hand.rotate(-ang, expand=True, resample=Image.Resampling.BICUBIC)
        rot_cx, rot_cy = rot.width / 2.0, rot.height / 2.0
        orig_dy = piv - (hand.height / 2.0)
        rad = math.radians(ang)
        r_dx, r_dy = -orig_dy * math.sin(rad), orig_dy * math.cos(rad)
        top_x, top_y = int(cx - (rot_cx + r_dx)), int(cy - (rot_cy + r_dy))
        prev.paste(rot, (top_x, top_y), rot)
    prev.paste(cap, (cx - 11, cy - 11), cap)
    
    b.set_preview(prev.resize((280, 280), Image.Resampling.LANCZOS))
    return b.build_and_pack(api_ver=35)


# ============================================================================
# WATCHFACE 8: GARMIN OUTLINE NEON ANALOG
# ============================================================================

def build_08_garmin_outline_neon_analog():
    b = WatchfaceBuilder("08_garmin_outline_neon_analog")
    
    cx, cy = 233, 233
    bg = Image.new("RGBA", (466, 466), (8, 13, 26, 255))
    d = ImageDraw.Draw(bg)
    
    # Radial guilloché ribs
    for i in range(120):
        rad = math.radians(i * 3)
        x2 = cx + 225 * math.cos(rad)
        y2 = cy + 225 * math.sin(rad)
        d.line([(cx, cy), (x2, y2)], fill=(15, 24, 46, 255), width=1)
        
    d.ellipse([10, 10, 456, 456], outline=(25, 38, 70, 255), width=2)
    
    # Big tubular neon outline numerals (12, 3, 6, 9)
    f_neon = ImageFont.truetype(FONT_BAHNSCHRIFT, 68)
    
    def draw_neon_text(text, x, y, outer_col, tube_col):
        # Outer glow
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                if dx*dx + dy*dy <= 16:
                    d.text((x + dx, y + dy), text, fill=outer_col, font=f_neon, anchor="mm")
        # Inner glowing tube
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx*dx + dy*dy <= 4:
                    d.text((x + dx, y + dy), text, fill=tube_col, font=f_neon, anchor="mm")
        # Hollow dark core
        d.text((x, y), text, fill=(8, 13, 26, 255), font=f_neon, anchor="mm")
        
    draw_neon_text("12", cx, 80, (0, 229, 255, 255), (57, 255, 20, 255))
    draw_neon_text("3", 385, cy, (57, 255, 20, 255), (255, 235, 59, 255))
    draw_neon_text("6", cx, 385, (0, 180, 255, 255), (0, 235, 255, 255))
    draw_neon_text("9", 80, cy, (0, 229, 255, 255), (57, 255, 20, 255))
    
    # Complication icons
    # Top-left runner
    d.ellipse([135, 142, 140, 147], fill=(255, 255, 255, 255))
    d.line([(137, 147), (135, 156)], fill=(255, 255, 255, 255), width=2)
    # Top-right VO2 label
    d.text((330, 142), "VO2", fill=(140, 150, 175, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 14), anchor="mm")
    
    d.text((233, 420), "GARMIN", fill=(100, 115, 145, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 13), anchor="mm")
    b.set_background(bg)
    
    # Digits
    _, _, d_data = make_uniform_digit_set(FONT_BAHNSCHRIFT, 22, color=(255, 255, 255, 255), pad_w=2, pad_h=2)
    id_data = b.add_digit_set(d_data)
    
    b.add_distance_num(id_data, 125, 156, align=0)
    b.add_heart_rate_num(id_data, 318, 156, align=0)
    
    # Day name & Date in bottom-right quadrant
    _, _, days = make_day_name_images(FONT_BAHNSCHRIFT, 20, color=(255, 255, 255, 255), pad_w=4, pad_h=2)
    b.add_day_name(days, 305, 305)
    b.add_day_num(id_data, [(312, 328), (324, 328)])
    
    # Battery Bar in bottom-left quadrant
    bars = make_battery_bars(w=46, h=16, border_color=(80, 95, 125, 255), fill_color=(44, 245, 125, 255))
    b.add_bar_display(bars, 115, 315)
    
    # Neon Analog Hands
    im_h, p_h = make_neon_hand(w=16, l_tip=128, l_tail=26, glow_color=(44, 245, 125, 255), core_color=(230, 255, 240, 255))
    im_m, p_m = make_neon_hand(w=12, l_tip=188, l_tail=30, glow_color=(0, 229, 255, 255), core_color=(220, 255, 255, 255))
    im_s, p_s = make_needle_hand(w=8, l_tip=215, l_tail=55, color=(44, 245, 125, 255))
    
    b.add_time_hand(im_h, 0, center_x=cx, center_y=cy, pivot_from_top=p_h)
    b.add_time_hand(im_m, 1, center_x=cx, center_y=cy, pivot_from_top=p_m)
    b.add_time_hand(im_s, 2, center_x=cx, center_y=cy, pivot_from_top=p_s)
    
    # Center Cap
    cap = make_center_cap(size=20, fill_color=(20, 28, 45, 255), ring_color=(44, 245, 125, 255), pip_color=(44, 245, 125, 255))
    b.add_overlay_image(cap, cx - 10, cy - 10)
    
    # Preview
    prev = bg.copy()
    pd = ImageDraw.Draw(prev)
    pd.text((125, 156), "0.0", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 22))
    pd.text((318, 156), "58", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 22))
    pd.text((305, 305), "WED", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 20))
    pd.text((312, 328), "10", fill=(255, 255, 255, 255), font=ImageFont.truetype(FONT_BAHNSCHRIFT, 22))
    prev.paste(bars[10], (115, 315), bars[10])
    # Hands (10:10)
    for ang, hand, piv in [(305, im_h, p_h), (60, im_m, p_m), (160, im_s, p_s)]:
        rot = hand.rotate(-ang, expand=True, resample=Image.Resampling.BICUBIC)
        rot_cx, rot_cy = rot.width / 2.0, rot.height / 2.0
        orig_dy = piv - (hand.height / 2.0)
        rad = math.radians(ang)
        r_dx, r_dy = -orig_dy * math.sin(rad), orig_dy * math.cos(rad)
        top_x, top_y = int(cx - (rot_cx + r_dx)), int(cy - (rot_cy + r_dy))
        prev.paste(rot, (top_x, top_y), rot)
    prev.paste(cap, (cx - 10, cy - 10), cap)
    
    b.set_preview(prev.resize((280, 280), Image.Resampling.LANCZOS))
    return b.build_and_pack(api_ver=35)


# ============================================================================
# MASTER BUILDER
# ============================================================================

def build_all():
    print("=" * 60)
    print("BUILDING 8 CUSTOM WATCHFACES FOR BOZLUN B71 (466x466)")
    print("=" * 60)
    builders = [
        ("01_raster_swiss_grid", build_01_raster_swiss_grid),
        ("02_khnst02_minimal_digital", build_02_khnst02_minimal_digital),
        ("03_casio_retro_lcd", build_03_casio_retro_lcd),
        ("04_minimalist_roman_analog", build_04_minimalist_roman_analog),
        ("05_easy_g1_sport_ring", build_05_easy_g1_sport_ring),
        ("06_cazzio_chronograph_retro", build_06_cazzio_chronograph_retro),
        ("07_skmei_hybrid_anadigi", build_07_skmei_hybrid_anadigi),
        ("08_garmin_outline_neon_analog", build_08_garmin_outline_neon_analog),
    ]
    results = []
    for name, fn in builders:
        try:
            bin_p = fn()
            sz = os.path.getsize(bin_p)
            with open(bin_p, "rb") as f:
                b_data = f.read()
            crc = wt.moyoung_crc16(b_data)
            results.append((name, bin_p, sz, crc, "OK"))
        except Exception as e:
            import traceback
            traceback.print_exc()
            results.append((name, "", 0, 0, f"ERR: {e}"))
            
    print("\n" + "=" * 60)
    print("SUMMARY RESULTS:")
    print("=" * 60)
    for name, bin_p, sz, crc, status in results:
        if status == "OK":
            print(f"[{status}] {name:32s} | Size: {sz:7d} B | CRC-16: 0x{crc:04X} | Bin: {bin_p}")
        else:
            print(f"[{status}] {name:32s}")
            
    return results


if __name__ == "__main__":
    build_all()
