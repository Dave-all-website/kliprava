<div align="center">

  # ⚡ Kliprava
  ### Unduh, potong, dan simpan video dalam satu tempat.
  
  <p align="center">
    <b>Enterprise-grade social media extraction engine, frame-accurate FFmpeg trimmer, and dual-client ecosystem (Vite React 19 + Standalone Android APK).</b>
  </p>

  <p align="center">
    <a href="https://omniklip.vercel.app" target="_blank">
      <img src="https://img.shields.io/badge/🌐_Live_Demo-omniklip.vercel.app-000000?style=for-the-badge&logo=vercel&logoColor=white" alt="Live Demo" />
    </a>
    <a href="https://github.com/davsite/sosmedify/releases/latest">
      <img src="https://img.shields.io/badge/📱_Download_APK-v1.0.0-06B6D4?style=for-the-badge&logo=android&logoColor=white" alt="Download APK" />
    </a>
    <a href="https://github.com/davsite/sosmedify/actions">
      <img src="https://img.shields.io/badge/⚡_CI%2FCD-Automated_Build-10B981?style=for-the-badge&logo=githubactions&logoColor=white" alt="CI/CD Status" />
    </a>
    <a href="#-lisensi--kontribusi">
      <img src="https://img.shields.io/badge/📄_License-MIT-8B5CF6?style=for-the-badge" alt="License MIT" />
    </a>
  </p>

  <!-- Tech Stack Shields -->
  <p align="center">
    <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/Python-3.12%20%7C%203.14-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/React-19.2-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React 19" />
    <img src="https://img.shields.io/badge/Vite-6.4-646CFF?style=flat-square&logo=vite&logoColor=white" alt="Vite" />
    <img src="https://img.shields.io/badge/TailwindCSS-3.4-38B2AC?style=flat-square&logo=tailwindcss&logoColor=white" alt="Tailwind CSS" />
    <img src="https://img.shields.io/badge/FFmpeg-7.x%20Proxy-007808?style=flat-square&logo=ffmpeg&logoColor=white" alt="FFmpeg" />
    <img src="https://img.shields.io/badge/yt--dlp-Active%20Engine-FF0000?style=flat-square&logo=youtube&logoColor=white" alt="yt-dlp" />
    <img src="https://img.shields.io/badge/Docker-Multi--stage-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker" />
    <img src="https://img.shields.io/badge/Render-Free_Hobby_Config-0B0D0E?style=flat-square&logo=render&logoColor=white" alt="Konfigurasi Render Free tersedia" />
  </p>

  <!-- Quick Nav -->
  <p align="center">
    <a href="#-keunggulan-arsitektur">Keunggulan</a> •
    <a href="#-sistem-arsitektur">Arsitektur</a> •
    <a href="#-matriks-dukungan-7-platform">Platform Matrix</a> •
    <a href="#-rest-api-reference">REST API</a> •
    <a href="#-aplikasi-android-apk">Android APK</a> •
    <a href="#-panduan-deployment-production">Deployment</a> •
    <a href="#-panduan-lokal-development">Local Dev</a>
  </p>

  <hr style="border: 0; height: 1px; background: linear-gradient(to right, transparent, #F43F5E, #8B5CF6, #06B6D4, transparent); margin: 28px 0;" />

</div>

---

## 🌟 Keunggulan Arsitektur • Key Capabilities

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>🚀 Zero-Watermark Extraction</h3>
      <p>Mengambil berkas video mentah beresolusi penuh tanpa watermark dari <b>TikTok</b> dan <b>Douyin</b> menggunakan jalur API Aweme RPC & TikWM Gateway berkecepatan tinggi.</p>
    </td>
    <td width="50%" valign="top">
      <h3>🛡️ Cloud Datacenter Anti-Bot Bypass</h3>
      <p>Menerapkan strategi fallback klien multi-tier <code>android_vr</code> & <code>ios</code> pada <b>YouTube</b> untuk menembus proteksi <i>"Sign in to confirm you're not a bot"</i> di server cloud Railway/Docker.</p>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>⏱️ Frame-Accurate Precision Trimming</h3>
      <p>Pemotong klip instan dengan akurasi milidetik berbasis <b>FFmpeg 7.x stream proxy</b>. Proses pemotongan rata-rata selesai dalam waktu <code>< 1.2 detik</code> tanpa membebani memori server.</p>
    </td>
    <td width="50%" valign="top">
      <h3>⚡ RedNote Direct CDN Ingestion (0.3s)</h3>
      <p>Mengekstrak video dari <b>Xiaohongshu (RedNote)</b> secara langsung melalui parser SSR Desktop State & token CDN <code>sns-video</code> tanpa perlu menjalankan browser headless yang lambat.</p>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>🎵 Lossless Audio & Format Selector</h3>
      <p>Konversi langsung ke format <b>MP4 Video</b> (hingga 1080p Full HD) atau ekstraksi <b>MP3 Audio 320kbps High-Bitrate</b> dengan penyesuaian sampling rate otomatis.</p>
    </td>
    <td width="50%" valign="top">
      <h3>📱 Dual Client Ecosystem</h3>
      <p>Tersedia dalam dua antarmuka terpadu: <b>Web Application</b> modern berbasis React 19 + Vite 6 dan <b>Aplikasi Android Standalone</b> dengan aset tertanam lokal <i>(0s initial load)</i>.</p>
    </td>
  </tr>
</table>

---

## 🏗️ Sistem Arsitektur • System Architecture

Kliprava menggunakan pola arsitektur *decoupled microservice* yang mengisolasi antarmuka klien, gateway streaming berkinerja tinggi, dan orkestrasi pemrosesan FFmpeg:

```mermaid
flowchart TD
    subgraph Clients["🌐 CLIENT PRESENTATION LAYER"]
        WEB["💻 Web SPA (React 19 + Vite 6 + Tailwind CSS)"]
        APK["📱 Android Client (Standalone Embedded WebView + Native DownloadManager)"]
    end

    subgraph Gateway["⚡ REVERSE PROXY & FASTAPI GATEWAY (Railway)"]
        ROUTER{"API Gateway Router"}
        INFO["/api/info<br/>Canonical URL Extractor"]
        STREAM["/api/stream<br/>HTTP 206 Partial Chunk Proxy"]
        PROCESS["/api/process<br/>FFmpeg Frame-Accurate Engine"]
        HEALTH["/api/health<br/>Liveness & Readiness Probe"]
    end

    subgraph Engines["🧩 MULTI-TIER SCRAPER & EXTRACTOR MATRIX"]
        YOUTUBE["YouTube Engine<br/>• Primary: android_vr Client<br/>• Fallback: tv / ios Clients<br/>• Optional: Session Cookie"]
        TIKTOK["TikTok & Douyin<br/>• TikWM Gateway<br/>• Canonical Aweme RPC<br/>• No-Watermark CDN Resolver"]
        REDNOTE["RedNote / Xiaohongshu<br/>• Desktop SSR State Parser<br/>• Direct sns-video CDN Tokenizer"]
        META["Instagram & Facebook<br/>• Graph API Scraper<br/>• Public Reel Stream Extractor"]
        TWITTER["X / Twitter<br/>• Video Bearer Stream Decoupler"]
    end

    subgraph Storage["💾 EPHEMERAL STORAGE & BUFFER"]
        TEMP["/app/temp_media<br/>• Ephemeral Local Buffer<br/>• Auto-purged via Starlette BackgroundTask"]
        S3["Cloudflare R2 / AWS S3<br/>(Optional Persistent Storage)"]
    end

    WEB -->|REST / JSON| ROUTER
    APK -->|REST / JSON| ROUTER
    ROUTER --> INFO
    ROUTER --> STREAM
    ROUTER --> PROCESS
    ROUTER --> HEALTH

    INFO --> Engines
    STREAM -->|Range Requests| Engines
    PROCESS -->|Direct Pipe| TEMP
    TEMP -.-> S3
```

---

## ⛩️ Matriks Dukungan 7 Platform • Platform Matrix

| Platform | Pola URL (Regex Support) | Engine Ekstraksi | Mekanisme Bypass | Output Resolusi | Watermark | Audio Output |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **TikTok** | `tiktok.com`, `vm.tiktok.com`, `vt.tiktok.com` | TikWM Gateway + yt-dlp | Mobile UA Spoofing & Redirect Resolver | 1080p | ❌ Bersih | MP3 320k |
| **Douyin** | `douyin.com`, `v.douyin.com`, `iesdouyin.com` | TikWM Aweme RPC & Canonical Page | Mobile Session Emulation | 1080p | ❌ Bersih | MP3 320k |
| **Instagram** | `instagram.com/(reel\|p\|tv)/` | Graph Video Stream Decoupler | Multi-Cookie Session Rotator | 1080p | ❌ Bersih | MP3 320k |
| **Facebook** | `facebook.com`, `fb.watch`, `fb.com` | Direct Watch & Public Reels Parser | Desktop SSR Tokenizer | 1080p | ❌ Bersih | MP3 320k |
| **X / Twitter** | `x.com`, `twitter.com` | Video CDN Token Parser | Direct Stream Decoupler | 1080p | ❌ Bersih | MP3 320k |
| **RedNote** | `xiaohongshu.com`, `xhslink.com` | Desktop SSR & Direct CDN Extractor | 0.3s Fast Stream Tokenizer | 1080p | ❌ Bersih | MP3 320k |
| **YouTube** | `youtube.com/watch`, `youtu.be`, `shorts` | yt-dlp Innertube Engine | Anti-Bot `android_vr` Client Bypass | 4K / 1080p | ❌ Bersih | MP3 320k |

---

## 📡 REST API Reference

Semua respons API menggunakan standar JSON terstruktur dan mendukung CORS universal.

<details open>
<summary><b>1. POST /api/info — Ekstraksi Metadata & Stream URL</b></summary>
<br/>

Menganalisis link media sosial, mengurai link pendek (*shortlinks*), dan mengembalikan metadata lengkap beserta daftar resolusi video yang tersedia.

* **Endpoint**: `/api/info`
* **Method**: `POST`
* **Header**: `Content-Type: application/json`

**Request Payload:**
```json
{
  "url": "https://vt.tiktok.com/ZSjXexample/"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "title": "Kliprava Video Showcase",
    "duration": 48.5,
    "thumbnail": "https://p16-sign.tiktokcdn.com/...jpg",
    "direct_url": "https://v16-webapp-prime.tiktokcdn.com/...mp4",
    "qualities": [
      { "label": "1080p Full HD", "height": 1080 },
      { "label": "720p HD", "height": 720 },
      { "label": "480p SD", "height": 480 },
      { "label": "360p SD", "height": 360 }
    ],
    "platform": "tiktok"
  }
}
```
</details>

<details>
<summary><b>2. GET /api/stream — Universal Streaming Video Proxy (HTTP 206)</b></summary>
<br/>

Menyediakan tunneling CORS dan mendukung *HTTP 206 Partial Content* dengan range requests. Fitur ini memungkinkan pengguna melihat preview video secara instan di filmstrip sebelum memotong video tanpa harus menunggu seluruh video terunduh.

* **Endpoint**: `/api/stream`
* **Method**: `GET`
* **Query Params**: `url=<encoded_direct_url>`
* **Header**: `Range: bytes=0-1048576`

**Contoh cURL:**
```bash
curl -I -X GET "https://convertallsosmed-production.up.railway.app/api/stream?url=https%3A%2F%2Fcdn.example.com%2Fvideo.mp4" \
  -H "Range: bytes=0-1048576"
```
</details>

<details>
<summary><b>3. POST /api/process — Pemotongan Klip & Konversi Format</b></summary>
<br/>

Menjalankan subproses pemotongan presisi (*frame-accurate trim*) dan konversi format ke MP4 Video atau MP3 Audio (320kbps) dengan encoding hardware/fast-preset.

* **Endpoint**: `/api/process`
* **Method**: `POST`
* **Header**: `Content-Type: application/json`

**Request Payload:**
```json
{
  "url": "https://www.instagram.com/reel/CxExample/",
  "start_time": 5.0,
  "end_time": 18.5,
  "format": "mp4",
  "resolution": "1080"
}
```

**Response**: Berkas biner media langsung terunduh via streaming attachment dengan nama berkas `Kliprava_00-05_00-18.mp4`.
</details>

<details>
<summary><b>4. GET /api/health — Liveness & Readiness Probe</b></summary>
<br/>

Digunakan oleh monitor infrastruktur (Railway, Docker health check, atau Uptime monitoring).

```json
{
  "status": "HEALTHY",
  "app_name": "Kliprava Converter Service",
  "redis_broker": "CONNECTED",
  "s3_storage_configured": false
}
```
</details>

---

## 📱 Aplikasi Android (APK) • Mobile Client

Kliprava dilengkapi aplikasi native Android dalam folder [`android-app/`](android-app/) dengan arsitektur **Standalone Embedded Client**:

```
📱 Perangkat Android Pengguna
   │
   ▼
[ Android Standalone Native App (MainActivity.java) ]
   ├── ⚡ Embedded Local Assets (WebViewAssetLoader)
   │     └── assets/web/index.html (React 19 + Vite JS + CSS) — Pemuatan instan 0 detik
   ├── 🔄 SwipeRefreshLayout (Pull-to-Refresh & Re-render)
   ├── 🛡️ Back Button Navigation Handler (Double-press exit protection)
   ├── 📥 Native DownloadListener ──► Android DownloadManager
   │                                  └── Simpan langsung ke /sdcard/Download
   └── ☁️ Background Cloud Media Engine ──► Railway FastAPI
                                              └── yt-dlp & FFmpeg 7.x
```

### 📥 Unduh Berkas APK Siap Pakai

| Berkas | Versi | Ukuran | Status | Unduhan |
| :--- | :---: | :---: | :---: | :---: |
| **`kliprava-v1.0.0.apk`** | `v1.0.0` | Sesuai hasil build | Dibuat oleh GitHub Actions | [**Lihat rilis terbaru**](https://github.com/davsite/sosmedify/releases/latest) |
| **GitHub Releases** | `Semua` | - | ![GitHub](https://img.shields.io/badge/Official-Release-06B6D4?style=flat-square) | [**🌐 Kunjungi Releases**](https://github.com/davsite/sosmedify/releases) |

> [!TIP]
> APK bernama Kliprava tersedia setelah workflow **Build Kliprava APK** berhasil.
>
> **Keunggulan Aset Tertanam (*Offline-Ready UI*)**:
> Seluruh antarmuka React 19 tersimpan langsung di dalam berkas APK. Saat dibuka, aplikasi langsung muncul tanpa menunggu koneksi internet memuat aset web. Komunikasi scraping dan konversi media tetap berjalan cepat melalui backend cloud Railway.

---

## 🏮 Panduan Deployment Production

### 1. Pilih Backend Gratis di Luar Railway

Lihat [perbandingan hosting dan panduan pemasangan](docs/hosting-gratis.md).
Oracle Cloud Always Free menyediakan kapasitas yang lebih cocok untuk konversi
video; Render Free lebih mudah dipasang untuk percobaan dengan beban ringan.

Untuk Render, buka **New → Blueprint**, pilih repository ini, lalu gunakan
[`render.yaml`](render.yaml). Konfigurasi memilih paket **Free**, Docker,
health check `/api/health`, dan batas keluaran video 480p untuk mengurangi beban.
Konversi panjang dan penggunaan bersamaan tetap bisa melampaui kapasitas gratis.

Setelah layanan sehat, salin URL HTTPS dari dashboard untuk konfigurasi frontend.
File konfigurasi ini belum berarti backend baru sudah terpasang. Endpoint lama
tetap menjadi fallback sampai `VITE_API_URL` diisi dengan URL baru.

### 2. Deploy Frontend ke Vercel (Edge Network)
1. Buka [Vercel](https://vercel.com) dan impor repository Anda.
2. Konfigurasi build project:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Masukkan **Environment Variable**:
   ```env
   VITE_API_URL=https://ALAMAT-BACKEND-DARI-DASHBOARD
   ```
4. Klik **Deploy**. Webapp Anda langsung aktif secara global di Vercel Edge CDN!

---

## ⚙️ Konfigurasi Environment Variables

| Variabel | Kategori | Wajib | Nilai Default | Deskripsi |
| :--- | :---: | :---: | :---: | :--- |
| `PORT` | Backend | Tidak | `8080` | Port listen server FastAPI container. |
| `DEBUG` | Backend | Tidak | `false` | Mode debug & verbose logging. |
| `VITE_API_URL` | Frontend | **Ya untuk migrasi** | Lokal: `http://localhost:8000`; produksi: endpoint Railway lama | URL HTTPS backend baru; isi saat build lalu deploy ulang frontend. |
| `MAX_VIDEO_HEIGHT` | Backend | Tidak | `1080`; Render Free: `480` | Batas tinggi video keluaran untuk mengurangi beban konversi. |
| `YOUTUBE_COOKIES` | Backend | Tidak | `None` | Konten cookies Netscape untuk rotasi sesi YouTube jika dibutuhkan. |
| `PROXIES` | Backend | Tidak | `[]` | JSON array proxy HTTP/SOCKS5 untuk rotasi alamat IP scraper. |
| `S3_ENDPOINT_URL` | Storage | Tidak | `None` | Endpoint URL Cloudflare R2 / AWS S3 (opsional). |
| `S3_ACCESS_KEY` | Storage | Tidak | `None` | Access Key ID kredensial S3. |
| `S3_SECRET_KEY` | Storage | Tidak | `None` | Secret Key kredensial S3. |
| `S3_BUCKET_NAME` | Storage | Tidak | `None` | Nama bucket S3/R2 tujuan upload permanen. |

---

## 💻 Panduan Lokal Development

### Prasyarat
* **Python**: 3.11 atau lebih baru
* **Node.js**: 18.x atau lebih baru (disarankan Node 20 LTS)
* **FFmpeg**: 6.0+ terpasang di PATH sistem

### 1. Menjalankan Backend
```bash
# Pindah ke direktori backend
cd backend

# Buat & aktifkan virtual environment
python -m venv venv
source venv/bin/activate   # Linux/Mac
# .\venv\Scripts\activate  # Windows

# Instal pustaka dependensi
pip install -r requirements.txt

# Jalankan server FastAPI dengan auto-reload
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Akses Swagger UI dokumentasi API di: `http://localhost:8000/docs`.

### 2. Menjalankan Frontend
```bash
# Buka terminal baru dan masuk ke frontend
cd frontend

# Instal paket dependensi
npm install

# Jalankan server Vite development
npm run dev
```
Buka browser di: `http://localhost:5173`.

---

## 🔒 Keamanan & Manajemen Sumber Daya

- **Pembersihan Berkas Otomatis**: Berkas sementara di `/app/temp_media` diproses menggunakan Starlette `BackgroundTask` dan langsung dihapus setelah pengiriman selesai ke pengguna (*zero disk leak*).
- **Sanitasi Parameter Input**: Parameter waktu pemotongan dan resolusi divalidasi ketat menggunakan Pydantic v2 untuk mencegah *command injection* pada subproses FFmpeg.
- **Wadah Iklan Terisolasi**: Banner monetisasi Adsterra dimuat dalam sandbox `iframe srcDoc` terisolasi sehingga tidak dapat memblokir interaksi UI atau mengakses token pengguna.

---

## 📄 Lisensi & Hak Cipta

Proyek ini dirilis di bawah lisensi terbuka [MIT License](LICENSE).  
Bebas digunakan, dikembangkan, dan dimodifikasi untuk kebutuhan personal maupun komersial.

<div align="center">

  <br/>
  <p>🍃 <i>Dibuat dengan presisi tinggi, dedikasi penuh, dan arsitektur yang tangguh.</i> 🌸</p>
  <p><strong>Kliprava by Dav'site</strong> • © 2026</p>

  <img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/grass.png" width="100%" alt="Footer accent line" />

</div>
