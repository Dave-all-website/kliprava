# Konversi YouTube, TikTok, dan RedNote

Backend menerima tautan TikTok `tt.site`, `vm.tiktok.com`, dan `vt.tiktok.com`.
Untuk RedNote, gunakan tautan hasil Salin Tautan dari aplikasi dan pertahankan
parameter `xsec_token`; parameter tersebut diperlukan oleh beberapa postingan.

Docker menyertakan Node 24 dan `yt-dlp[default]`, termasuk versi EJS yang cocok
dengan yt-dlp. Kebutuhan runtime dijelaskan di
[dokumentasi resmi EJS](https://github.com/yt-dlp/yt-dlp/wiki/EJS).
Pada instalasi lokal, instal requirements terbaru dan pastikan Node 22+ ada di PATH.

## YouTube tanpa cookie login

Docker menyertakan BgUtils PO Token Provider 2.0.2 (image dikunci dengan digest),
beserta plugin Python dengan versi yang sama. `YOUTUBE_POT_SERVER_HOME` menunjuk
ke `/opt/youtube-pot`. Mode ini memakai client `mweb` dan meminta PO Token untuk
permintaan player maupun streaming. Token dibuat oleh proses Node lokal tanpa
layanan publik tambahan dan tanpa mengimpor `YOUTUBE_COOKIES` atau file cookie.
Ekstraksi metadata dan fallback unduhan yt-dlp memakai konfigurasi yang sama.
Satu ekstraksi diizinkan sekaligus agar proses Node dan cache provider tidak
bertumpuk. Platform lain tetap memakai konfigurasi masing-masing.

Untuk uji lokal, ikuti instalasi **Generation Script** dari
[BgUtils provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider),
lalu arahkan `YOUTUBE_POT_SERVER_HOME` ke direktori `server` yang sudah dibangun.
Tanpa variabel tersebut, yt-dlp tetap menggunakan client bawaannya.

PO Token bukan jaminan akses: YouTube masih dapat menolak IP datacenter, dan
video khusus member tetap membutuhkan akses membership. Verifikasi metadata,
preview, dan hasil konversi langsung dari Railway diperlukan sebelum menyatakan
jalur ini berhasil di production. Rujukan:
[panduan PO Token yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide).

### Konfigurasi sesi opsional untuk instalasi lain

Jika Railway menerima pesan YouTube meminta verifikasi, administrator dapat
mengatur `YOUTUBE_COOKIES` jika mode PO Token anonim tidak aktif. Nilainya berupa isi file
cookie Netscape atau Base64 dari file tersebut. `YOUTUBE_PROXY` opsional untuk
koneksi keluar yang diizinkan. Cookie tidak menjamin IP server diterima YouTube;
cookie yang kedaluwarsa atau pembatasan akun/wilayah tetap bisa menyebabkan gagal.
Jangan commit cookie atau kredensial proxy ke Git.

Bedakan dua jenis penolakan YouTube:

- `members-only` / `Join this channel`: video memerlukan membership channel.
  Sesi anonim tidak memiliki akses; cookie akun tanpa membership juga tidak cukup.
  Gunakan video publik atau sesi akun yang memang memiliki akses.
- `Sign in to confirm you're not a bot`: YouTube menolak sesi/koneksi server.
  Uji dari Railway setelah konfigurasi sesi atau koneksi keluar; keberhasilan
  pemutaran di browser pribadi tidak membuktikan server mendapat akses.

Panduan sesi tersedia di
[dokumentasi resmi yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies).
Masukkan rahasia hanya ke Variables Railway, bukan chat atau repository.
Redeploy kode tanpa mengubah kondisi akses tersebut belum tentu mengatasi penolakan.
Peringatan kredensial S3 yang tidak terisi bukan penyebab kedua error ekstraksi ini.

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
