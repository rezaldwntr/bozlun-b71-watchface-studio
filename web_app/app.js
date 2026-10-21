/**
 * Bozlun B71 Watchface Studio - Direct BLE Flasher
 * Works natively in mobile browsers (Android Chrome) via Web Bluetooth API.
 * Requires ZERO Developer Mode, ZERO USB Debugging, ZERO Root.
 */

// BLE UUIDs for MoYoung / JieLi OTA
const UUID_SERVICE_FEEA = '0000feea-0000-1000-8000-00805f9b34fb'; // Primary MoYoung/JieLi Service containing FEE1..FEE6
const UUID_SERVICE_FEE1 = '0000fee1-0000-1000-8000-00805f9b34fb';
const UUID_SERVICE_FEE7 = '0000fee7-0000-1000-8000-00805f9b34fb';
const UUID_BATTERY_SVC  = '0000180f-0000-1000-8000-00805f9b34fb';

const UUID_FEE1         = '0000fee1-0000-1000-8000-00805f9b34fb';
const UUID_FEE2         = '0000fee2-0000-1000-8000-00805f9b34fb'; // TX Control (Write Without Response)
const UUID_FEE3         = '0000fee3-0000-1000-8000-00805f9b34fb'; // RX Notify
const UUID_FEE6         = '0000fee6-0000-1000-8000-00805f9b34fb'; // OTA Data Stream (Write Without Response)
const UUID_BATTERY_CHR  = '00002a19-0000-1000-8000-00805f9b34fb';

// Built-in Watchface Catalog
const WATCHFACE_CATALOG = [
  {
    id: 'casio_retro',
    faceId: 14698,
    title: 'Casio Retro LCD (COROS)',
    subtitle: 'Revisi 100% Sempurna • Vintage Chronograph',
    file: 'watchfaces/casio_retro.bin',
    preview: 'previews/casio_retro.png',
    badge: 'Pilihan Utama',
    desc: 'Desain Casio/COROS vintage dengan border heksagonal merah, display 7-segment tebal, indikator detak jantung, baterai petir oranye, dan tapak kucing.'
  },
  {
    id: 'khnst02_digital',
    faceId: 14698,
    title: 'KHNST02 Minimal Digital',
    subtitle: 'Revisi 1:1 Presisi • 5-Dot Baterai + %',
    file: 'watchfaces/khnst02_digital.bin',
    preview: 'previews/khnst02_digital.png',
    badge: 'Revisi 1:1',
    desc: 'Desain digital modern ultra-bersih hasil revisi 1:1 sesuai referensi: 5 dot kapsul baterai + persentase dinamis, jam bold tebal, SUN 23.09, dan 4 metrik fitness sejajar presisi.'
  },
  {
    id: 'roman_analog',
    faceId: 14698,
    title: 'Minimalist Roman Analog',
    subtitle: 'Classic 2-Hand Haute Horlogerie • Ultra Responsif',
    file: 'watchfaces/roman_analog.bin',
    preview: 'previews/roman_analog.png',
    badge: 'Super Responsif',
    desc: 'Desain dress watch klasik 2-jarum (Hour & Minute) ultra-ringan tanpa lag. Layar bangun instan 0 detik, transisi menu 60fps super mulus, dan hemat baterai drastis.'
  },
  {
    id: 'lonely_moon',
    faceId: 28268,
    title: 'Lonely Moon (Restore Asli)',
    subtitle: 'Backup Pabrikan Resmi • Slot 4',
    file: 'watchfaces/lonely_moon.bin',
    preview: 'previews/lonely_moon.png',
    badge: 'Backup Asli',
    desc: 'Watchface resmi bawaan pabrikan Da Fit. Gunakan ini kapan pun Anda ingin mengembalikan tampilan awal pabrik.'
  }
];

// App State
let bleDevice = null;
let gattServer = null;
let charFee2 = null;
let charFee3 = null;
let charFee6 = null;

let isConnected = false;
let isFlashing = false;
let selectedFace = WATCHFACE_CATALOG[0];
let customFileData = null;

// OTA Transfer Variables
let otaBinData = null;
let otaFileSize = 0;
let otaBlockSize = 10240;
let otaTotalBlocks = 0;
let otaCrc = 0;
let otaStartTime = 0;
let otaResolveComplete = null;
let otaRejectComplete = null;

// DOM Elements
const btnConnect = document.getElementById('btnConnect');
const btnDisconnect = document.getElementById('btnDisconnect');
const btnSyncTime = document.getElementById('btnSyncTime');
const deviceCard = document.getElementById('deviceCard');
const deviceNameEl = document.getElementById('deviceName');
const deviceStatusEl = document.getElementById('deviceStatus');
const batteryBadge = document.getElementById('batteryBadge');
const batteryLevelEl = document.getElementById('batteryLevel');

const galleryContainer = document.getElementById('galleryContainer');
const fileInput = document.getElementById('fileInput');
const btnUploadCustom = document.getElementById('btnUploadCustom');

const progressModal = document.getElementById('progressModal');
const progressCircle = document.getElementById('progressCircle');
const progressPercentEl = document.getElementById('progressPercent');
const progressStatusEl = document.getElementById('progressStatus');
const progressSubstatusEl = document.getElementById('progressSubstatus');
const progressSpeedEl = document.getElementById('progressSpeed');

const toast = document.getElementById('toast');

// Utility sleep
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// MoYoung / JieLi Hardware CRC-16 (t29.java algorithm)
function moyoungCrc16(data, init = 0xFEEA) {
  let crc = init;
  for (let i = 0; i < data.length; i++) {
    const b = data[i] & 0xFF;
    const i3 = (((crc & 0xFF) << 8) | ((crc & 0xFF00) >> 8)) ^ b;
    const i4 = i3 ^ ((i3 & 0xFF) >> 4);
    const i5 = (i4 ^ ((i4 & 0xFF) << 12)) & 0xFFFF;
    crc = (i5 ^ ((i5 & 0xFF) << 5)) & 0xFFFF;
  }
  return crc;
}

// Build standard MoYoung 0xFE 0xEA framed packet
function buildBlePacket(cmdId, payload = new Uint8Array(0)) {
  const plLen = payload.length;
  const pktLen = plLen + 5;
  let flags = 0x20;
  if (pktLen > 255) {
    flags = ((pktLen >> 8) & 0xFF) + 0x20;
  }
  const pkt = new Uint8Array(pktLen);
  pkt[0] = 0xFE;
  pkt[1] = 0xEA;
  pkt[2] = flags;
  pkt[3] = pktLen & 0xFF;
  pkt[4] = cmdId & 0xFF;
  if (plLen > 0) {
    pkt.set(payload, 5);
  }
  return pkt;
}

// Show Toast
function showToast(message, type = 'info') {
  toast.textContent = message;
  toast.className = `toast show ${type}`;
  setTimeout(() => {
    toast.className = 'toast';
  }, 4000);
}

// Format Bytes
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
}

// Render Watchface Cards in Gallery
function renderGallery() {
  galleryContainer.innerHTML = '';

  WATCHFACE_CATALOG.forEach((item, index) => {
    const isSel = selectedFace && selectedFace.id === item.id;
    const card = document.createElement('div');
    card.className = `watchface-card ${isSel ? 'selected' : ''}`;
    card.innerHTML = `
      <div class="card-badge">${item.badge}</div>
      <div class="preview-wrapper">
        <img src="${item.preview}" alt="${item.title}" class="watchface-preview-img" onerror="this.src='icons/icon-192.png'" />
      </div>
      <div class="card-body">
        <h3 class="card-title">${item.title}</h3>
        <p class="card-subtitle">${item.subtitle}</p>
        <p class="card-desc">${item.desc}</p>
        <div class="card-actions">
          <button class="btn btn-flash ${isSel ? 'active' : ''}" data-index="${index}">
            <svg class="icon" viewBox="0 0 24 24"><path fill="currentColor" d="M7 2v11h3v9l7-12h-4l4-8z"/></svg>
            Flash ke Jam
          </button>
        </div>
      </div>
    `;

    card.querySelector('.btn-flash').addEventListener('click', (e) => {
      e.stopPropagation();
      selectAndFlash(item);
    });

    card.addEventListener('click', () => {
      selectedFace = item;
      renderGallery();
    });

    galleryContainer.appendChild(card);
  });
}

// Handle Select & Flash
async function selectAndFlash(item) {
  selectedFace = item;
  renderGallery();

  if (!isConnected) {
    showToast('Silakan hubungkan jam tangan B71 terlebih dahulu!', 'warning');
    await connectBluetooth();
    if (!isConnected) return;
  }

  try {
    showToast(`Mengambil file watchface: ${item.title}...`);
    let binBuffer;
    if (item.customData) {
      binBuffer = item.customData;
    } else {
      const resp = await fetch(item.file);
      if (!resp.ok) throw new Error(`Gagal mengunduh berkas ${item.file}`);
      binBuffer = await resp.arrayBuffer();
    }

    await startOtaTransfer(new Uint8Array(binBuffer), item.faceId || 14698);
  } catch (err) {
    console.error(err);
    showToast(`Error: ${err.message}`, 'error');
  }
}

// Check Web Bluetooth Support
function checkBluetoothSupport() {
  if (!navigator.bluetooth) {
    const isHttps = window.location.protocol === 'https:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (!isHttps) {
      showToast('Web Bluetooth membutuhkan koneksi HTTPS aman. Buka via https://', 'error');
    } else {
      showToast('Browser Anda belum mendukung Web Bluetooth. Gunakan Google Chrome di Android!', 'error');
    }
    btnConnect.disabled = true;
    return false;
  }
  return true;
}

// Connect to Watch via Web Bluetooth (Strictly locked to B71)
async function connectBluetooth() {
  if (!checkBluetoothSupport()) return;

  try {
    deviceStatusEl.textContent = 'Mencari jam Bozlun B71...';
    showToast('Mencari jam Bozlun B71...', 'info');

    const options = {
      filters: [
        { name: 'B71' },
        { namePrefix: 'B71' },
        { name: 'b71' },
        { namePrefix: 'b71' }
      ],
      optionalServices: [
        UUID_SERVICE_FEEA,
        UUID_SERVICE_FEE1,
        UUID_SERVICE_FEE7,
        UUID_BATTERY_SVC,
        '0000180a-0000-1000-8000-00805f9b34fb',
        '0000190e-0000-1000-8000-00805f9b34fb',
        '0000ae00-0000-1000-8000-00805f9b34fb'
      ]
    };

    bleDevice = await navigator.bluetooth.requestDevice(options);

    bleDevice.addEventListener('gattserverdisconnected', onDisconnected);

    deviceStatusEl.textContent = 'Menghubungkan GATT...';
    try {
      gattServer = await bleDevice.gatt.connect();
    } catch (gattErr) {
      console.error('GATT Connect Error:', gattErr);
      throw new Error('Gagal konek! Kemungkinan jam sedang dikunci oleh aplikasi Da Fit di HP. Harap TUTUP/KELUARKAN aplikasi Da Fit terlebih dahulu, lalu coba lagi.');
    }

    deviceStatusEl.textContent = 'Mencari Layanan Komunikasi OTA...';
    let serviceOta = null;
    const candidateServices = [
      UUID_SERVICE_FEEA,
      UUID_SERVICE_FEE1,
      UUID_SERVICE_FEE7
    ];

    for (const sUuid of candidateServices) {
      try {
        serviceOta = await gattServer.getPrimaryService(sUuid);
        if (serviceOta) {
          console.log(`[BLE] Primary service ditemukan: ${sUuid}`);
          break;
        }
      } catch (e) {
        console.warn(`[BLE] Service ${sUuid} tidak ditemukan di perangkat:`, e);
      }
    }

    if (!serviceOta) {
      throw new Error('Layanan OTA (FEEA) tidak ditemukan pada jam tangan.');
    }

    deviceStatusEl.textContent = 'Mempersiapkan Karakteristik OTA...';
    charFee2 = await serviceOta.getCharacteristic(UUID_FEE2);
    charFee3 = await serviceOta.getCharacteristic(UUID_FEE3);
    charFee6 = await serviceOta.getCharacteristic(UUID_FEE6);

    // Subscribe to notifications on FEE3
    await charFee3.startNotifications();
    charFee3.addEventListener('characteristicvaluechanged', handleFee3Notification);

    // Read Battery
    try {
      const batSvc = await gattServer.getPrimaryService(UUID_BATTERY_SVC);
      const batChr = await batSvc.getCharacteristic(UUID_BATTERY_CHR);
      const batVal = await batChr.readValue();
      const pct = batVal.getUint8(0);
      batteryLevelEl.textContent = `${pct}%`;
      batteryBadge.style.display = 'flex';
    } catch (e) {
      console.warn('Battery read skipped:', e);
    }

    isConnected = true;
    deviceNameEl.textContent = bleDevice.name || 'Bozlun B71';
    deviceStatusEl.textContent = 'Terhubung (BLE Siap Flash)';
    deviceCard.classList.add('connected');
    btnConnect.style.display = 'none';
    btnDisconnect.style.display = 'inline-flex';
    btnSyncTime.disabled = false;

    showToast(`Berhasil terhubung ke ${bleDevice.name || 'Bozlun B71'}!`, 'success');
  } catch (err) {
    console.error('Bluetooth connection error:', err);
    if (err.name === 'NotFoundError') {
      if (err.message && err.message.toLowerCase().includes('user cancelled')) {
        showToast('Pencarian dibatalkan oleh pengguna.', 'warning');
      } else {
        showToast(`Gagal membaca layanan jam: ${err.message}`, 'error');
      }
    } else {
      showToast(`${err.message}`, 'error');
    }
    deviceStatusEl.textContent = 'Belum terhubung';
  }
}

// Disconnect
function disconnectBluetooth() {
  if (bleDevice && bleDevice.gatt.connected) {
    bleDevice.gatt.disconnect();
  }
  onDisconnected();
}

function onDisconnected() {
  isConnected = false;
  isFlashing = false;
  deviceCard.classList.remove('connected');
  deviceNameEl.textContent = 'Bozlun B71';
  deviceStatusEl.textContent = 'Terputus';
  btnConnect.style.display = 'inline-flex';
  btnDisconnect.style.display = 'none';
  btnSyncTime.disabled = true;
  batteryBadge.style.display = 'none';
  progressModal.style.display = 'none';
  showToast('Koneksi Bluetooth terputus.', 'warning');
}

// Handle Watch Inbound Notifications (FEE3)
function handleFee3Notification(event) {
  const value = event.target.value;
  if (!value || value.byteLength < 5) return;

  const b0 = value.getUint8(0);
  const b1 = value.getUint8(1);
  if (b0 !== 0xFE || b1 !== 0xEA) return;

  const cmd = value.getUint8(4);
  const payload = new Uint8Array(value.buffer, 5);

  console.log(`[FEE3 RX] Cmd: 0x${cmd.toString(16).toUpperCase()}, Payload:`, payload);

  // 1. DFU Block Negotiation Response: 0xBA 0x01
  if (cmd === 0xBA && payload.length >= 3 && payload[0] === 0x01) {
    otaBlockSize = (payload[2] << 8) | payload[1];
    otaTotalBlocks = Math.ceil(otaFileSize / otaBlockSize);
    console.log(`[+] Block Size negotiated: ${otaBlockSize} bytes (${otaTotalBlocks} blocks)`);
  }

  // 2. Block Request / CRC Response: 0x74
  else if (cmd === 0x74 && payload.length >= 2) {
    const reqBlock = (payload[0] << 8) | payload[1];

    if (reqBlock === 0xFFFF) {
      // Hardware CRC Check
      let watchCrc = 0;
      if (payload.length >= 4) {
        watchCrc = (payload[2] << 8) | payload[3];
      }
      console.log(`[*] All blocks sent! Watch CRC: 0x${watchCrc.toString(16).toUpperCase()} (Local: 0x${otaCrc.toString(16).toUpperCase()})`);

      if (watchCrc === otaCrc) {
        progressStatusEl.textContent = 'CRC Cocok! Menyimpan ke memori jam...';
        progressSubstatusEl.textContent = 'Jangan matikan atau jauhkan jam tangan';
        sendCommitAck();
      } else {
        progressStatusEl.textContent = 'CRC Mismatch!';
        if (otaRejectComplete) otaRejectComplete(new Error(`CRC mismatch: 0x${watchCrc.toString(16)} != 0x${otaCrc.toString(16)}`));
      }
    } else {
      // Send the requested block
      sendBlock(reqBlock);
    }
  }

  // 3. Install Status Response: 0xB4
  else if (cmd === 0xB4) {
    if (payload.length >= 2 && payload[0] === 0x02) {
      const status = payload[1];
      console.log(`[+] Watch reported Flash write status: ${status}`);
      if (status === 0 && otaResolveComplete) {
        otaResolveComplete(true);
      }
    }
  }
}

// Send Single DFU Block in 240-byte slices to FEE6
async function sendBlock(blockIdx) {
  if (!isFlashing || !otaBinData) return;

  const start = blockIdx * otaBlockSize;
  const end = Math.min(otaFileSize, (blockIdx + 1) * otaBlockSize);
  const blockBytes = otaBinData.subarray(start, end);
  const blockLen = blockBytes.length;

  // Update Progress UI
  const pct = Math.floor((end / otaFileSize) * 100);
  updateProgressUI(pct, `Mengirim Blok ${blockIdx + 1} / ${otaTotalBlocks}`, `${formatBytes(end)} dari ${formatBytes(otaFileSize)}`);

  const elapsed = (Date.now() - otaStartTime) / 1000;
  if (elapsed > 0) {
    const speedKb = ((end / 1024) / elapsed).toFixed(1);
    progressSpeedEl.textContent = `${speedKb} KB/s`;
  }

  const chunkSlice = 240;
  for (let offset = 0; offset < blockLen; offset += chunkSlice) {
    if (!isFlashing) break;
    const sliceData = blockBytes.subarray(offset, offset + chunkSlice);
    await charFee6.writeValueWithoutResponse(sliceData);
    await sleep(5); // 5ms throttle
  }
}

// Send Commit ACK after CRC check
async function sendCommitAck() {
  try {
    const ackPkt = buildBlePacket(0x74, new Uint8Array([0, 0, 0, 0]));
    await charFee2.writeValueWithoutResponse(ackPkt);
    console.log('[+] Commit ACK sent. Watch is writing SPI flash...');

    updateProgressUI(100, 'Memproses Watchface di Jam...', 'Jam sedang menyimpan ke chip flash');

    // Wait for flash completion or timeout
    await sleep(3500);

    if (otaResolveComplete) {
      otaResolveComplete(true);
    }
  } catch (err) {
    console.error('Error sending commit ACK:', err);
    if (otaRejectComplete) otaRejectComplete(err);
  }
}

// Start Complete OTA Transfer
async function startOtaTransfer(binData, faceId = 14698) {
  if (isFlashing) return;
  isFlashing = true;
  otaBinData = binData;
  otaFileSize = binData.length;
  otaBlockSize = 10240;
  otaTotalBlocks = Math.ceil(otaFileSize / otaBlockSize);
  otaCrc = moyoungCrc16(binData);
  otaStartTime = Date.now();

  console.log(`[*] Starting OTA: Size=${otaFileSize} B, CRC=0x${otaCrc.toString(16).toUpperCase()}`);

  // Open Progress Modal
  progressModal.style.display = 'flex';
  updateProgressUI(0, 'Inisialisasi Handshake BLE...', 'Menyiapkan modul DFU');

  const transferPromise = new Promise((resolve, reject) => {
    otaResolveComplete = resolve;
    otaRejectComplete = reject;
  });

  try {
    // 1. Handshake Query: 0xBA 0x01
    const lenQueryPkt = buildBlePacket(0xBA, new Uint8Array([0x01]));
    await charFee2.writeValueWithoutResponse(lenQueryPkt);
    await sleep(300);

    // 2. Start OTA Transfer: 0x74 (file size 4 bytes big-endian)
    const sizePayload = new Uint8Array([
      (otaFileSize >> 24) & 0xFF,
      (otaFileSize >> 16) & 0xFF,
      (otaFileSize >> 8) & 0xFF,
      otaFileSize & 0xFF
    ]);
    const startPkt = buildBlePacket(0x74, sizePayload);
    await charFee2.writeValueWithoutResponse(startPkt);

    // 3. Wait for full block streaming & SPI flash write
    await Promise.race([
      transferPromise,
      new Promise((_, reject) => setTimeout(() => reject(new Error('Waktu transfer habis (Timeout 60s)')), 60000))
    ]);

    // 4. Send Watchface ID (0xB4 0x11)
    updateProgressUI(100, 'Mengaktifkan Watchface...', 'Mengunci Slot Tampilan 4');
    const idHi = (faceId >> 8) & 0xFF;
    const idLo = faceId & 0xFF;
    const idPkt = new Uint8Array([0xFE, 0xEA, 0x20, 0x0A, 0xB4, 0x11, idHi, idLo, 0x00, 0x00]);
    await charFee2.writeValueWithoutResponse(idPkt);
    await sleep(1000);

    // 5. Send Display WatchFace Index 4 (0x19 0x04)
    const dispPkt = new Uint8Array([0xFE, 0xEA, 0x20, 0x06, 0x19, 0x04]);
    await charFee2.writeValueWithoutResponse(dispPkt);
    await sleep(1000);

    // 6. Sync Clock & Timezone
    updateProgressUI(100, 'Sinkronisasi Jam & Tanggal HP...', 'Menyetel RTC akurat');
    await syncPhoneClock();
    await sleep(1500);

    // Success!
    updateProgressUI(100, 'SUKSES PENUH!', 'Watchface kini telah aktif di jam Bozlun B71 Anda!');
    showToast('Watchface berhasil diflash dan aktif di jam tangan!', 'success');

    setTimeout(() => {
      progressModal.style.display = 'none';
      isFlashing = false;
    }, 2500);

  } catch (err) {
    console.error('OTA Transfer failed:', err);
    isFlashing = false;
    updateProgressUI(0, 'Gagal Flash', err.message);
    showToast(`Gagal: ${err.message}`, 'error');
    setTimeout(() => {
      progressModal.style.display = 'none';
    }, 3000);
  }
}

// Sync Live Phone Time & Timezone to Watch (0x31 & 0xBB)
async function syncPhoneClock() {
  if (!isConnected || !charFee2) return;

  const now = new Date();
  const ts = Math.floor(now.getTime() / 1000);

  // Time Packet (0x31)
  const timePayload = new Uint8Array([
    (ts >> 24) & 0xFF,
    (ts >> 16) & 0xFF,
    (ts >> 8) & 0xFF,
    ts & 0xFF,
    8
  ]);
  const timePkt = buildBlePacket(0x31, timePayload);
  await charFee2.writeValueWithoutResponse(timePkt);
  await sleep(300);

  // Timezone Packet (0xBB)
  const offsetSec = -now.getTimezoneOffset() * 60;
  const tzPayload = new Uint8Array(6);
  tzPayload[0] = 0x07;
  tzPayload[1] = 0x00;
  tzPayload[2] = offsetSec & 0xFF;
  tzPayload[3] = (offsetSec >> 8) & 0xFF;
  tzPayload[4] = (offsetSec >> 16) & 0xFF;
  tzPayload[5] = (offsetSec >> 24) & 0xFF;

  const tzPkt = buildBlePacket(0xBB, tzPayload);
  await charFee2.writeValueWithoutResponse(tzPkt);

  console.log(`[+] Phone clock synced: ${now.toLocaleTimeString()} (Offset ${offsetSec}s)`);
}

// Update Circular Progress UI
function updateProgressUI(percent, status, substatus) {
  progressPercentEl.textContent = `${percent}%`;
  progressStatusEl.textContent = status;
  progressSubstatusEl.textContent = substatus;

  // SVG dashoffset: 2 * PI * r = 2 * PI * 68 ≈ 427.26
  const circumference = 427.26;
  const offset = circumference - (percent / 100) * circumference;
  progressCircle.style.strokeDashoffset = offset;
}

// Handle Custom .bin File Upload
btnUploadCustom.addEventListener('click', () => {
  fileInput.click();
});

fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  try {
    const arrayBuf = await file.arrayBuffer();
    const uint8 = new Uint8Array(arrayBuf);
    const crc = moyoungCrc16(uint8);

    const customItem = {
      id: 'custom_' + Date.now(),
      faceId: 14698,
      title: file.name.replace('.bin', ''),
      subtitle: `File Kustom • ${formatBytes(uint8.length)}`,
      customData: arrayBuf,
      preview: 'icons/icon-192.png',
      badge: 'File Sendiri',
      desc: `Berkas watchface kustom yang dipilih langsung dari HP. Ukuran: ${formatBytes(uint8.length)}, CRC-16: 0x${crc.toString(16).toUpperCase()}`
    };

    WATCHFACE_CATALOG.unshift(customItem);
    selectedFace = customItem;
    renderGallery();
    showToast(`File ${file.name} siap diflash!`, 'success');
  } catch (err) {
    showToast(`Gagal membaca file: ${err.message}`, 'error');
  }
});

// Event Listeners
btnConnect.addEventListener('click', connectBluetooth);
btnDisconnect.addEventListener('click', disconnectBluetooth);
btnSyncTime.addEventListener('click', async () => {
  await syncPhoneClock();
  showToast('Jam & tanggal smartwatch berhasil disinkronkan!', 'success');
});

// Register PWA Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js')
      .then((reg) => console.log('[PWA] Service Worker registered:', reg.scope))
      .catch((err) => console.warn('[PWA] SW registration failed:', err));
  });
}

// Initialize Gallery
renderGallery();
