#!/usr/bin/env python3
"""
Sync Time and Timezone for Bozlun B71 / MoYoung Smartwatches over BLE
"""

import os
import sys
import asyncio
import struct
import time
from datetime import datetime, timezone, timedelta
from bleak import BleakClient, BleakScanner

CHAR_TX  = "0000fee2-0000-1000-8000-00805f9b34fb"
CHAR_RX  = "0000fee1-0000-1000-8000-00805f9b34fb"
CHAR_BAT = "00002a19-0000-1000-8000-00805f9b34fb"
ADDR     = "F7:BF:47:B8:BA:82"


async def sync_time():
    print("=" * 60)
    print("SMARTWATCH TIME & TIMEZONE SYNCHRONIZER")
    print("=" * 60)
    print(f"Connecting to Bozlun B71 ({ADDR})...")

    async with BleakClient(ADDR) as client:
        if not client.is_connected:
            print("[!] Failed to connect to smartwatch.")
            return

        print("[+] Connected successfully!")

        # 1. Read battery
        try:
            bat = await client.read_gatt_char(CHAR_BAT)
            print(f"[+] Battery Level: {bat[0]}%")
        except Exception as e:
            print(f"[-] Battery read note: {e}")

        # 2. Subscribe to notifications
        rx_responses = []

        def on_notify(sender, data):
            hex_str = " ".join(f"{b:02x}" for b in data)
            print(f"    [BLE Response] {hex_str}")
            rx_responses.append(data)

        try:
            await client.start_notify(CHAR_RX, on_notify)
        except Exception as e:
            print(f"[-] Notify start note: {e}")

        # 3. Calculate time packet
        now = datetime.now()
        local_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[*] PC Local Time: {local_time_str}")

        is_dst = time.daylight and time.localtime().tm_isdst > 0
        utc_offset_sec = -(time.altzone if is_dst else time.timezone)
        utc_offset_hr = utc_offset_sec // 3600
        print(f"[*] Timezone Offset: UTC{'+' if utc_offset_hr >= 0 else ''}{utc_offset_hr} ({utc_offset_sec} seconds)")

        # In Da Fit, epoch is calculated as wall time interpreted in GMT+8:
        # SimpleDateFormat("yyyy-MM-dd HH:mm:ss").setTimeZone("GMT+8").parse(format)
        tz_gmt8 = timezone(timedelta(hours=8))
        ts_gmt8 = int(now.replace(tzinfo=tz_gmt8).timestamp())

        # Payload: 4 bytes big endian timestamp + 1 byte timezone (8)
        time_payload = struct.pack(">I", ts_gmt8) + bytes([max(0, min(24, utc_offset_hr))])
        # Packet: [0xFE, 0xEA, flags, len, 0x31, payload]
        time_pkt = bytearray([0xFE, 0xEA, 0x20, len(time_payload) + 5, 0x31]) + time_payload

        # Timezone Packet (0xBB = 187)
        # Payload: [0x07, 0x00, <offset_sec: 4 bytes LE>]
        tz_payload = bytearray([0x07, 0x00]) + struct.pack("<i", utc_offset_sec)
        tz_pkt = bytearray([0xFE, 0xEA, 0x20, len(tz_payload) + 5, 0xBB]) + tz_payload

        time_hex = " ".join(f"{b:02x}" for b in time_pkt)
        tz_hex = " ".join(f"{b:02x}" for b in tz_pkt)

        print(f"[*] Sending Time Sync packet (0x31): {time_hex}")
        await client.write_gatt_char(CHAR_TX, time_pkt, response=False)
        await asyncio.sleep(0.5)

        print(f"[*] Sending Timezone packet (0xBB): {tz_hex}")
        await client.write_gatt_char(CHAR_TX, tz_pkt, response=False)
        await asyncio.sleep(1.0)

        print("=" * 60)
        print("[+] Jam dan Zona Waktu smartwatch BERHASIL disinkronkan!")
        print(f"    Waktu jam tangan sekarang tepat: {local_time_str}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(sync_time())
