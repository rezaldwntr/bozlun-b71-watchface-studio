import asyncio
from bleak import BleakClient

ADDR = "F7:BF:47:B8:BA:82"
FEE2 = "0000fee2-0000-1000-8000-00805f9b34fb"
FEE3 = "0000fee3-0000-1000-8000-00805f9b34fb"

async def main():
    print(f"Connecting to {ADDR}...")
    async with BleakClient(ADDR) as client:
        print(f"Connected: {client.is_connected}")

        def on_notify(sender, data):
            print(f"  <<< [FEE3] {data.hex()} (len={len(data)})")

        await client.start_notify(FEE3, on_notify)

        # 1. Send WatchFace ID 14698 (hu9.a(14698, False)):
        # bArr = [17, 0x39, 0x6A, 0x00, 0x00]
        # Packet: [0xFE, 0xEA, 0x20, 0x0A, 0xB4, 0x11, 0x39, 0x6A, 0x00, 0x00]
        id_pkt = bytes([0xFE, 0xEA, 0x20, 0x0A, 0xB4, 0x11, 0x39, 0x6A, 0x00, 0x00])
        print(f"[*] Sending sendJieliWatchFaceId (14698): {id_pkt.hex()}")
        await client.write_gatt_char(FEE2, id_pkt, response=False)
        await asyncio.sleep(1.0)

        # 2. Send Display WatchFace Index 4 (hu9.b(4)):
        # Packet: [0xFE, 0xEA, 0x20, 0x06, 0x19, 0x04]
        disp_pkt = bytes([0xFE, 0xEA, 0x20, 0x06, 0x19, 0x04])
        print(f"[*] Sending sendDisplayWatchFace (4): {disp_pkt.hex()}")
        await client.write_gatt_char(FEE2, disp_pkt, response=False)
        await asyncio.sleep(1.0)

        # 3. Also try sending slot 0, then slot 4 (toggle refresh)
        print("[*] Waiting 3 seconds for watch responses...")
        await asyncio.sleep(3.0)

if __name__ == "__main__":
    asyncio.run(main())
