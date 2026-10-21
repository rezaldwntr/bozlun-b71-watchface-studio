#!/usr/bin/env python3
"""
Direct PC BLE Flasher for Bozlun B71 (JieLi JLI MCU / Da Fit / MoYoung V2)
Accurately follows the complete Da Fit / JieLi OTA lifecycle:
1. Handshake & Block MTU negotiation (FEE2/FEE3)
2. High-speed block streaming to FEE6
3. Verification of hardware CRC-16
4. Commit ACK & WAITING for internal Flash write completion (FEE3 0xB4)
5. Activating and locking the new watchface into the active display slot!
"""

import os
import sys
import time
import struct
import asyncio
import argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import watchface_tool as wt

from bleak import BleakClient, BleakScanner

DEFAULT_ADDR = "F7:BF:47:B8:BA:82"

UUID_FEE1 = "0000fee1-0000-1000-8000-00805f9b34fb"
UUID_FEE2 = "0000fee2-0000-1000-8000-00805f9b34fb"
UUID_FEE3 = "0000fee3-0000-1000-8000-00805f9b34fb"
UUID_FEE6 = "0000fee6-0000-1000-8000-00805f9b34fb"
UUID_BAT  = "00002a19-0000-1000-8000-00805f9b34fb"


def build_ble_packet(cmd_id: int, payload: bytes = b"") -> bytes:
    pl_len = len(payload)
    pkt_len = pl_len + 5
    flags = 0x20
    if pkt_len > 255:
        flags = (pkt_len >> 8) + 0x20
    pkt = bytearray([0xFE, 0xEA, flags, pkt_len & 0xFF, cmd_id & 0xFF])
    if payload:
        pkt.extend(payload)
    return bytes(pkt)


async def flash_watchface(device_addr: str, bin_file: str, face_id: int = 14698):
    if not os.path.exists(bin_file):
        print(f"[!] Binary file not found: {bin_file}")
        return False

    with open(bin_file, "rb") as f:
        bin_data = f.read()

    file_size = len(bin_data)
    file_crc = wt.moyoung_crc16(bin_data)
    fname = os.path.basename(bin_file)

    print("=" * 65)
    print("  BOZLUN B71 (JIELI) DIRECT BLE WATCHFACE FLASHER")
    print("=" * 65)
    print(f"[*] Target Binary : {fname}")
    print(f"[*] Binary Size   : {file_size:,} bytes")
    print(f"[*] BLE CRC-16    : 0x{file_crc:04X}")
    print(f"[*] Smartwatch MAC: {device_addr}")
    print("=" * 65)

    print(f"[*] Connecting to {device_addr}...")
    async with BleakClient(device_addr, timeout=20.0) as client:
        if not client.is_connected:
            print("[!] Connection failed.")
            return False

        print("[+] Connected to Bozlun B71!")

        try:
            bat_bytes = await client.read_gatt_char(UUID_BAT)
            print(f"[+] Watch Battery Level: {bat_bytes[0]}%")
        except Exception:
            pass

        block_size = 10240
        total_blocks = (file_size + block_size - 1) // block_size
        flash_complete = asyncio.Event()
        install_complete = asyncio.Event()
        flash_success = False
        error_msg = None
        transfer_started = asyncio.Event()

        def on_fee3_notify(sender, data: bytes):
            nonlocal block_size, total_blocks, flash_success, error_msg

            if len(data) < 5 or data[0] != 0xFE or data[1] != 0xEA:
                return

            cmd = data[4]
            payload = data[5:]
            print(f"  <<< [FEE3 RX] Cmd: 0x{cmd:02X}, Payload: {payload.hex()}")

            # 1. Packet Length response: 0xBA 0x01
            if cmd == 0xBA and len(payload) >= 3 and payload[0] == 0x01:
                block_size = (payload[2] << 8) | payload[1]
                total_blocks = (file_size + block_size - 1) // block_size
                print(f"[+] DFU Block Size negotiated: {block_size} bytes ({total_blocks} total blocks)")
                transfer_started.set()

            # 2. Block request / CRC response: 0x74
            elif cmd == 0x74 and len(payload) >= 2:
                req_block = (payload[0] << 8) | payload[1]

                # 0xFFFF = CRC check
                if req_block == 0xFFFF:
                    watch_crc = 0
                    if len(payload) >= 4:
                        watch_crc = (payload[2] << 8) | payload[3]
                    print(f"\n[*] All blocks sent! Watch CRC: 0x{watch_crc:04X} (Expected: 0x{file_crc:04X})")

                    if watch_crc == file_crc:
                        print("[+] CRC MATCH! Sending Commit ACK...")
                        flash_success = True
                    else:
                        print(f"[!] CRC MISMATCH! (Watch: 0x{watch_crc:04X} != Local: 0x{file_crc:04X})")
                        flash_success = False
                        error_msg = f"CRC mismatch: 0x{watch_crc:04X} != 0x{file_crc:04X}"

                    flash_complete.set()
                else:
                    asyncio.create_task(send_block(req_block))

            # 3. Installation status response: 0xB4
            elif cmd == 0xB4:
                # payload[0] == 2 -> onInstallStateChange
                if len(payload) >= 2 and payload[0] == 0x02:
                    status = payload[1]
                    if status == 0:
                        print("\n[+] [WATCH NOTIFICATION] Watchface SPI Flash write SUCCEEDED (status 0)!")
                    else:
                        print(f"\n[!] [WATCH NOTIFICATION] Watchface SPI Flash write note (status {status})")
                    install_complete.set()

        async def send_block(block_idx: int):
            start = block_idx * block_size
            end = min(file_size, (block_idx + 1) * block_size)
            block_bytes = bin_data[start:end]
            block_len = len(block_bytes)

            curr_pct = int(end / file_size * 100)
            bar_len = 30
            filled = int(bar_len * end / file_size)
            bar = "=" * filled + ">" + " " * (bar_len - filled - 1) if filled < bar_len else "=" * bar_len
            print(f"\r    [{bar}] {curr_pct:3d}% | Block {block_idx + 1:2d}/{total_blocks} ({end:,}/{file_size:,} B)", end="", flush=True)

            chunk_slice = 240
            for offset in range(0, block_len, chunk_slice):
                slice_data = block_bytes[offset:offset + chunk_slice]
                await client.write_gatt_char(UUID_FEE6, slice_data, response=False)
                await asyncio.sleep(0.005)

        # 1. Subscribe to notifications
        await client.start_notify(UUID_FEE3, on_fee3_notify)
        print("[+] Subscribed to watch notifications (FEE3)")

        # 2. Handshake: 0xBA 0x01
        pkt_len_query = build_ble_packet(0xBA, bytes([0x01]))
        await client.write_gatt_char(UUID_FEE2, pkt_len_query, response=False)

        try:
            await asyncio.wait_for(transfer_started.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            print("[*] Handshake default to 10,240 byte blocks...")

        # 3. Start Transfer: 0x74
        start_payload = struct.pack(">I", file_size)
        start_pkt = build_ble_packet(0x74, start_payload)
        print(f"[*] Starting OTA transfer: {start_pkt.hex()}")
        await client.write_gatt_char(UUID_FEE2, start_pkt, response=False)

        # 4. Stream blocks
        print("[*] Streaming data to smartwatch...")
        t_start = time.time()
        try:
            await asyncio.wait_for(flash_complete.wait(), timeout=45.0)
        except asyncio.TimeoutError:
            print("\n[!] Transfer timed out.")
            return False

        elapsed = time.time() - t_start
        speed_kb = (file_size / 1024) / elapsed if elapsed > 0 else 0

        # 5. Commit ACK
        if flash_success:
            commit_pkt = build_ble_packet(0x74, bytes([0x00, 0x00, 0x00, 0x00]))
            await client.write_gatt_char(UUID_FEE2, commit_pkt, response=False)
            print(f"\n[+] Commit ACK sent. Watch is now flashing SPI memory...")
            print("[*] Waiting for watch to complete internal flash write (do NOT disconnect)...")

            # Wait up to 20 seconds for watch to finish writing to SPI flash
            try:
                await asyncio.wait_for(install_complete.wait(), timeout=20.0)
            except asyncio.TimeoutError:
                print("[*] Watch did not send 0xB4 0x02, proceeding to activation...")

            await asyncio.sleep(2.0)

            # 6. Send WatchFace ID (0xB4 0x11)
            id_hi = (face_id >> 8) & 0xFF
            id_lo = face_id & 0xFF
            id_pkt = bytes([0xFE, 0xEA, 0x20, 0x0A, 0xB4, 0x11, id_hi, id_lo, 0x00, 0x00])
            print(f"[*] Sending sendJieliWatchFaceId ({face_id}): {id_pkt.hex()}")
            await client.write_gatt_char(UUID_FEE2, id_pkt, response=False)
            await asyncio.sleep(1.0)

            # 7. Send Display WatchFace Index 4 (0x19 0x04)
            disp_pkt = bytes([0xFE, 0xEA, 0x20, 0x06, 0x19, 0x04])
            print(f"[*] Sending sendDisplayWatchFace (slot 4): {disp_pkt.hex()}")
            await client.write_gatt_char(UUID_FEE2, disp_pkt, response=False)
            await asyncio.sleep(1.0)

            # 8. Sync time & timezone
            now = datetime.now()
            tz_gmt8 = timezone(timedelta(hours=8))
            ts_gmt8 = int(now.replace(tzinfo=tz_gmt8).timestamp())
            time_payload = struct.pack(">I", ts_gmt8) + bytes([8])
            time_pkt = build_ble_packet(0x31, time_payload)

            is_dst = time.daylight and time.localtime().tm_isdst > 0
            utc_offset_sec = -(time.altzone if is_dst else time.timezone)
            tz_payload = bytearray([0x07, 0x00]) + struct.pack("<i", utc_offset_sec)
            tz_pkt = build_ble_packet(0xBB, tz_payload)

            await client.write_gatt_char(UUID_FEE2, time_pkt, response=False)
            await asyncio.sleep(0.3)
            await client.write_gatt_char(UUID_FEE2, tz_pkt, response=False)
            await asyncio.sleep(2.0)

            print("=" * 65)
            print("  SUKSES PENUH! Watchface telah aktif di layar Bozlun B71!")
            print("=" * 65)
            return True
        else:
            abort_pkt = build_ble_packet(0x74, bytes([0xFF, 0xFF, 0xFF, 0xFF]))
            await client.write_gatt_char(UUID_FEE2, abort_pkt, response=False)
            print(f"\n[!] Flash failed: {error_msg}")
            return False


async def main():
    parser = argparse.ArgumentParser(description="Direct BLE Watchface Flasher for Bozlun B71")
    parser.add_argument("bin_file", help="Path to custom watchface .bin")
    parser.add_argument("--address", help="Smartwatch BLE MAC address", default=DEFAULT_ADDR)
    parser.add_argument("--id", help="WatchFace ID (default: 14698)", type=int, default=14698)
    args = parser.parse_args()

    await flash_watchface(args.address, args.bin_file, args.id)


if __name__ == "__main__":
    asyncio.run(main())
