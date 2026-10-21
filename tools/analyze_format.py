import struct
import glob

print("=== OFFICIAL B71 WATCHFACES ===")
for p in sorted(glob.glob("apk/b71_official_*.bin")):
    b = open(p, "rb").read()
    print(f"\nFile: {p} ({len(b):,} bytes)")
    print(f"Hex 0..32: {b[:32].hex()}")
    # Unpack as various types
    vals16 = [struct.unpack_from("<H", b, i)[0] for i in range(0, 32, 2)]
    print(f"U16 LE   : {vals16}")
    vals32 = [struct.unpack_from("<I", b, i)[0] for i in range(0, 32, 4)]
    print(f"U32 LE   : {vals32}")

print("\n=== SAMPLE JIELI 3000 ===")
b = open("apk/sample_jieli_3000.bin", "rb").read()
print(f"Hex 0..32: {b[:32].hex()}")
vals16 = [struct.unpack_from("<H", b, i)[0] for i in range(0, 32, 2)]
print(f"U16 LE   : {vals16}")
