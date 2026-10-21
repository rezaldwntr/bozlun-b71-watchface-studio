#!/usr/bin/env python3
"""
Da Fit / MoYoung / JieLi Smartwatch Watchface Toolkit (watchface_tool.py)
Target Hardware: Bozlun B71 (Firmware: MOY-7H75-2.0.3, Platform: JieLi JLI, LCM: 41)

Capabilities:
  1. info <file.bin>                 : Inspect binary watchface header, digit sets, and elements
  2. unpack <file.bin> <out_dir>     : Extract all RLE ARGB8565 images to PNG/BMP + watchface.json
  3. pack <in_dir> <out.bin>         : Compile watchface.json + edited PNG/BMP images into .bin
  4. download <face_id> [out_dir]    : Download watchface .bin & preview .png from MoYoung CDN
  5. search <width> <height> [start] : Search MoYoung CDN for watchfaces with target resolution
  6. crc16 <file.bin>                : Calculate MoYoung BLE transfer CRC-16 (init=0xFEEA)
"""

import os
import sys
import json
import zlib
import struct
import hashlib
import urllib.request

# ============================================================================
# 1. COLOR & IMAGE CODEC (ARGB8888 <-> ARGB8565 <-> MoYoung RleNew + PNG/BMP)
# ============================================================================

def rgb565_to_888(a: int, b: int):
    pixel = b | (a << 8)
    b8 = ((pixel & 0x001F) << 3) | ((pixel & 0x001C) >> 3)
    g8 = ((pixel & 0x07E0) >> 3) | ((pixel & 0x0600) >> 9)
    r8 = ((pixel & 0xF800) >> 8) | ((pixel & 0xE000) >> 13)
    return r8, g8, b8


def rgb888_to_565(r: int, g: int, b: int):
    val = ((b & 0xF8) >> 3) | ((g & 0xFC) << 3) | ((r & 0xF8) << 8)
    return (val >> 8) & 0xFF, val & 0xFF


def get_rle_blob_size(file_data: bytes, base_offset: int, height: int) -> int:
    if height == 0 or base_offset == 0 or base_offset >= len(file_data):
        return 0
    header_size = height * 4
    last_entry = base_offset + header_size - 4
    if last_entry + 4 > len(file_data):
        return 0
    last_offset = struct.unpack_from("<H", file_data, last_entry)[0]
    last_size = struct.unpack_from("<H", file_data, last_entry + 2)[0]
    last_offset += (last_size & 0x1F) << 16
    last_size = last_size >> 5
    image_size = last_offset + last_size
    return max(0, image_size - header_size)


def decompress_rle_to_rgba(rle_data: bytes, width: int, height: int) -> bytes:
    """Decompresses MoYoung RleNew (ARGB8565) into RGBA8888 bytes (width * height * 4)."""
    total_pixels = width * height
    out = bytearray(total_pixels * 4)
    idx_in = 0
    px_out = 0
    n = len(rle_data)
    while idx_in < n and px_out < total_pixels:
        cmd = rle_data[idx_in]
        idx_in += 1
        if cmd & 0x80:
            count = cmd & 0x7F
            if idx_in + 3 > n:
                break
            alpha = rle_data[idx_in]
            a565 = rle_data[idx_in + 1]
            b565 = rle_data[idx_in + 2]
            idx_in += 3
            r, g, b = rgb565_to_888(a565, b565)
            pixel_bytes = bytes((r, g, b, alpha))
            end_px = min(total_pixels, px_out + count)
            out[px_out * 4 : end_px * 4] = pixel_bytes * (end_px - px_out)
            px_out = end_px
        else:
            count = cmd
            for _ in range(count):
                if idx_in + 3 > n or px_out >= total_pixels:
                    break
                alpha = rle_data[idx_in]
                a565 = rle_data[idx_in + 1]
                b565 = rle_data[idx_in + 2]
                idx_in += 3
                r, g, b = rgb565_to_888(a565, b565)
                off = px_out * 4
                out[off] = r
                out[off + 1] = g
                out[off + 2] = b
                out[off + 3] = alpha
                px_out += 1
    return bytes(out)


def compress_rgba_to_rle(rgba: bytes, width: int, height: int) -> bytes:
    """Compresses RGBA8888 bytes into MoYoung RleNew (header + compressed ARGB8565 data)."""
    argb8565 = bytearray(width * height * 3)
    for i in range(width * height):
        r = rgba[i * 4]
        g = rgba[i * 4 + 1]
        b = rgba[i * 4 + 2]
        a = rgba[i * 4 + 3]
        hi, lo = rgb888_to_565(r, g, b)
        argb8565[i * 3] = a
        argb8565[i * 3 + 1] = hi
        argb8565[i * 3 + 2] = lo

    dest_header = bytearray()
    dest_data = bytearray()
    dest_offset = height * 4
    row_width = width * 3

    for y in range(height):
        row = argb8565[y * row_width : (y + 1) * row_width]
        row_dest = bytearray()
        offset = 0
        while offset <= row_width - 9:
            pa = row[offset : offset + 3]
            pb = row[offset + 3 : offset + 6]
            pc = row[offset + 6 : offset + 9]
            if pa == pb and pb == pc:
                rep_px = pa
                rep_count = 2
                offset += 6
                while rep_count < 127 and offset <= row_width - 3 and row[offset : offset + 3] == rep_px:
                    rep_count += 1
                    offset += 3
                row_dest.append(0x80 | rep_count)
                row_dest.extend(rep_px)
            else:
                nr_start = offset
                nr_count = 0
                while nr_count < 127:
                    if offset <= row_width - 9:
                        pa = row[offset : offset + 3]
                        pb = row[offset + 3 : offset + 6]
                        pc = row[offset + 6 : offset + 9]
                        if pa == pb and pb == pc:
                            break
                        nr_count += 1
                        offset += 3
                    else:
                        while offset < row_width:
                            if nr_count == 127:
                                row_dest.append(nr_count)
                                row_dest.extend(row[nr_start:offset])
                                nr_count = 0
                                nr_start = offset
                            nr_count += 1
                            offset += 3
                        break
                if nr_count > 0:
                    row_dest.append(nr_count)
                    row_dest.extend(row[nr_start:offset])
        rem = (row_width - offset) // 3
        if rem > 0:
            row_dest.append(rem)
            row_dest.extend(row[offset:row_width])

        row_size_shifted = len(row_dest) * 32
        b0 = dest_offset & 0xFF
        b1 = (dest_offset >> 8) & 0xFF
        b2 = ((dest_offset >> 16) & 0x1F) | (row_size_shifted & 0xFF)
        b3 = (row_size_shifted >> 8) & 0xFF
        dest_header.extend((b0, b1, b2, b3))
        dest_offset += len(row_dest)
        dest_data.extend(row_dest)

    return bytes(dest_header + dest_data)


def write_png(path: str, width: int, height: int, rgba: bytes):
    """Pure-Python RGBA PNG writer (zero external dependencies)."""
    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    raw_rows = bytearray()
    stride = width * 4
    for y in range(height):
        raw_rows.append(0)  # Filter type 0 (None)
        raw_rows.extend(rgba[y * stride : (y + 1) * stride])

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    compressed = zlib.compress(bytes(raw_rows), 9)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + make_chunk(b"IHDR", ihdr)
        + make_chunk(b"IDAT", compressed)
        + make_chunk(b"IEND", b"")
    )
    with open(path, "wb") as f:
        f.write(png_bytes)


def read_image_rgba(path: str):
    """Reads PNG or BMP into (width, height, rgba_bytes). Uses Pillow if available, else pure Python."""
    try:
        from PIL import Image
        img = Image.open(path).convert("RGBA")
        return img.width, img.height, img.tobytes()
    except ImportError:
        pass

    data = open(path, "rb").read()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        pos = 8
        width = height = 0
        idat = bytearray()
        while pos < len(data):
            length = struct.unpack(">I", data[pos : pos + 4])[0]
            ctype = data[pos + 4 : pos + 8]
            cdata = data[pos + 8 : pos + 8 + length]
            pos += 12 + length
            if ctype == b"IHDR":
                width, height, bit_depth, color_type = struct.unpack(">IIBB", cdata[:10])
                if bit_depth != 8 or color_type != 6:
                    raise ValueError("Pure-Python PNG reader requires 8-bit RGBA PNG (or install Pillow: pip install pillow)")
            elif ctype == b"IDAT":
                idat.extend(cdata)
            elif ctype == b"IEND":
                break
        raw = zlib.decompress(bytes(idat))
        stride = width * 4
        rgba = bytearray(width * height * 4)
        for y in range(height):
            ftype = raw[y * (stride + 1)]
            row = raw[y * (stride + 1) + 1 : (y + 1) * (stride + 1)]
            if ftype != 0:
                raise ValueError("Filtered PNG requires Pillow (pip install pillow)")
            rgba[y * stride : (y + 1) * stride] = row
        return width, height, bytes(rgba)
    raise ValueError(f"Unsupported image format for {path} (install Pillow: pip install pillow)")


# ============================================================================
# 2. ELEMENT DEFINITIONS & PARSER FOR MOYOUNG / JIELI WATCHFACE (.BIN)
# ============================================================================

ELEMENT_NAMES = {
    0: "image",
    2: "time_num",
    4: "day_name",
    5: "battery_fill",
    6: "heart_rate_num",
    7: "steps_num",
    8: "distance_num",
    9: "kcal_num",
    10: "time_hand",
    13: "day_num",
    14: "month_name",
    15: "month_num",
    17: "ampm",
    18: "bar_display",
    27: "weather",
    28: "decor_multi",
    29: "unknown_29",
    35: "dash",
}

FIXED_ELEMENT_SIZES = {
    0: 14,
    2: 34,
    4: 63,
    5: 42,
    6: 26,
    7: 26,
    8: 26,
    9: 17,
    10: 19,
    13: 12,
    14: 198,
    15: 12,
    17: 27,
    28: 32,
    29: 3,
    35: 10,
}


def get_element_size(b: bytes, pos: int) -> int:
    et = b[pos + 1]
    if et in FIXED_ELEMENT_SIZES:
        return FIXED_ELEMENT_SIZES[et]
    if et == 18:
        cnt = b[pos + 3]
        return 8 + cnt * 8
    if et == 27:
        cnt = b[pos + 2]
        return 7 + cnt * 8
    raise ValueError(f"Unknown element type {et} (0x{et:02x}) at offset 0x{pos:x}")


def get_element_owh_positions(b: bytes, pos: int, sz: int):
    """Returns list of relative offsets within the element (from pos) where 8-byte OWH structs reside."""
    et = b[pos + 1]
    if et == 0:
        return [6]
    if et == 4:
        return [7 + i * 8 for i in range(7)]
    if et == 5:
        return [6, 26, 34]
    if et == 10:
        return [7]
    if et == 14:
        return [6 + i * 8 for i in range(24)]
    if et == 17:
        return [11, 19]
    if et == 18:
        cnt = b[pos + 3]
        return [8 + i * 8 for i in range(cnt)]
    if et == 27:
        cnt = b[pos + 2]
        return [7 + i * 8 for i in range(cnt)]
    if et == 28:
        return [8 + i * 8 for i in range(3)]
    if et == 35:
        return [2]
    return []


def parse_watchface_bin(b: bytes):
    """Parses a MoYoung / Da Fit binary watchface into a structured dictionary."""
    if len(b) < 16:
        raise ValueError("File too small to be a valid watchface .bin")

    # Check if it's a Custom Background image file (starts with 0x06 FF FF FF)
    if b[1:4] == b"\xff\xff\xff" and b[0] in (0, 1, 2, 3, 4, 5, 6):
        payload_len = struct.unpack_from("<I", b, 4)[0]
        return {
            "format": "custom_background",
            "compression_type": b[0],
            "payload_length": payload_len,
            "actual_file_size": len(b),
        }

    api_ver, unk, prev_off, pw, ph, d_off, e_off = struct.unpack_from("<HHIHHHH", b, 0)
    num_digit_sets = (e_off - d_off - 2) // 83 if e_off > d_off else 0

    digit_sets = []
    pos = d_off + 2
    for d_idx in range(num_digit_sets):
        d_id = b[pos]
        owhs = []
        for g in range(10):
            off, w, h = struct.unpack_from("<IHH", b, pos + 1 + g * 8)
            owhs.append({"offset": off, "w": w, "h": h})
        d_unk = struct.unpack_from("<H", b, pos + 81)[0]
        digit_sets.append({"digit_set_id": d_id, "unknown": d_unk, "glyphs": owhs})
        pos += 83

    elements = []
    pos = e_off
    while pos < len(b) and b[pos] == 1:
        et = b[pos + 1]
        sz = get_element_size(b, pos)
        raw_elem = b[pos : pos + sz]
        owh_rels = get_element_owh_positions(b, pos, sz)
        owhs = []
        for rel in owh_rels:
            off, w, h = struct.unpack_from("<IHH", b, pos + rel)
            owhs.append({"rel_offset": rel, "offset": off, "w": w, "h": h})

        elem_info = {
            "e_type": et,
            "name": ELEMENT_NAMES.get(et, f"type_{et}"),
            "size": sz,
            "raw_hex": raw_elem.hex(),
            "owhs": owhs,
        }
        # Add human-friendly coordinate decoded fields for common elements
        if et in (0, 5):
            elem_info["x"], elem_info["y"] = struct.unpack_from("<HH", b, pos + 2)
        elif et == 2:
            elem_info["digit_sets"] = list(b[pos + 2 : pos + 6])
            elem_info["coords"] = [
                {"x": struct.unpack_from("<H", b, pos + 6 + i * 4)[0], "y": struct.unpack_from("<H", b, pos + 8 + i * 4)[0]}
                for i in range(4)
            ]
        elif et in (6, 7, 8, 9):
            elem_info["digit_set"] = b[pos + 2]
            elem_info["align"] = b[pos + 3]
            elem_info["x"], elem_info["y"] = struct.unpack_from("<HH", b, pos + 4)
        elif et in (13, 15):
            elem_info["digit_set"] = b[pos + 2]
            elem_info["align"] = b[pos + 3]
            elem_info["coords"] = [
                {"x": struct.unpack_from("<H", b, pos + 4 + i * 4)[0], "y": struct.unpack_from("<H", b, pos + 6 + i * 4)[0]}
                for i in range(2)
            ]
        elif et == 10:
            elem_info["hand_type"] = {0: "hour", 1: "minute", 2: "second"}.get(b[pos + 2], b[pos + 2])
            elem_info["pivot_x"], elem_info["pivot_y"] = struct.unpack_from("<HH", b, pos + 3)

        elements.append(elem_info)
        pos += sz

    return {
        "format": "watchface_bin",
        "file_size": len(b),
        "api_ver": api_ver,
        "unknown": unk,
        "preview": {"offset": prev_off, "w": pw, "h": ph},
        "d_offset": d_off,
        "e_offset": e_off,
        "digit_sets": digit_sets,
        "elements": elements,
    }


# ============================================================================
# 3. UNPACK & PACK WORKFLOW
# ============================================================================

def unpack_watchface(bin_path: str, out_dir: str):
    b = open(bin_path, "rb").read()
    meta = parse_watchface_bin(b)
    if meta["format"] != "watchface_bin":
        raise ValueError(f"Cannot unpack format: {meta['format']}")

    os.makedirs(out_dir, exist_ok=True)
    images_dir = os.path.join(out_dir, "images")
    raw_dir = os.path.join(out_dir, "raw_blobs")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)

    def extract_owh(off: int, w: int, h: int, name_prefix: str):
        if off == 0 or w == 0 or h == 0:
            return None
        hdr_sz = h * 4
        blob_sz = get_rle_blob_size(b, off, h)
        raw_blob = b[off : off + hdr_sz + blob_sz]
        rle_data = b[off + hdr_sz : off + hdr_sz + blob_sz]
        rgba = decompress_rle_to_rgba(rle_data, w, h)

        png_name = f"{name_prefix}.png"
        png_path = os.path.join(images_dir, png_name)
        write_png(png_path, w, h, rgba)

        png_sha256 = hashlib.sha256(open(png_path, "rb").read()).hexdigest()
        raw_name = f"{name_prefix}.rle"
        with open(os.path.join(raw_dir, raw_name), "wb") as rf:
            rf.write(raw_blob)

        return {
            "file": f"images/{png_name}",
            "raw_cache": f"raw_blobs/{raw_name}",
            "png_sha256": png_sha256,
            "orig_offset": off,
            "w": w,
            "h": h,
        }

    # 1. Extract Preview
    prev = meta["preview"]
    meta["preview"]["image"] = extract_owh(prev["offset"], prev["w"], prev["h"], "preview")

    # 2. Extract Digit Sets
    for d_idx, dset in enumerate(meta["digit_sets"]):
        for g_idx, g in enumerate(dset["glyphs"]):
            g["image"] = extract_owh(g["offset"], g["w"], g["h"], f"digits_{d_idx:02d}_{g_idx}")

    # 3. Extract Element Images
    for e_idx, el in enumerate(meta["elements"]):
        for o_idx, owh in enumerate(el["owhs"]):
            owh["image"] = extract_owh(
                owh["offset"], owh["w"], owh["h"], f"elem_{e_idx:02d}_{el['name']}_{o_idx:02d}"
            )

    json_path = os.path.join(out_dir, "watchface.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"[+] Successfully unpacked {bin_path} -> {out_dir}")
    print(f"    - Layout JSON : {json_path}")
    print(f"    - PNG Images  : {images_dir}")


def pad_4(buf: bytearray, pad_byte: int = 0xFF):
    rem = len(buf) % 4
    if rem != 0:
        buf.extend([pad_byte] * (4 - rem))


def pack_watchface(in_dir: str, out_bin_path: str):
    json_path = os.path.join(in_dir, "watchface.json")
    meta = json.load(open(json_path, "r", encoding="utf-8"))

    # Calculate header + digits + elements size first
    d_offset = 16
    num_d = len(meta["digit_sets"])
    e_offset = d_offset + (2 + num_d * 83 if num_d > 0 else 0)

    elem_total_len = sum(el["size"] for el in meta["elements"]) + 1  # +1 for 0x00 terminator
    hdr_end = e_offset + elem_total_len
    if hdr_end % 4 != 0:
        hdr_end += 4 - (hdr_end % 4)

    blob_section = bytearray()
    dedup_map = {}  # key -> new_offset

    def resolve_image_blob(img_info):
        if not img_info:
            return 0, 0, 0
        png_path = os.path.join(in_dir, img_info["file"])
        raw_path = os.path.join(in_dir, img_info.get("raw_cache", ""))
        cur_sha = hashlib.sha256(open(png_path, "rb").read()).hexdigest()

        # If PNG was NOT modified by user and raw_cache exists, reuse exact original RLE bytes!
        if cur_sha == img_info.get("png_sha256") and os.path.exists(raw_path):
            rle_blob = open(raw_path, "rb").read()
            w, h = img_info["w"], img_info["h"]
            dedup_key = ("orig", img_info.get("orig_offset"), rle_blob)
        else:
            w, h, rgba = read_image_rgba(png_path)
            rle_blob = compress_rgba_to_rle(rgba, w, h)
            dedup_key = ("new", rle_blob)

        if dedup_key in dedup_map:
            return dedup_map[dedup_key], w, h

        new_off = hdr_end + len(blob_section)
        blob_section.extend(rle_blob)
        pad_4(blob_section, 0xFF)
        dedup_map[dedup_key] = new_off
        return new_off, w, h

    # Note: Some watchfaces store element images before digit images or vice versa.
    # Let's sort all image descriptors by their original offset so we preserve exact ordering,
    # while still allowing edited PNGs!
    all_slots = []
    for d_idx, dset in enumerate(meta["digit_sets"]):
        for g_idx, g in enumerate(dset["glyphs"]):
            if g.get("image"):
                all_slots.append((g["image"].get("orig_offset", 0xFFFFFF), ("digit", d_idx, g_idx), g["image"]))
    for e_idx, el in enumerate(meta["elements"]):
        for o_idx, owh in enumerate(el["owhs"]):
            if owh.get("image"):
                all_slots.append((owh["image"].get("orig_offset", 0xFFFFFF), ("elem", e_idx, o_idx), owh["image"]))
    if meta["preview"].get("image"):
        all_slots.append((meta["preview"]["image"].get("orig_offset", 0xFFFFFFF), ("preview", 0, 0), meta["preview"]["image"]))

    all_slots.sort(key=lambda x: x[0])
    resolved = {}
    for _, slot_id, img_info in all_slots:
        resolved[slot_id] = resolve_image_blob(img_info)

    # Build Digits Table
    digits_buf = bytearray()
    if num_d > 0:
        digits_buf.extend((0x01, 0x01))
        for d_idx, dset in enumerate(meta["digit_sets"]):
            digits_buf.append(dset["digit_set_id"])
            for g_idx, g in enumerate(dset["glyphs"]):
                if g.get("image"):
                    off, w, h = resolved[("digit", d_idx, g_idx)]
                else:
                    off, w, h = 0, 0, 0
                digits_buf.extend(struct.pack("<IHH", off, w, h))
            digits_buf.extend(struct.pack("<H", dset["unknown"]))

    # Build Elements Table
    elems_buf = bytearray()
    for e_idx, el in enumerate(meta["elements"]):
        raw_el = bytearray.fromhex(el["raw_hex"])
        # Patch any edited coordinates for common types if modified in JSON
        et = el["e_type"]
        if et in (0, 5) and "x" in el and "y" in el:
            struct.pack_into("<HH", raw_el, 2, el["x"], el["y"])
        elif et == 2 and "coords" in el:
            for i, c in enumerate(el["coords"][:4]):
                struct.pack_into("<HH", raw_el, 6 + i * 4, c["x"], c["y"])
        elif et in (6, 7, 8, 9) and "x" in el and "y" in el:
            struct.pack_into("<HH", raw_el, 4, el["x"], el["y"])
        elif et in (13, 15) and "coords" in el:
            for i, c in enumerate(el["coords"][:2]):
                struct.pack_into("<HH", raw_el, 4 + i * 4, c["x"], c["y"])

        for o_idx, owh in enumerate(el["owhs"]):
            rel = owh["rel_offset"]
            if owh.get("image"):
                off, w, h = resolved[("elem", e_idx, o_idx)]
            else:
                off, w, h = 0, 0, 0
            struct.pack_into("<IHH", raw_el, rel, off, w, h)
        elems_buf.extend(raw_el)

    elems_buf.append(0x00)  # Terminator
    while (16 + len(digits_buf) + len(elems_buf)) % 4 != 0:
        elems_buf.append(0x00)

    prev_off, pw, ph = resolved.get(("preview", 0, 0), (0, meta["preview"]["w"], meta["preview"]["h"]))
    header_buf = struct.pack(
        "<HHIHHHH",
        meta["api_ver"],
        meta["unknown"],
        prev_off,
        pw,
        ph,
        d_offset,
        e_offset,
    )

    final_bin = header_buf + digits_buf + elems_buf + blob_section
    with open(out_bin_path, "wb") as f:
        f.write(final_bin)

    crc = moyoung_crc16(final_bin)
    print(f"[+] Packed watchface -> {out_bin_path} ({len(final_bin)} bytes, BLE CRC-16: 0x{crc:04X})")


# ============================================================================
# 4. MOYOUNG BLE CRC-16 & CDN DOWNLOADER / SEARCH
# ============================================================================

def moyoung_crc16(data: bytes, init: int = 0xFEEA) -> int:
    """Exact implementation of t29.java CRC-16 used by Da Fit BLE watchface transfer (0x74 / 0x6E)."""
    crc = init
    for b in data:
        i3 = (((crc & 0xFF) << 8) | ((crc & 0xFF00) >> 8)) ^ (b & 0xFF)
        i4 = i3 ^ ((i3 & 0xFF) >> 4)
        i5 = (i4 ^ ((i4 & 0xFF) << 12)) & 0xFFFF
        crc = (i5 ^ ((i5 & 0xFF) << 5)) & 0xFFFF
    return crc


def moyoung_decrypt_3des(data: bytes) -> bytes:
    """Decrypts Da Fit assets/config.txt or /v2/init-settings using 3DES-CBC (key=CBCDEFGHIJKLMNOPQRSTUVWX, iv=20160808)."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    cipher = Cipher(algorithms.TripleDES(b"CBCDEFGHIJKLMNOPQRSTUVWX"), modes.CBC(b"20160808"))
    dec = cipher.decryptor()
    out = dec.update(data) + dec.finalize()
    pad = out[-1]
    return out[:-pad] if 1 <= pad <= 8 else out


def download_face(face_id: int, out_dir: str = "."):
    os.makedirs(out_dir, exist_ok=True)
    url = f"https://api-cdn.moyoung.com/faces/new/{face_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "okhttp/4.9.0"})
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
    face = resp.get("face") or resp.get("data", {}).get("face") or resp
    file_url = face.get("file")
    prev_url = face.get("preview")
    if not file_url:
        print(f"[-] Face ID {face_id} not found or empty: {resp}")
        return None
    bin_path = os.path.join(out_dir, f"face_{face_id}.bin")
    png_path = os.path.join(out_dir, f"face_{face_id}_preview.png")
    urllib.request.urlretrieve(file_url, bin_path)
    if prev_url:
        urllib.request.urlretrieve(prev_url, png_path)
    print(f"[+] Downloaded face {face_id}:")
    print(f"    - BIN : {bin_path} ({os.path.getsize(bin_path)} bytes)")
    print(f"    - PNG : {png_path}")
    return bin_path


def search_faces(target_w: int, target_h: int, start_id: int = 5000, count: int = 30):
    print(f"[*] Scanning MoYoung CDN for {target_w}x{target_h} watchfaces (starting at ID {start_id})...")
    matches = []
    for fid in range(start_id, start_id + count):
        try:
            url = f"https://api-cdn.moyoung.com/faces/new/{fid}"
            req = urllib.request.Request(url, headers={"User-Agent": "okhttp/4.9.0"})
            resp = json.loads(urllib.request.urlopen(req, timeout=8).read().decode("utf-8"))
            face = resp.get("face") or resp.get("data", {}).get("face") or resp
            f_url = face.get("file")
            if not f_url:
                continue
            r2 = urllib.request.Request(f_url, headers={"User-Agent": "okhttp/4.9.0", "Range": "bytes=0-511"})
            head = urllib.request.urlopen(r2, timeout=8).read(512)
            api_ver, unk, prev_off, pw, ph, d_off, e_off = struct.unpack_from("<HHIHHHH", head, 0)
            if e_off + 14 <= len(head) and head[e_off] == 1 and head[e_off + 1] == 0:
                bg_w, bg_h = struct.unpack_from("<HH", head, e_off + 10)
            else:
                bg_w, bg_h = pw, ph
            print(f"  ID {fid}: bg={bg_w}x{bg_h} preview={pw}x{ph} api_ver={api_ver} url={f_url}")
            if bg_w == target_w and bg_h == target_h:
                matches.append((fid, f_url, face.get("preview")))
        except Exception:
            pass
    print(f"[+] Found {len(matches)} matching {target_w}x{target_h} watchfaces.")
    return matches


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()
    if cmd == "info":
        meta = parse_watchface_bin(open(sys.argv[2], "rb").read())
        print(json.dumps(meta, indent=2))
    elif cmd == "unpack":
        unpack_watchface(sys.argv[2], sys.argv[3])
    elif cmd == "pack":
        pack_watchface(sys.argv[2], sys.argv[3])
    elif cmd == "download":
        out = sys.argv[3] if len(sys.argv) > 3 else "."
        download_face(int(sys.argv[2]), out)
    elif cmd == "search":
        w, h = int(sys.argv[2]), int(sys.argv[3])
        start = int(sys.argv[4]) if len(sys.argv) > 4 else 5000
        cnt = int(sys.argv[5]) if len(sys.argv) > 5 else 30
        search_faces(w, h, start, cnt)
    elif cmd == "decrypt-config":
        dec = moyoung_decrypt_3des(open(sys.argv[2], "rb").read())
        open(sys.argv[3], "wb").write(dec)
        print(f"[+] Decrypted {sys.argv[2]} -> {sys.argv[3]} ({len(dec)} bytes)")
    elif cmd == "crc16":
        data = open(sys.argv[2], "rb").read()
        print(f"0x{moyoung_crc16(data):04X}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
