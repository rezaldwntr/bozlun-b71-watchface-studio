import asyncio
import os
import sys
import struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bleak import BleakClient
import watchface_tool as wt

ADDR = "F7:BF:47:B8:BA:82"
FEE1 = "0000fee1-0000-1000-8000-00805f9b34fb"
FEE2 = "0000fee2-0000-1000-8000-00805f9b34fb"
FEE3 = "0000fee3-0000-1000-8000-00805f9b34fb"
FEE6 = "0000fee6-0000-1000-8000-00805f9b34fb"

BIN_PATH = "custom_watchfaces/03_casio_retro_lcd/03_casio_retro_lcd.bin"

async def main():
    with open(BIN_PATH, "rb") as f:
        data = f.read()
    file_size = len(data)
    crc = wt.moyoung_crc16(data)
    print(f"File: {BIN_PATH}, Size: {file_size} bytes, CRC-16: 0x{crc:04X}")

    print(f"Connecting to {ADDR}...")
    async with BleakClient(ADDR) as client:
        print(f"Connected: {client.is_connected}")

        def handle_rx(sender, rx_data):
            print(f"  <<< [FEE3 RX] {rx_data.hex()} (len={len(rx_data)})")

        await client.start_notify(FEE3, handle_rx)
        print("[+] Subscribed to FEE3 notifications")

        # 1. Query Packet Length (0xBA 0x01)
        # [0xFE, 0xEA, 0x20, 0x06, 0xBA, 0x01]
        pkt_len_query = bytes([0xFE, 0xEA, 0x20, 0x06, 0xBA, 0x01])
        print(f"\n[*] Sending Query Packet Length (0xBA 0x01): {pkt_len_query.hex()}")
        await client.write_gatt_char(FEE2, pkt_len_query, response=False)
        await asyncio.sleep(0.5)

        # 2. Send Start Watchface Transfer (0x74, 4-byte BE size)
        # [0xFE, 0xEA, 0x20, 0x09, 0x74, (size>>24)&0xff, (size>>16)&0xff, (size>>8)&0xff, size&0xff]
        start_pkt = bytearray([0xFE, 0xEA, 0x20, 0x09, 0x74])
        start_pkt.extend(struct.pack(">I", file_size))
        print(f"\n[*] Sending Start Watchface Transfer (0x74): {start_pkt.hex()}")
        await client.write_gatt_char(FEE2, bytes(start_pkt), response=False)
        
        print("\n[*] Waiting 5 seconds for watch to request block 0...")
        await asyncio.sleep(5.0)

if __name__ == "__main__":
    asyncio.run(main())
