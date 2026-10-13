# Hosting gratis dan nama Kliprava

Diperiksa pada **13 Oktober 2026**. Backend ini membutuhkan Python/FastAPI,
FFmpeg, yt-dlp, dan Chromium untuk sebagian fallback. Menyimpan frontend saja
di hosting statis tidak menjalankan backend tersebut.

## Pilihan di luar Railway

| Penyedia | Paket gratis dan batas penting | Kecocokan untuk proyek ini |
| --- | --- | --- |
| **Oracle Cloud Always Free** | Ampere A1: total 2 OCPU dan RAM 12 GB, setara kuota 1.500 OCPU-jam dan 9.000 GB-jam/bulan. Kapasitas region dapat habis; instance menganggur dapat direklamasi. | Pilihan kapasitas terbaik dari tiga opsi ini untuk FFmpeg, tetapi perlu mengelola VM, Docker, HTTPS, dan pembaruan sendiri. |
| **Render Free** | 512 MB RAM, 0,1 CPU, 750 jam/workspace/bulan. Tidur setelah 15 menit sepi; bangun kembali sekitar satu menit. Trafik keluar dan proses build punya kuota; trafik keluar yang dianggap terlalu tinggi dapat menyebabkan suspensi. | Paling mudah untuk percobaan ringan melalui Docker. Tidak cocok untuk unduhan ramai atau konversi panjang. |
| **Koyeb Free Instance** | Satu instance 512 MB RAM, 0,1 vCPU, disk 2 GB. Tidur setelah satu jam; region Frankfurt atau Washington. | Cocok untuk eksperimen ringan. Pendaftaran memerlukan kartu; FAQ menyebut pilihan awal Pro berbayar, sehingga jangan menganggap seluruh proses pendaftaran gratis. |

Sumber resmi: [Oracle Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm),
[Oracle FAQ untuk verifikasi kartu](https://www.oracle.com/cloud/free/faq/),
[Render Free](https://render.com/docs/free),
[spesifikasi paket Render](https://render.com/docs/blueprint-spec),
[Koyeb Instances](https://www.koyeb.com/docs/reference/instances),
dan [Koyeb Pricing FAQ](https://www.koyeb.com/docs/faqs/pricing).

Rekomendasi kapasitas di atas merupakan penilaian berdasarkan kebutuhan aplikasi,
bukan hasil uji beban di penyedia tersebut. Oracle memerlukan verifikasi kartu
saat pendaftaran standar. Gunakan sumber daya bertanda Always Free dan periksa
kuota akun; kredit trial bukan jaminan biaya nol setelah trial habis.

Hugging Face tidak dipilih sebagai backend gratis baru: dokumentasi saat ini
mensyaratkan paket berbayar untuk membuat Docker/Gradio Spaces, meskipun CPU Basic
tidak dikenai tarif per jam. [Sumber](https://huggingface.co/docs/hub/en/spaces-overview).

## Render: konfigurasi sudah disiapkan

1. Masuk ke [Render Dashboard](https://dashboard.render.com), lalu **New → Blueprint**.
2. Hubungkan repository `davsite/sosmedify`, pilih branch `main` dan file `render.yaml`.
3. Periksa bahwa layanan `kliprava-api` memakai paket **Free**. Tidak ada database,
   disk berbayar, atau worker yang dibuat oleh konfigurasi ini.
4. Jalankan deployment. Dockerfile memasang FFmpeg, Node.js, dan Chromium.
5. Buka URL layanan yang diberikan dashboard, ditambah `/api/health`.
   Respons harus HTTP 200 dengan `status: HEALTHY` dan `ffmpeg_available: true`.
   Redis `UNAVAILABLE` dan antrean `queue_available: false` wajar pada setup ini:
   frontend memakai `/api/process`, yang tidak memerlukan Redis/S3.
6. Di pengaturan frontend Vercel, isi **VITE_API_URL** dengan URL HTTPS layanan
   tersebut, tanpa `/api` di belakangnya, lalu deploy ulang frontend.
7. Uji tautan video pendek milik sendiri: preview, unduh MP4 dengan suara,
   potong durasi, serta ekspor MP3. Matikan layanan Railway setelah hasilnya benar.

Untuk setup manual gunakan **New → Web Service → Docker**, build context root
repository, Dockerfile `./Dockerfile`, health check `/api/health`, dan plan Free.
Samakan environment variables dengan `render.yaml`.

Batas video pada konfigurasi Render adalah **480p** untuk mengurangi beban.
Ini tidak membatasi ukuran sumber, durasi, atau jumlah permintaan bersamaan;
RAM tetap dapat habis. Chromium dan FFmpeg berjalan dalam jatah memori yang sama.
Lakukan satu konversi pendek dahulu. Migrasi server juga tidak menjamin platform
sosial media menerima IP server baru atau berhenti meminta login.

## Oracle: pilihan untuk kapasitas lebih besar

Buat VM Ubuntu berlabel Always Free dalam home region, dengan alokasi total
Ampere A1 maksimal 2 OCPU/12 GB sesuai kuota akun. Pasang Docker, ambil repository,
dan bangun image dari Dockerfile root. Jalankan port 8080 di belakang reverse
proxy HTTPS, lalu verifikasi `/api/health` dan konfigurasi `VITE_API_URL` seperti
langkah Render. Image perlu dibangun untuk arsitektur ARM VM tersebut.

VM, domain HTTPS, dan akun hosting belum dibuat oleh perubahan repository ini.
Tidak ada endpoint pengganti yang diasumsikan sudah aktif.

## Nama aplikasi

Nama baru: **Kliprava**, dibaca *klip-ra-va*. Pencarian web untuk nama persis
`"Kliprava"` dan pencarian tanpa tanda kutip pada tanggal di atas tidak menemukan
hasil terkait. Ini adalah pemeriksaan awal, bukan bukti bahwa seluruh domain,
akun sosial, atau merek dengan nama tersebut tersedia. Belum ada domain yang
didaftarkan atau dipesan.

Branding UI, metadata halaman, manifest, nama berkas unduhan, identitas API,
dan label sumber Android memakai nama baru. Alamat Vercel yang sudah tercantum
di proyek dan repository GitHub tetap digunakan sampai domain baru benar-benar
terpasang. Setelah domain baru aktif, perbarui canonical/Open Graph/JSON-LD di
`frontend/index.html`, `frontend/public/robots.txt`, `frontend/public/sitemap.xml`,
`android-app/app/src/main/res/values/strings.xml`, dan tautan README.

ID paket Android dan jembatan JavaScript `SosmedifyApp` dipertahankan untuk
kompatibilitas. Workflow GitHub membangun ulang antarmuka Android dari frontend
terbaru; APK baru hanya tersedia setelah workflow berhasil.
