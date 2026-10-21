import asyncio
import sys
from bleak import BleakClient

ADDR = "F7:BF:47:B8:BA:82"
FEE2 = "0000fee2-0000-1000-8000-00805f9b34fb"

async def switch_face(slot: int):
    print(f"Connecting to {ADDR}...")
    async with BleakClient(ADDR) as client:
        pkt = bytes([0xFE, 0xEA, 0x20, 0x06, 0x19, slot & 0xFF])
        print(f"[*] Sending Switch Watchface to slot {slot}: {pkt.hex()}")
        await client.write_gatt_char(FEE2, pkt, response=False)
        await asyncio.sleep(1.0)
        print(f"[+] Switched to slot {slot}!")

if __name__ == "__main__":
    slot = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    asyncio.run(switch_face(slot))
