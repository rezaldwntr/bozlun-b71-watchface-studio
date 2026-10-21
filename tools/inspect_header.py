import struct

b = open("apk/b71_official_14698.bin", "rb").read()

# Let's inspect the first 64 bytes in detail
print("Header inspection:")
for i in range(0, 64, 4):
    u32_le = struct.unpack_from("<I", b, i)[0]
    u16_0 = struct.unpack_from("<H", b, i)[0]
    u16_1 = struct.unpack_from("<H", b, i+2)[0]
    b0, b1, b2, b3 = b[i:i+4]
    print(f"[{i:2d}..{i+3:2d}]: {b[i:i+4].hex()} | u16=({u16_0:5d}, {u16_1:5d}) | bytes=({b0}, {b1}, {b2}, {b3})")
