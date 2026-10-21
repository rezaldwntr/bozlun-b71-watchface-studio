import asyncio
from bleak import BleakClient

ADDR = "F7:BF:47:B8:BA:82"
FEE2 = "0000fee2-0000-1000-8000-00805f9b34fb"
FEE3 = "0000fee3-0000-1000-8000-00805f9b34fb"

async def main():
    async with BleakClient(ADDR) as client:
        def on_rx(sender, data):
            print(f"  <<< [FEE3 RX] {data.hex()} (len={len(data)})")
            if len(data) >= 5 and data[0] == 0xFE and data[1] == 0xEA:
                cmd = data[4]
                payload = data[5:]
                print(f"      Cmd: 0x{cmd:02X}, Payload: {payload.hex()}")

        await client.start_notify(FEE3, on_rx)

        # 1. Query WatchFace List (0xA6 0x01)
        pkt_list = bytes([0xFE, 0xEA, 0x20, 0x06, 0xA6, 0x01])
        print(f"[*] Sending Query WatchFace List (0xA6 0x01): {pkt_list.hex()}")
        await client.write_gatt_char(FEE2, pkt_list, response=False)
        await asyncio.sleep(1.0)

        # 2. Query Support WatchFace (0x84)
        pkt_supp = bytes([0xFE, 0xEA, 0x20, 0x05, 0x84])
        print(f"[*] Sending Query Support WatchFace (0x84): {pkt_supp.hex()}")
        await client.write_gatt_char(FEE2, pkt_supp, response=False)
        await asyncio.sleep(1.0)

        # 3. Query Display WatchFace (0x29)
        pkt_disp = bytes([0xFE, 0xEA, 0x20, 0x05, 0x29])
        print(f"[*] Sending Query Display WatchFace (0x29): {pkt_disp.hex()}")
        await client.write_gatt_char(FEE2, pkt_disp, response=False)
        await asyncio.sleep(1.0)

        # 4. Query WatchFace Screen Info (0xB4 0x14)
        pkt_screen = bytes([0xFE, 0xEA, 0x20, 0x06, 0xB4, 0x14])
        print(f"[*] Sending Query Screen Info (0xB4 0x14): {pkt_screen.hex()}")
        await client.write_gatt_char(FEE2, pkt_screen, response=False)
        await asyncio.sleep(1.0)

        print("[*] Waiting 2s...")
        await asyncio.sleep(2.0)

if __name__ == "__main__":
    asyncio.run(main())
