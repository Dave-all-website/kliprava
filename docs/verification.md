# Verifikasi perbaikan web app

## Frontend

```powershell
cd frontend
npm ci
npm test
npm run build
```

`npm test` menguji konfigurasi URL backend, status koneksi, dan payload ekspor
yang menggunakan URL dari metadata preview. `npm run build` memeriksa build React/Vite.

`VITE_API_URL` menerima alamat lokal maupun produksi. Tanpa konfigurasi, mode
development memakai `http://localhost:8000`; build produksi memakai endpoint
Railway yang sudah digunakan proyek. Dev server frontend memakai port **3000**.

Konfigurasi Render Free tersedia di `render.yaml`. Setelah backend baru aktif,
isi `VITE_API_URL` dan build ulang frontend; lihat [panduan hosting](hosting-gratis.md).
Nama tampilan aplikasi sekarang **Kliprava**. Alamat layanan tidak berubah hanya
karena branding diganti.

## Backend

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements-dev.txt
backend/.venv/Scripts/python -m pytest backend/tests -q --basetemp=temp_media/pytest-regression
```

Jalankan dari direktori root proyek. Pada Linux/macOS gunakan
`backend/.venv/bin/python`. Pengujian memakai request tiruan sehingga tidak
membutuhkan Redis, S3, cookie, atau akun sosial media. Dua pengujian menjalankan
FFmpeg dari paket `imageio-ffmpeg`, membuat video/suara sintetis, dan memeriksa
audio serta durasi hasil MP4/MP3. Backend produksi tetap memerlukan `ffmpeg`
dan `ffprobe` di PATH seperti konfigurasi Docker yang ada.

Perilaku yang diuji mencakup pemilihan video HD beserta audio terpisah, batas
resolusi, validasi waktu/format, pembersihan berkas, HTTP Range, dan penolakan
alamat privat serta redirect ke jaringan internal. Transport streaming mengikat
koneksi ke IP publik yang telah diperiksa, sambil mempertahankan hostname untuk
validasi sertifikat HTTPS.

`/api/health` mengembalikan 503 jika FFmpeg tidak ditemukan. Redis dan S3/R2
digunakan hanya untuk antrean; `/api/process` tetap menyediakan unduhan langsung.
`/api/convert` menolak permintaan dengan 503 jika storage belum dikonfigurasi,
sehingga tidak lagi memberikan tautan lokal yang tidak tersedia.

Pengujian ini tidak menjamin akses langsung ke semua platform: pembatasan akun,
wilayah, dan CDN perlu diuji dengan tautan publik yang tersedia saat deployment.
