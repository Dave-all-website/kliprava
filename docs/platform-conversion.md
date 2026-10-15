# Konversi YouTube, TikTok, dan RedNote

Backend menerima tautan TikTok `tt.site`, `vm.tiktok.com`, dan `vt.tiktok.com`.
Untuk RedNote, gunakan tautan hasil Salin Tautan dari aplikasi dan pertahankan
parameter `xsec_token`; parameter tersebut diperlukan oleh beberapa postingan.

Docker menyertakan Node 24 dan `yt-dlp[default]`, termasuk versi EJS yang cocok
dengan yt-dlp. Kebutuhan runtime dijelaskan di
[dokumentasi resmi EJS](https://github.com/yt-dlp/yt-dlp/wiki/EJS).
Pada instalasi lokal, instal requirements terbaru dan pastikan Node 22+ ada di PATH.

Jika Railway menerima pesan YouTube meminta verifikasi, administrator dapat
mengatur `YOUTUBE_COOKIES` melalui Variables Railway. Nilainya berupa isi file
cookie Netscape atau Base64 dari file tersebut. `YOUTUBE_PROXY` opsional untuk
koneksi keluar yang diizinkan. Cookie tidak menjamin IP server diterima YouTube;
cookie yang kedaluwarsa atau pembatasan akun/wilayah tetap bisa menyebabkan gagal.
Jangan commit cookie atau kredensial proxy ke Git.

Ekstraksi metadata dan pengunduhan menggunakan pengaturan yang sama. Cookie
YouTube tidak otomatis dipakai untuk TikTok atau RedNote. Jika diperlukan,
tersedia variabel `TIKTOK_COOKIES`, `TIKTOK_PROXY`, `REDNOTE_COOKIES`, dan
`REDNOTE_PROXY` untuk jalur yt-dlp masing-masing platform. Jalur TikWM dan
ekstraksi HTML RedNote tidak memakai variabel tersebut.

Uji regresi:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests -q
node --test frontend\src\mediaClient.test.js
```

Tes mencakup tautan pendek, URL CDN dari respons TikTok, identitas dan durasi
RedNote, CDN cadangan, isolasi cookie, serta konversi video berdimensi ganjil.
Tes jaringan langsung tetap diperlukan karena akses platform dapat berubah.

## Douyin tanpa impor cookie login

Setelah memeriksa halaman berbagi, backend membuka beranda Douyin dengan Chromium
dalam sesi sementara yang baru dan memberi waktu untuk inisialisasi tamu sebelum
membuka video. Browser memakai identitas versi dan sistem operasinya sendiri,
bukan User-Agent Windows versi lama di Linux. Jika halaman video tidak memberikan
data, backend mencoba rute `user/self?modal_id=...` dalam sesi yang sama.
Backend membaca respons detail video
hanya jika ID-nya cocok dengan tautan yang diminta, lalu mengunduh URL MP4 yang
memuat video dan audio. Format DASH terpisah tidak dipakai sebagai MP4 gabungan.

Jalur Douyin tidak membaca `DOUYIN_COOKIES`, file cookie, atau profil browser
pribadi. Tidak perlu menambahkan cookie login di Railway. Situs dapat membuat
cookie sesi anonim selama halaman dibuka; sesi tersebut dibuang saat browser
ditutup dan tidak diekspor ke pengguna. Tidak ada login otomatis atau penyelesaian
CAPTCHA. Jika Douyin tidak menyediakan video untuk browser anonim, backend
melaporkan kegagalan tersebut tanpa menyarankan unggah cookie.

Docker sudah memasang Chromium. Untuk lokal, jalankan
`python -m playwright install chromium` dari lingkungan backend. Pada Windows,
Microsoft Edge digunakan sebagai cadangan jika Chromium tidak tersedia.
Satu proses browser diizinkan sekaligus untuk membatasi pemakaian memori server.
Akses tetap bergantung pada ketersediaan video dan respons Douyin terhadap
koneksi server; berhasil di lokal belum membuktikan berhasil di Railway.

### Verifikasi Railway, 15 Oktober 2026

Deployment `23f69a46-3ac2-492c-a063-07c4e858e0ef`, kode `9ea9fb8`, berhasil diuji
melalui API publik Railway tanpa mengimpor cookie Douyin:

- Tautan `https://v.douyin.com/Q4d8B5M0l2I/` menghasilkan metadata video
  `7675505205047348543`, durasi 1501,823 detik (HTTP 200).
- Permintaan potongan 0–3 detik menghasilkan MP4 640x360 dengan video H.264
  dan audio AAC, durasi keluaran 3,017 detik, 319.434 byte (HTTP 200).
- Permintaan potongan yang sama menghasilkan MP3 116.186 byte (HTTP 200).
  Pengunduhan sumber video panjang membuat pengujian MP3 memerlukan 116 detik.
- Video kedua `7694279177201415418` juga menghasilkan metadata,
  durasi 12,7 detik (HTTP 200).
- Uji regresi backend: 52 lulus. Hasil ini memverifikasi dua tautan tersebut;
  ketersediaan video lain tetap ditentukan oleh respons Douyin.
