import struct

b = open("apk/b71_official_14698.bin", "rb").read()
print(f"Total size: {len(b)} bytes")

# In b71_official_14698.bin:
# Hex: 81 0b 46 6a 39 01 00 00 00 01 00 f0 00 18 01 40 01
# Let's inspect bytes:
# [0]: 0x81, [1]: 0x0B, [2]: 0x46, [3]: 0x6A, [4..7]: 0x00000139 (313)
# [8..9]: 0x0100 (256), [10..11]: 0xf000? Wait, or [8..11] uint32?
# Let's print out all candidate structures!

print("Bytes 0..48:")
for i in range(0, 48, 4):
    u32 = struct.unpack_from("<I", b, i)[0]
    u16_a = struct.unpack_from("<H", b, i)[0]
    u16_b = struct.unpack_from("<H", b, i+2)[0]
    print(f"Offset {i:2d}: hex={b[i:i+4].hex()} | u32={u32:10d} (0x{u32:08x}) | u16=({u16_a}, {u16_b})")
