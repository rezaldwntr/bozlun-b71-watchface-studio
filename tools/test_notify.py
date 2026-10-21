import asyncio
from bleak import BleakClient

ADDR = "F7:BF:47:B8:BA:82"
FEE1 = "0000fee1-0000-1000-8000-00805f9b34fb"
FEE2 = "0000fee2-0000-1000-8000-00805f9b34fb"
FEE3 = "0000fee3-0000-1000-8000-00805f9b34fb"
FEA1 = "0000fea1-0000-1000-8000-00805f9b34fb"

async def main():
    print(f"Connecting to {ADDR}...")
    async with BleakClient(ADDR) as client:
        print(f"Connected: {client.is_connected}")

        def make_handler(name):
            def handler(sender, data):
                print(f"  <<< [{name}] {data.hex()} (len={len(data)})")
            return handler

        for name, uuid in [("FEE1", FEE1), ("FEE3", FEE3), ("FEA1", FEA1)]:
            try:
                await client.start_notify(uuid, make_handler(name))
                print(f"[+] Started notify on {name} ({uuid})")
            except Exception as e:
                print(f"[-] Could not start notify on {name}: {e}")

        # Send time sync first to establish active session
        import time
        from datetime import datetime, timezone, timedelta
        now = datetime.now()
        tz_gmt8 = timezone(timedelta(hours=8))
        ts_gmt8 = int(now.replace(tzinfo=tz_gmt8).timestamp())
        time_pkt = bytearray([0xFE, 0xEA, 0x20, 0x0A, 0x31]) + int(ts_gmt8).to_bytes(4, 'big') + bytes([8])
        print(f"\n[*] Sending Time Sync (0x31): {time_pkt.hex()}")
        await client.write_gatt_char(FEE2, time_pkt, response=False)
        await asyncio.sleep(0.5)

        # 1. Query Battery (0x03) - standard MoYoung
        query_bat = bytes([0xFE, 0xEA, 0x20, 0x05, 0x03])
        print(f"\n[*] Sending Query Battery (0x03): {query_bat.hex()}")
        await client.write_gatt_char(FEE2, query_bat, response=False)
        await asyncio.sleep(0.5)

        # 2. Query Current Watchface (0x29)
        query_wf = bytes([0xFE, 0xEA, 0x20, 0x05, 0x29])
        print(f"\n[*] Sending Query Display Watchface (0x29): {query_wf.hex()}")
        await client.write_gatt_char(FEE2, query_wf, response=False)
        await asyncio.sleep(0.5)

        # 3. Query JieLi DFU Packet Length (0xBA 0x01)
        pkt_len_query = bytes([0xFE, 0xEA, 0x20, 0x06, 0xBA, 0x01])
        print(f"\n[*] Sending Query Packet Length (0xBA 0x01): {pkt_len_query.hex()}")
        await client.write_gatt_char(FEE2, pkt_len_query, response=False)
        await asyncio.sleep(0.5)

        # 4. Query JieLi Watchface Info (0xBA 0x02)
        pkt_wf_query = bytes([0xFE, 0xEA, 0x20, 0x06, 0xBA, 0x02])
        print(f"\n[*] Sending Query Watchface Info (0xBA 0x02): {pkt_wf_query.hex()}")
        await client.write_gatt_char(FEE2, pkt_wf_query, response=False)
        await asyncio.sleep(0.5)

        # 5. Query Support Watchface (0xB4 0x00)
        pkt_supp = bytes([0xFE, 0xEA, 0x20, 0x06, 0xB4, 0x00])
        print(f"\n[*] Sending Query Support Watchface (0xB4 0x00): {pkt_supp.hex()}")
        await client.write_gatt_char(FEE2, pkt_supp, response=False)
        await asyncio.sleep(1.0)

        print("\n[*] Waiting 3 seconds for any incoming packets...")
        await asyncio.sleep(3.0)

if __name__ == "__main__":
    asyncio.run(main())
