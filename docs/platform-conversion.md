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

Setelah memeriksa halaman berbagi, backend membuka halaman desktop Douyin dengan
Chromium dalam sesi sementara yang baru. Backend membaca respons detail video
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
