# ⌚ Bozlun B71 Watchface Studio & Web Bluetooth Flasher

A modern, standalone Web Bluetooth Progressive Web App (PWA) and flashing toolkit for the **Bozlun B71** smartwatch (JieLi JLI MCU, MoYoung / Da Fit protocol, 466x466 AMOLED).

---

## 🚀 Fitur Utama

- **Web Bluetooth PWA Flasher**: Mem-flash watchface langsung dari smartphone Android (Chrome) tanpa perlu PC.
- **Aman untuk Aplikasi Absensi Kantor**: 100% **Bebas Mode Pengembang (Developer Options: OFF)**, bebas USB debugging, dan bebas root.
- **Auto-Sync Waktu & Tanggal**: Sinkronisasi jam dan zona waktu HP ke jam tangan otomatis setelah flash.
- **Katalog Watchface Siap Pakai**:
  1. **Casio Retro LCD (COROS)**: Vintage chronograph LCD dengan border heksagonal merah, font 7-segment tebal, heart rate, steps, dan level baterai.
  2. **KHNST02 Minimal Digital**: Desain digital modern ultra-bersih dan tipis.
  3. **Minimalist Roman Analog**: Jam jarum analog klasik elegan dengan angka Romawi.
  4. **Lonely Moon (Official Restore)**: Backup resmi pabrikan untuk mengembalikan tampilan pabrik kapan saja.
  5. **Custom .bin Uploader**: Pilih berkas `.bin` apa saja langsung dari memori HP.

---

## 🌐 Deploy ke Vercel (1-Klik)

1. **Push repositori ini ke GitHub** akun Anda.
2. Buka [vercel.com/new](https://vercel.com/new).
3. Pilih repositori GitHub Anda dan klik **Deploy**.
4. Dalam hitungan detik, aplikasi web Anda aktif di domain `https://<nama-proyek>.vercel.app`.
5. Buka tautan tersebut di Google Chrome HP Anda, ketuk **"Hubungkan"**, dan pilih watchface favorit Anda!

---

## 💻 Penggunaan Langsung via PC (Opsional)

Jika ingin mem-flash langsung dari PC menggunakan Python:

```bash
# Flash Casio Retro LCD
python tools/flash_ble.py custom_watchfaces/03_casio_retro_lcd/03_casio_retro_lcd_safe.bin

# Sinkronisasi Waktu Jam Tangan
python tools/sync_time_ble.py
```

---

## 📜 Lisensi
MIT License.
