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

## Douyin

Backend mempertahankan parameter tautan berbagi dan mencari video dengan ID yang
sesuai di `loaderData.videoInfoRes.item_list` maupun struktur bersarang lainnya.
URL media yang diberikan Douyin dipakai apa adanya, termasuk URL cadangannya.

Jika halaman berbagi tidak memuat video dan API melaporkan `Fresh cookies` atau
HTTP 403, link telah dikenali tetapi sesi/koneksi server belum diterima Douyin.
Ini tidak cukup untuk menyimpulkan pembatasan wilayah atau postingan telah dihapus.
Backend tidak lagi mengulangi panggilan API yang sama lewat dua bentuk URL.

Administrator dapat menambahkan `DOUYIN_COOKIES` berformat Netscape atau Base64
di Variables layanan Railway, kemudian melakukan redeploy. Cookie hanya perlu
dipasang melalui pengaturan rahasia layanan, bukan dikirim di chat atau Git.
Variabel tersebut dipakai oleh jalur yt-dlp, termasuk fallback unduhan.
`DOUYIN_PROXY` tersedia jika diperlukan untuk koneksi keluar yang diizinkan.
Cookie/proxy tidak menjamin semua postingan dapat diakses; uji kembali link yang
sama setelah konfigurasi. Halaman yang hanya dapat ditonton lewat aplikasi
Douyin mungkin tetap tidak menyediakan video untuk backend web.
