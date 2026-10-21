#!/usr/bin/env python3
"""
Local HTTPS & PWA Web Server for Bozlun B71 Watchface Studio.
Generates an automatic local SSL certificate and terminal QR code
so users can instantly connect and flash watchfaces from their mobile browser.
"""

import os
import sys
import ssl
import socket
import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

import qrcode
import ipaddress
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

WEB_APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_app")
SSL_DIR = os.path.join(WEB_APP_DIR, "ssl")
CERT_FILE = os.path.join(SSL_DIR, "server.pem")
KEY_FILE = os.path.join(SSL_DIR, "key.pem")


def get_local_ip():
    """Detect the most likely LAN IPv4 address of this machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually connect, just probes route
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def generate_self_signed_cert(ip_addr: str):
    """Generate self-signed certificate with IP SAN for local HTTPS."""
    os.makedirs(SSL_DIR, exist_ok=True)
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        return

    print(f"[*] Generating local SSL certificate for IP {ip_addr}...")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Bozlun Studio"),
        x509.NameAttribute(NameOID.COMMON_NAME, ip_addr),
    ])

    now = datetime.datetime.now(datetime.timezone.utc)
    alt_names = [
        x509.IPAddress(ipaddress.IPv4Address(ip_addr)),
        x509.DNSName("localhost")
    ]

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .sign(key, hashes.SHA256())
    )

    with open(KEY_FILE, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    with open(CERT_FILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"[+] SSL certificate generated: {CERT_FILE}")


class CustomPWAHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_APP_DIR, **kwargs)

    def end_headers(self):
        # Enable CORS and disable aggressive caching during development
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def guess_type(self, path):
        if path.endswith(".bin"):
            return "application/octet-stream"
        if path.endswith(".json") or path.endswith(".webmanifest"):
            return "application/manifest+json"
        return super().guess_type(path)


def print_ascii_qr(url: str):
    """Print ASCII QR Code directly into terminal and save PNG."""
    qr = qrcode.QRCode(box_size=1, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    
    # Save image version
    img = qr.make_image(fill_color="black", back_color="white")
    qr_img_path = os.path.join(WEB_APP_DIR, "qr_code.png")
    img.save(qr_img_path)
    print(f"[+] QR Code image saved to: {qr_img_path}")
    print("\n" + "=" * 50)
    print("  SCAN QR CODE / BUKA TAUTAN INI DI HP:")
    print("=" * 50)
    print(f"  URL: {url}\n")
    try:
        if sys.platform == "win32":
            # Reconfigure stdout to utf-8 if possible
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")
        qr.print_ascii(invert=True)
    except Exception:
        # Fallback to simple ASCII blocks if terminal doesn't support utf-8 box characters
        matrix = qr.get_matrix()
        for row in matrix:
            line = "".join("  " if col else "██" for col in row)
            try:
                print(line)
            except Exception:
                print("".join("  " if col else "##" for col in row))


def run_server(port: int = 8443):
    local_ip = get_local_ip()
    generate_self_signed_cert(local_ip)

    https_url = f"https://{local_ip}:{port}"

    print_ascii_qr(https_url)

    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, CustomPWAHandler)

    # Wrap with SSL
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    print("\n" + "=" * 65)
    print("  BOZLUN B71 WATCHFACE STUDIO (PWA MOBILE SERVER)")
    print("=" * 65)
    print(f"[*] Status Server   : AKTIF (HTTPS / SSL)")
    print(f"[*] Buka di HP      : {https_url}")
    print(f"[*] Buka di PC      : https://localhost:{port}")
    print("=" * 65)
    print("\n[PANDUAN BUKA DI HP]:")
    print("1. Pastikan HP dan PC terhubung ke Wi-Fi yang sama.")
    print(f"2. Buka Chrome di HP dan ketik: {https_url}")
    print("3. Jika muncul peringatan keamanan (karena sertifikat lokal),")
    print("   ketuk 'Lanjutan' (Advanced) -> 'Lanjutkan ke situs (tidak aman)'.")
    print("4. Ketuk 'Hubungkan' untuk memilih jam Bozlun B71 via Bluetooth.")
    print("5. Ketuk 'Flash ke Jam' pada watchface yang Anda inginkan!")
    print("6. Tekan Ctrl+C di terminal ini jika ingin menghentikan server.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server dihentikan oleh pengguna.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8443
    run_server(port)
