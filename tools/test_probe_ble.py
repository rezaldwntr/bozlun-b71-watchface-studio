import asyncio
import struct
from bleak import BleakClient

ADDR = "F7:BF:47:B8:BA:82"
CHAR_TX = "0000fee2-0000-1000-8000-00805f9b34fb"
CHAR_RX = "0000fee1-0000-1000-8000-00805f9b34fb"

async def main():
    print(f"Connecting to {ADDR}...")
    async with BleakClient(ADDR) as client:
        print(f"Connected: {client.is_connected}")

        # List all services & characteristics
        for s in client.services:
            print(f"\n[Service] {s.uuid} ({s.description})")
            for c in s.characteristics:
                props = ",".join(c.properties)
                print(f"  [Char] {c.uuid} ({props})")
                if "read" in c.properties:
                    try:
                        val = await client.read_gatt_char(c.uuid)
                        try:
                            val_str = val.decode("utf-8")
                            print(f"         Value (str): '{val_str}'")
                        except Exception:
                            print(f"         Value (hex): {val.hex()}")
                    except Exception as e:
                        print(f"         Read error: {e}")

        # Setup notification handler
        def handle_rx(sender, data):
            print(f"  <<< [RX NOTIFY] {data.hex()} (len={len(data)})")

        await client.start_notify(CHAR_RX, handle_rx)
        print("\n[*] Started notify on FEE1")

        # 1. Query Packet Length (0xBA 0x01)
        # Packet: [0xFE, 0xEA, 0x20, 0x06, 0xBA, 0x01]
        pkt_len_query = bytes([0xFE, 0xEA, 0x20, 0x06, 0xBA, 0x01])
        print(f"\n[*] Sending Query Packet Length (0xBA 0x01): {pkt_len_query.hex()}")
        await client.write_gatt_char(CHAR_TX, pkt_len_query, response=False)
        await asyncio.sleep(1.0)

        # 2. Query Watchface Info (0xBA 0x02)
        # Packet: [0xFE, 0xEA, 0x20, 0x06, 0xBA, 0x02]
        pkt_wf_query = bytes([0xFE, 0xEA, 0x20, 0x06, 0xBA, 0x02])
        print(f"\n[*] Sending Query Watchface Info (0xBA 0x02): {pkt_wf_query.hex()}")
        await client.write_gatt_char(CHAR_TX, pkt_wf_query, response=False)
        await asyncio.sleep(1.0)

        # 3. Query Device Display Watchface (0xB4 0x00)
        # hu9.d() -> z29.a(-76, [0x00]) -> [0xFE, 0xEA, 0x20, 0x06, 0xB4, 0x00]
        pkt_disp_query = bytes([0xFE, 0xEA, 0x20, 0x06, 0xB4, 0x00])
        print(f"\n[*] Sending Query Current Watchface (0xB4 0x00): {pkt_disp_query.hex()}")
        await client.write_gatt_char(CHAR_TX, pkt_disp_query, response=False)
        await asyncio.sleep(1.0)

        print("\n[*] Finished probe.")

if __name__ == "__main__":
    asyncio.run(main())
