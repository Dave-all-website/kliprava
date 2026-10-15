import React, { useState, useRef, useEffect, useMemo } from 'react';
import './studio.css';
import { backendUrl, checkBackend, processPayload } from './mediaClient';
import {
  Search, Download, Loader2, AlertCircle, CheckCircle,
  Tv, Camera, Music, Globe, Image as ImageIcon,
  Sun, Moon, Clock, Volume2, RefreshCw, Play, Sparkles,
  Clipboard, X, Zap, Film, ShieldCheck, ExternalLink, Activity,
  Sliders, Smartphone, Monitor, Pause, Scissors,
  ChevronDown, ChevronUp, HelpCircle, Info, FileText, Check, Shield, Layers, ArrowRight
} from 'lucide-react';

const API = backendUrl(import.meta.env.VITE_API_URL, import.meta.env.DEV);

/* ---- 7 Platform Sosial Media ---------------------------------------------- */
const PLATFORMS = [
  { key: 'youtube',   name: 'YouTube',   jpName: 'ユーチューブ', logo: '/logos/logo_youtube.png',   color: '#EF4444', glowClass: 'glow-youtube',   badgeClass: 'bg-red-500/15 text-red-500 border-red-500/30', match: (u) => /youtube\.com|youtu\.be/.test(u) },
  { key: 'tiktok',    name: 'TikTok',    jpName: 'ティックトック', logo: '/logos/logo_tiktok.png',    color: '#06B6D4', glowClass: 'glow-tiktok',    badgeClass: 'bg-cyan-500/15 text-cyan-500 border-cyan-500/30', match: (u) => /tiktok\.com|tt\.site/.test(u) },
  { key: 'douyin',    name: 'Douyin',    jpName: '抖音',         logo: '/logos/logo_douyin.png',    color: '#EC4899', glowClass: 'glow-douyin',    badgeClass: 'bg-pink-500/15 text-pink-500 border-pink-500/30', match: (u) => /douyin\.com/.test(u) },
  { key: 'instagram', name: 'Instagram', jpName: 'インスタグラム', logo: '/logos/logo_instagram.png', color: '#D946EF', glowClass: 'glow-instagram', badgeClass: 'bg-fuchsia-500/15 text-fuchsia-500 border-fuchsia-500/30', match: (u) => /instagram\.com/.test(u) },
  { key: 'facebook',  name: 'Facebook',  jpName: 'フェイスブック', logo: '/logos/logo_facebook.png',  color: '#3B82F6', glowClass: 'glow-facebook',  badgeClass: 'bg-blue-500/15 text-blue-500 border-blue-500/30', match: (u) => /facebook\.com|fb\.watch/.test(u) },
  { key: 'x',         name: 'X / Twitter',jpName: 'ツイッター',    logo: '/logos/logo_x.png',         color: '#8B5CF6', glowClass: 'glow-x',         badgeClass: 'bg-purple-500/15 text-purple-500 border-purple-500/30', match: (u) => /twitter\.com|x\.com/.test(u) },
  { key: 'rednote',   name: 'Rednote',   jpName: '小紅書',       logo: '/logos/logo_rednote.png',   color: '#F43F5E', glowClass: 'glow-rednote',   badgeClass: 'bg-rose-500/15 text-rose-500 border-rose-500/30', match: (u) => /xiaohongshu\.com|xhslink|rednote/.test(u) },
];

const platformOf = (url) => PLATFORMS.find((p) => p.match(url || '')) || null;

const fmt = (s) => {
  if (!Number.isFinite(s)) return '00:00';
  const m = Math.floor(s / 60).toString().padStart(2, '0');
  const sec = Math.floor(s % 60).toString().padStart(2, '0');
  return `${m}:${sec}`;
};

const fmtPrecise = (s) => {
  if (!Number.isFinite(s)) return '00:00.0';
  const m = Math.floor(s / 60).toString().padStart(2, '0');
  const sec = Math.floor(s % 60).toString().padStart(2, '0');
  const tenths = Math.floor((s % 1) * 10);
  return `${m}:${sec}.${tenths}`;
};

const humanBytes = (n) => {
  if (!Number.isFinite(n)) return '';
  const u = ['B', 'KB', 'MB', 'GB'];
  let v = n, i = 0;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${u[i]}`;
};

const initialTheme = () => {
  try {
    const saved = localStorage.getItem('cuplik-theme');
    if (saved === 'dark' || saved === 'light') return saved;
  } catch (_) {}
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

const fmtElapsed = (ms) => {
  if (!ms || ms <= 0) return '00:00.0s';
  const totalSec = Math.floor(ms / 1000);
  const mins = Math.floor(totalSec / 60).toString().padStart(2, '0');
  const secs = (totalSec % 60).toString().padStart(2, '0');
  const tenths = Math.floor((ms % 1000) / 100);
  return `${mins}:${secs}.${tenths}s`;
};

/* ---- SEO & Showcase Content Data ------------------------------------------ */
const PLATFORM_DETAILS = [
  {
    key: 'youtube',
    name: 'YouTube & Shorts',
    badge: 'Hingga 1080p',
    color: '#EF4444',
    badgeClass: 'bg-red-500/15 text-red-500 border-red-500/30',
    desc: 'Unduh video YouTube, Shorts, dan konversi ke trek audio MP3 kualitas tinggi.',
    features: ['YouTube Shorts & Video', 'Pilihan Resolusi HD/FullHD', 'Presisi Potong Detik'],
    example: 'https://youtube.com/watch?v=...'
  },
  {
    key: 'tiktok',
    name: 'TikTok Video',
    badge: 'No Watermark',
    color: '#06B6D4',
    badgeClass: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
    desc: 'Ekstraksi video TikTok murni tanpa watermark (tanda air) dan simpan sound MP3 asli.',
    features: ['100% Tanpa Logo Watermark', 'Download Sound Audio', 'Kualitas Jernih Source'],
    example: 'https://vt.tiktok.com/...'
  },
  {
    key: 'instagram',
    name: 'Instagram Reels',
    badge: 'Reels & Feed',
    color: '#D946EF',
    badgeClass: 'bg-fuchsia-500/15 text-fuchsia-400 border-fuchsia-500/30',
    desc: 'Simpan video Instagram Reels, feed video, dan klip kreator dengan resolusi tajam.',
    features: ['Instagram Reels & Video', 'Kecepatan Unduh Kilat', 'Format MP4 Universal'],
    example: 'https://instagram.com/reel/...'
  },
  {
    key: 'douyin',
    name: 'Douyin (抖音)',
    badge: 'Original HD',
    color: '#EC4899',
    badgeClass: 'bg-pink-500/15 text-pink-400 border-pink-500/30',
    desc: 'Unduh video Douyin Tiongkok kualitas HD tanpa watermark dengan dukungan link pendek.',
    features: ['Douyin Bebas Watermark', 'Resolusi Asli Tiongkok', 'Tautan v.douyin.com'],
    example: 'https://v.douyin.com/...'
  },
  {
    key: 'facebook',
    name: 'Facebook Watch',
    badge: 'Watch & Reels',
    color: '#3B82F6',
    badgeClass: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    desc: 'Unduh video publik Facebook, FB Watch, dan Facebook Reels langsung ke perangkat.',
    features: ['Facebook Reels & Watch', 'Video Publik Kualitas HD', 'Support Link Mobile'],
    example: 'https://fb.watch/...'
  },
  {
    key: 'x',
    name: 'X (Twitter)',
    badge: 'Video & GIF',
    color: '#8B5CF6',
    badgeClass: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    desc: 'Simpan klip video dari postingan cuitan X (Twitter) dan animasi GIF instan tanpa kendala.',
    features: ['X Tweet Post Video', 'Konversi Animasi GIF', 'Server Proxy Cepat'],
    example: 'https://x.com/user/status/...'
  },
  {
    key: 'rednote',
    name: 'Rednote (小红书)',
    badge: 'Lifestyle Video',
    color: '#F43F5E',
    badgeClass: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
    desc: 'Ekstraksi video gaya hidup, resep, dan estetika dari Xiaohongshu tanpa watermark.',
    features: ['Xiaohongshu Video', 'Kualitas Visual Tajam', 'Dukungan Tautan xhslink'],
    example: 'http://xhslink.com/...'
  }
];

const FEATURES = [
  {
    icon: Sparkles,
    title: 'Bebas Watermark Agresif',
    desc: 'Ekstraksi video murni dari TikTok dan Douyin tanpa logo tanda air mengganggu yang menutupi konten visual Anda.'
  },
  {
    icon: Scissors,
    title: 'Frame-Accurate Video Trimming',
    desc: 'Potong video langsung di server cloud FFmpeg dengan presisi milidetik. Ambil hanya momen terbaik dan hemat kuota.'
  },
  {
    icon: Zap,
    title: 'Pemrosesan Cloud Cepat & Ringan',
    desc: 'Arsitektur streaming Range HTTP 206 instan memungkinkan analisis video dan proses potong selesai dalam hitungan detik.'
  },
  {
    icon: Music,
    title: 'Ekstraksi Audio MP3 Kualitas 320kbps',
    desc: 'Konversi video menjadi file audio MP3 berkualitas studio secara langsung untuk koleksi musik, nada dering, atau podcast.'
  },
  {
    icon: ShieldCheck,
    title: 'Privasi Terjamin & Zero-Logs',
    desc: 'Kami memprioritaskan keamanan Anda. Berkas sementara segera dibersihkan otomatis dan kami tidak merekam riwayat unduhan.'
  },
  {
    icon: Globe,
    title: '100% Gratis Tanpa Perlu Login',
    desc: 'Akses tanpa biaya langganan, tanpa batasan kuota harian, dan tanpa perlu mendaftarkan akun pribadi.'
  }
];

const STEPS = [
  {
    num: '01',
    title: 'Salin Tautan Video',
    desc: 'Buka TikTok, Instagram, YouTube, atau platform sosial media favorit Anda, lalu salin URL tautan video yang ingin Anda simpan.'
  },
  {
    num: '02',
    title: 'Tempel & Ambil Media',
    desc: 'Tempel tautan di bilah input Kliprava di atas, kemudian klik tombol "Ambil Video" untuk memulai analisis instan.'
  },
  {
    num: '03',
    title: 'Pratinjau & Atur Potongan',
    desc: 'Putar video di pemutar bawaan. Tentukan detik mulai dan selesai jika ingin memotong klip, lalu tentukan format MP4 atau MP3.'
  },
  {
    num: '04',
    title: 'Unduh Langsung ke Galeri',
    desc: 'Klik tombol "Unduh". Server FFmpeg kami akan menyiapkan berkas dan menyimpannya langsung ke perangkat Anda dalam sekejap.'
  }
];

const FAQS = [
  {q: 'Perlu akun atau aplikasi?', a: 'Tidak. Kamu bisa menempel tautan dan mengunduh hasilnya langsung melalui browser tanpa membuat akun Kliprava.'},
  {q: 'Bagaimana cara memotong?', a: 'Setelah video dimuat, geser titik mulai dan selesai pada timeline atau gunakan tombol pengaturan waktu. Pilih format, lalu klik Unduh.'},
  {q: 'Bisa unduh audio saja?', a: 'Bisa. Pilih MP3 Audio pada pengaturan keluaran. Kliprava akan mengonversi suara dari bagian yang kamu pilih.'},
  {q: 'Kenapa tautan gagal?', a: 'Pastikan tautannya lengkap dan videonya publik. Video privat, pembatasan wilayah, atau verifikasi dari platform asal dapat membuat video tidak tersedia. Coba tautan lain atau ulangi beberapa saat lagi.'},
  {q: 'Hasilnya tanpa watermark?', a: 'Jika platform menyediakan sumber tanpa watermark, Kliprava akan menggunakan sumber tersebut. Watermark yang menyatu dengan gambar video tidak dihapus.'},
  {q: 'Bisa dipakai di HP?', a: 'Bisa. Gunakan browser di Android, iPhone, tablet, atau laptop. Hasil unduhan tersimpan sesuai pengaturan browser dan perangkatmu.'},
];

const LEGAL_DOCS = {
  privacy: {
    title: 'Kebijakan Privasi (Privacy Policy)',
    updated: '17 September 2026',
    sections: [
      {
        heading: '1. Komitmen Privasi Nol Log (Zero-Logs)',
        content: 'Kliprava sangat menghormati privasi Anda. Kami tidak mengumpulkan data pribadi yang dapat mengidentifikasi Anda (PII), tidak meminta registrasi akun, tidak melacak riwayat penelusuran pribadi Anda, dan tidak pernah menjual data kepada pihak ketiga.'
      },
      {
        heading: '2. Pemrosesan URL & Media Sementara',
        content: 'Tautan (URL) yang Anda masukkan semata-mata dikirimkan ke server backend kami untuk mengambil metadata publik dari penyedia platform terkait. Semua berkas media hasil pemotongan atau konversi disimpan secara sementara (ephemeral) di direktori kerja terisolasi dan dihapus secara otomatis dan berkala.'
      },
      {
        heading: '3. Cookie & Jaringan Periklanan',
        content: 'Kami menggunakan cookie browser lokal untuk menyimpan preferensi tampilan antarmuka (seperti Mode Gelap/Terang). Selain itu, mitra jaringan periklanan pihak ketiga dapat menggunakan cookie standar untuk menayangkan iklan kontekstual yang mendukung operasional server gratis ini.'
      },
      {
        heading: '4. Keamanan Infrastruktur',
        content: 'Seluruh komunikasi data antara peramban Anda dan server kami dilindungi oleh enkripsi standar industri HTTPS/TLS 1.3 untuk mencegah penyadapan data di jalur transmisi.'
      }
    ]
  },
  terms: {
    title: 'Ketentuan Layanan (Terms of Service)',
    updated: '17 September 2026',
    sections: [
      {
        heading: '1. Penerimaan Ketentuan',
        content: 'Dengan mengakses atau menggunakan situs web Kliprava, Anda menyatakan bahwa Anda telah membaca, memahami, dan menyetujui untuk terikat oleh Ketentuan Layanan ini serta mematuhi seluruh peraturan hukum yang berlaku.'
      },
      {
        heading: '2. Batasan Penggunaan Wajar (Fair Use)',
        content: 'Kliprava disediakan semata-mata untuk penggunaan pribadi yang wajar (personal fair use), tujuan edukasi, atau pencadangan arsip konten milik Anda sendiri. Pengguna dilarang memanfaatkan alat ini untuk tujuan komersial tanpa izin pemegang hak cipta yang sah.'
      },
      {
        heading: '3. Tanggung Jawab Hak Cipta',
        content: 'Pengguna bertanggung jawab penuh atas segala konten yang diunduh atau diproses melalui alat ini. Kliprava tidak bertanggung jawab atas tindakan penyalahgunaan konten oleh pengguna akhir yang melanggar hak cipta pihak ketiga.'
      },
      {
        heading: '4. Batasan Tanggung Jawab Teknis',
        content: 'Layanan Kliprava disediakan berdasarkan prinsip "sebagaimana adanya" (as is) dan "sebagaimana tersedia" (as available). Kami tidak memberikan jaminan bahwa layanan akan selalu bebas gangguan, bebas kesalahan, atau selalu kompatibel dengan perubahan API platform pihak ketiga di masa mendatang.'
      }
    ]
  },
  disclaimer: {
    title: 'Penafian Hak Cipta & DMCA (Disclaimer)',
    updated: '17 September 2026',
    sections: [
      {
        heading: '1. Penafian Afiliasi',
        content: 'Kliprava adalah proyek perangkat lunak independen dan TIDAK berafiliasi, didukung, disponsori, atau secara resmi terhubung dengan YouTube, Google LLC, TikTok, ByteDance Ltd, Meta Platforms Inc. (Instagram & Facebook), X Corp. (Twitter), maupun Xiaohongshu / Rednote.'
      },
      {
        heading: '2. Hak Merek Dagang & Konten',
        content: 'Seluruh nama produk, logo, merek dagang, dan merek terdaftar yang ditampilkan di situs ini adalah milik dari pemegang hak cipta masing-masing. Penggunaan merek dan logo di situs ini semata-mata bersifat nominatif untuk tujuan identifikasi kompatibilitas platform.'
      },
      {
        heading: '3. Prosedur Pemberitahuan DMCA',
        content: 'Jika Anda adalah pemilik hak cipta yang sah atau agen perwakilan resminya dan meyakini bahwa tautan tertentu melanggar hak cipta Anda melalui utilitas kami, silakan sampaikan pemberitahuan resmi kepada kami. Kami berkomitmen untuk menindaklanjuti permintaan yang sah secara cepat.'
      }
    ]
  }
};

export default function App() {
  const [theme, setTheme] = useState(initialTheme);
  const [url, setUrl] = useState('');
  const [state, setState] = useState('idle'); // idle | parsing | preview | processing | downloading | error
  const [error, setError] = useState('');
  const [videoError, setVideoError] = useState(false);
  const [streamAttempt, setStreamAttempt] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isVertical, setIsVertical] = useState(false);
  const [videoRatio, setVideoRatio] = useState('Otomatis');
  const [toast, setToast] = useState('');
  const [prog, setProg] = useState(null);
  const [backendPing, setBackendPing] = useState({ online: null, latency: null });
  const [openFaq, setOpenFaq] = useState(0);
  const [activeModal, setActiveModal] = useState(null);
  const [activeSection, setActiveSection] = useState('converter');

  const [video, setVideo] = useState({ title: '', thumbnail: '', streamUrl: '', audioUrl: '', duration: 0, qualities: [], canonicalUrl: '' });
  const [start, setStart] = useState(0);
  const [end, setEnd] = useState(0);
  const [now, setNow] = useState(0);
  const [format, setFormat] = useState('mp4'); // mp4 | mp3 | thumbnail
  const [resolution, setResolution] = useState('best');
  const [elapsedMs, setElapsedMs] = useState(0);

  const videoRef = useRef(null);
  const audioRef = useRef(null);
  const trackRef = useRef(null);
  const dragRef = useRef(null);
  const infoRequestRef = useRef(null);
  const downloadStartedRef = useRef(null);
  const downloadInFlightRef = useRef(false);
  const dark = theme === 'dark';

  // Cek latency backend saat awal load
  useEffect(() => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    let mounted = true;
    checkBackend(API, controller.signal).then((health) => {
      if (mounted) setBackendPing(health);
    }).finally(() => clearTimeout(timeout));
    return () => { mounted = false; clearTimeout(timeout); controller.abort(); };
  }, []);

  useEffect(() => () => infoRequestRef.current?.abort(), []);

  useEffect(() => {
    const updateSection = () => {
      const sections = ['converter', 'platforms', 'how-it-works', 'faq'];
      const current = sections.filter(id => (document.getElementById(id)?.getBoundingClientRect().top ?? Infinity) <= 160).pop();
      setActiveSection(current || 'converter');
    };
    updateSection();
    window.addEventListener('scroll', updateSection, { passive: true });
    window.addEventListener('resize', updateSection);
    return () => { window.removeEventListener('scroll', updateSection); window.removeEventListener('resize', updateSection); };
  }, []);

  // Timer live pemrosesan unduhan
  useEffect(() => {
    if (state !== 'processing' && state !== 'downloading') {
      return;
    }
    const interval = setInterval(() => {
      setElapsedMs(Date.now() - downloadStartedRef.current);
    }, 100);
    return () => clearInterval(interval);
  }, [state]);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    document.body.className = dark ? 'dark' : 'light';
    try { localStorage.setItem('cuplik-theme', theme); } catch (_) {}
  }, [dark, theme]);

  useEffect(() => {
    const html = document.documentElement;
    html.setAttribute('translate', 'no');
    html.classList.add('notranslate');
    if (!document.querySelector('meta[name="google"]')) {
      const meta = document.createElement('meta');
      meta.name = 'google';
      meta.content = 'notranslate';
      document.head.appendChild(meta);
    }
  }, []);

  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(''), 3500);
    return () => clearTimeout(id);
  }, [toast]);

  const active = platformOf((state === 'preview' || state === 'processing' || state === 'downloading') ? video.canonicalUrl : url);
  const busy = state === 'processing' || state === 'downloading';

  const resOptions = useMemo(() => {
    const opts = [{ label: 'Kualitas asli (terbaik)', value: 'best' }];
    (video.qualities || []).forEach((q) => opts.push({ label: `${q.label}`, value: String(q.height) }));
    return opts;
  }, [video.qualities]);

  const streamSrc = useMemo(() => {
    if (!video.streamUrl) return undefined;
    if (streamAttempt === 1) {
      return video.streamUrl;
    }
    const cUrl = encodeURIComponent(video.canonicalUrl || url || '');
    return `${API}/api/stream?url=${encodeURIComponent(video.streamUrl)}&vid=${cUrl}`;
  }, [video.streamUrl, video.canonicalUrl, url, streamAttempt]);

  const audioSrc = useMemo(() => {
    if (!video.audioUrl) return undefined;
    const cUrl = encodeURIComponent(video.canonicalUrl || url || '');
    return `${API}/api/stream?url=${encodeURIComponent(video.audioUrl)}&vid=${cUrl}`;
  }, [video.audioUrl, video.canonicalUrl, url]);

  const seek = (t) => {
    if (videoRef.current) videoRef.current.currentTime = t;
    if (audioRef.current) audioRef.current.currentTime = t;
  };

  const togglePlay = () => {
    const v = videoRef.current;
    const a = audioRef.current;
    if (!v) return;
    if (v.paused) {
      v.play().catch(() => {});
      if (a) a.play().catch(() => {});
    } else {
      v.pause();
      if (a) a.pause();
    }
  };

  /* ---- Timeline potong pointer (Mouse & Touch HP) ------------------------ */
  const posToTime = (clientX) => {
    const el = trackRef.current;
    if (!el || !video.duration) return 0;
    const r = el.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (clientX - r.left) / r.width));
    return ratio * video.duration;
  };

  const applyDrag = (t) => {
    if (dragRef.current === 'start') {
      const v = Math.max(0, Math.min(Number(t.toFixed(2)), end - 0.2));
      setStart(v); seek(v);
    } else if (dragRef.current === 'end') {
      const v = Math.min(video.duration, Math.max(Number(t.toFixed(2)), start + 0.2));
      setEnd(v); seek(v);
    }
  };

  const beginDrag = (e) => {
    if (busy || !video.duration) return;
    const t = posToTime(e.clientX);
    dragRef.current = Math.abs(t - start) <= Math.abs(t - end) ? 'start' : 'end';
    try { trackRef.current.setPointerCapture(e.pointerId); } catch (_) {}
    applyDrag(t);
  };

  const moveDrag = (e) => { if (dragRef.current) applyDrag(posToTime(e.clientX)); };
  const endDrag = (e) => {
    dragRef.current = null;
    try { trackRef.current.releasePointerCapture(e.pointerId); } catch (_) {}
  };

  const nudge = (which, d) => {
    if (which === 'start') {
      const v = Math.max(0, Math.min(Number((start + d).toFixed(2)), end - 0.2));
      setStart(v); seek(v);
    } else {
      const v = Math.min(video.duration, Math.max(Number((end + d).toFixed(2)), start + 0.2));
      setEnd(v); seek(v);
    }
  };

  const markStart = () => {
    const v = Math.max(0, Math.min(Number(now.toFixed(2)), end - 0.2));
    setStart(v);
  };

  const markEnd = () => {
    const v = Math.min(video.duration, Math.max(Number(now.toFixed(2)), start + 0.2));
    setEnd(v);
  };

  const setPreset = (sec) => {
    if (!video.duration) return;
    const targetEnd = Math.min(video.duration, start + sec);
    setEnd(Number(targetEnd.toFixed(2)));
  };

  const resetTrim = () => {
    setStart(0);
    setEnd(video.duration);
    seek(0);
  };

  const handlePaste = async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.readText) {
        const text = await navigator.clipboard.readText();
        if (text) {
          setUrl(text.trim());
          setToast('Tautan ditempel. Klik Ambil video untuk melanjutkan.');
        }
      }
    } catch (_) {
      setToast('Izin clipboard tidak diberikan oleh browser.');
    }
  };

  const fetchInfo = async () => {
    if (!url.trim() || downloadInFlightRef.current) return;
    infoRequestRef.current?.abort();
    const controller = new AbortController();
    infoRequestRef.current = controller;
    const requestedUrl = url.trim();
    setState('parsing'); setError(''); setVideoError(false);
    try {
      const r = await fetch(`${API}/api/info`, {
        signal: controller.signal,
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: requestedUrl }),
      });
      const rawText = await r.text();
      let j = {};
      try {
        j = JSON.parse(rawText);
      } catch (_) {
        if (!r.ok) {
          throw new Error(`Server Backend Error (${r.status}): ${rawText.slice(0, 100)}`);
        }
        throw new Error('Respon dari server tidak valid.');
      }
      if (!r.ok) throw new Error(j.detail || j.message || 'Tautan gagal dibaca oleh server.');
      const d = j.data;
      if (!d) throw new Error('Data media tidak ditemukan.');
      if (controller.signal.aborted || infoRequestRef.current !== controller) return;
      const dur = d.duration || 60;
      setVideo({
        title: d.title || 'Video Media',
        thumbnail: d.thumbnail,
        streamUrl: d.direct_url,
        audioUrl: d.audio_url || '',
        duration: dur,
        qualities: d.qualities || [],
        canonicalUrl: d.canonical_url || requestedUrl
      });
      setStart(0); setEnd(dur); setNow(0); setResolution('best'); setFormat('mp4');
      setVideoRatio('Otomatis'); setIsVertical(false);
      setVideoError(false); setStreamAttempt(0);
      setState('preview');
    } catch (e) {
      if (controller.signal.aborted || infoRequestRef.current !== controller) return;
      setError(mapNetErr(e)); setState('error');
    } finally {
      if (infoRequestRef.current === controller) infoRequestRef.current = null;
    }
  };

  const download = async () => {
    if (downloadInFlightRef.current || !video.canonicalUrl) return;
    downloadInFlightRef.current = true;
    downloadStartedRef.current = Date.now();
    setElapsedMs(0);
    setState('processing'); setError(''); setProg(null);
    try {
      const r = await fetch(`${API}/api/process`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(processPayload(video, start, end, format, resolution)),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        throw new Error(j.detail || 'Server gagal memproses klip media.');
      }

      let blob;
      if (r.body && r.body.getReader) {
        const total = Number(r.headers.get('Content-Length')) || 0;
        const reader = r.body.getReader();
        const chunks = [];
        let loaded = 0;
        setState('downloading'); setProg({ loaded: 0, total });
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          chunks.push(value); loaded += value.length;
          setProg({ loaded, total });
        }
        blob = new Blob(chunks);
      } else {
        blob = await r.blob();
      }

      const href = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = href;

      const isYouTube = /youtube\.com|youtu\.be/.test(video.canonicalUrl);
      let downloadFilename;
      if (isYouTube && video.title && video.title !== 'Video Media') {
        const safeTitle = video.title
          .replace(/[\\/:*?"<>|]/g, '')
          .replace(/[\r\n\t]+/g, ' ')
          .replace(/\s+/g, ' ')
          .trim()
          .slice(0, 150);

        const isTrimmed = start > 0.05 || (video.duration && end < video.duration - 0.5);
        if (isTrimmed) {
          downloadFilename = `${safeTitle || 'YouTube_Video'}_${fmt(start).replace(':', '-')}_${fmt(end).replace(':', '-')}.${format}`;
        } else {
          downloadFilename = `${safeTitle || 'YouTube_Video'}.${format}`;
        }
      } else {
        downloadFilename = `Kliprava_${fmt(start).replace(':', '-')}_${fmt(end).replace(':', '-')}.${format}`;
      }

      a.download = downloadFilename;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(href);
      setState('preview'); setProg(null);
      setToast('File siap. Periksa unduhan browser.');
    } catch (e) {
      setError(mapNetErr(e)); setState('error'); setProg(null);
    } finally {
      downloadInFlightRef.current = false;
    }
  };

  const clipLen = Math.max(0, Math.floor(end - start));
  const pct = (t) => (video.duration ? (t / video.duration) * 100 : 0);
  const progPct = prog && prog.total ? Math.round((prog.loaded / prog.total) * 100) : null;

  const displayPct = state === 'downloading' && progPct !== null
    ? Math.max(0, Math.min(100, progPct)) : null;

  // Estimasi ukuran file
  const estSizeMb = useMemo(() => {
    if (format === 'mp3') {
      return ((clipLen * 320) / (8 * 1024)).toFixed(1);
    }
    if (format === 'thumbnail') {
      return '0.4';
    }
    return ((clipLen * 2.4) / 8).toFixed(1);
  }, [clipLen, format]);

  return (
    <div translate="no" className="notranslate studio-app">
      <a className="skip-link" href="#converter">Langsung ke alat konversi</a>
      <aside className="studio-sidebar" aria-label="Navigasi studio">
        <a className="studio-brand" href="#" aria-label="Kliprava, beranda">
          <span className="brand-mark"><Scissors size={22} /></span>
          <span>Kliprava<span className="brand-period">.</span></span>
        </a>
        <nav className="studio-nav" aria-label="Menu utama">
          {[
            ['converter', 'Studio', Sliders], ['platforms', 'Platform', Layers],
            ['how-it-works', 'Cara pakai', Play], ['faq', 'Bantuan', HelpCircle],
          ].map(([id, label, Icon]) => <a key={id} href={`#${id}`} className={activeSection === id ? 'studio-nav-primary' : ''}
            aria-current={activeSection === id ? 'location' : undefined} onClick={() => setActiveSection(id)}><Icon size={19} /><span>{label}</span></a>)}
        </nav>
        <div className="sidebar-note"><Scissors size={26} strokeWidth={1.4} /><p>Momen bagus<br />layak disimpan.</p><span>Video & audio, versi kamu.</span></div>
        <div className="sidebar-bottom"><span className="sidebar-dot" /> Ruang kreatifmu</div>
      </aside>

      <header className="studio-header page-width">
        <div className="workspace-path"><span>Ruang kerja</span><ChevronDown size={13} /><strong>Studio kreator</strong></div>
        <a className="studio-brand mobile-brand" href="#" aria-label="Kliprava, beranda"><span className="brand-mark"><Scissors size={20} /></span><span>Kliprava.</span></a>
        <div className="header-actions">
          <button className="theme-switch" onClick={() => setTheme(dark ? 'light' : 'dark')}
            aria-label={dark ? 'Aktifkan mode terang' : 'Aktifkan mode gelap'} aria-pressed={dark}>
            {dark ? <Sun size={18} /> : <Moon size={18} />}
            <span>{dark ? 'Mode terang' : 'Mode gelap'}</span>
          </button>
        </div>
      </header>

      <main className="page-width studio-main">
        <section className="studio-intro" aria-labelledby="page-title">
          <h1 id="page-title">Momenmu. <span>Versimu.</span></h1>
          <div className="intro-note">
            <p>Potong video atau ambil audionya. Mulai dari satu tautan.</p>
          </div>
        </section>

        <div className="studio-launch">
        <section id="converter" className="converter-panel" aria-label="Alat konversi video">
          <div className="converter-toolbar">
            <span className="tool-name"><span className="tool-dot" /> Buat klip baru</span>
            <ol className="workflow-steps" aria-label="Tahapan konversi">
              <li className={state === 'idle' || state === 'parsing' || state === 'error' ? 'current' : 'complete'}><span>1</span> Tautan</li>
              <li className={state === 'preview' ? 'current' : ''}><span>2</span> Potong</li>
              <li className={busy ? 'current' : ''}><span>3</span> Unduh</li>
            </ol>
          </div>
          <div className="converter-body">
            <div className="source-form">
              <h2>Tempel. Potong. Simpan.</h2>
              <p>Videonya dari mana? Masukkan tautannya di bawah.</p>
              <label htmlFor="video-url">Tautan video</label>
              <div className={`url-field ${state === 'error' ? 'has-error' : ''}`}>
                {active ? <img src={active.logo} alt="" width="20" height="20" /> : <Globe size={20} />}
                <input id="video-url" type="text" inputMode="url" autoComplete="off" spellCheck="false"
                  value={url} disabled={busy} aria-invalid={state === 'error'} aria-describedby={state === 'error' ? 'conversion-error' : 'url-help'}
                  onChange={(e) => { infoRequestRef.current?.abort(); infoRequestRef.current = null; setUrl(e.target.value); setState('idle'); setError(''); }}
                  onKeyDown={(e) => e.key === 'Enter' && fetchInfo()} placeholder="Tempel tautan video di sini…" />
                {url && <button className="icon-button" disabled={busy} aria-label="Hapus tautan"
                  onClick={() => { infoRequestRef.current?.abort(); infoRequestRef.current = null; setUrl(''); setState('idle'); setError(''); }}><X size={17} /></button>}
              </div>
              <div className="source-actions">
                <button className="primary-button" onClick={fetchInfo} disabled={busy || state === 'parsing' || !url.trim()}>
                  {state === 'parsing' ? <><Loader2 size={18} className="animate-spin" /> Mengambil video…</> : <>Ambil video <ArrowRight size={18} /></>}
                </button>
                <button className="secondary-button" onClick={handlePaste} disabled={busy || state === 'parsing'}><Clipboard size={17} /> Tempel tautan</button>
              </div>
              <p className="url-help" id="url-help" role="status">{state === 'parsing' ? 'Sedang membaca video. Beberapa platform memerlukan waktu lebih lama.' : active ? `Tautan ${active.name} terdeteksi. Siap diambil.` : 'Video publik saja. Pilihan format tersedia setelah video dimuat.'}</p>
            </div>
          </div>
          <div className="platform-rail">
            <span className="platform-caption">Platform yang didukung</span>
            <div className="platform-options">{PLATFORMS.map(p => (
              <button key={p.key} className={`platform-option ${active?.key === p.key ? 'is-detected' : ''}`}
                aria-label={`Gunakan tautan ${p.name}`} disabled={busy}
                onClick={() => { document.getElementById('video-url')?.focus(); setToast(`Tempel tautan ${p.name} pada kolom video.`); }}>
                <span>{p.key === 'x' ? 'X / Twitter' : p.name}</span>
              </button>
            ))}</div>
          </div>
        </section>
        <aside className="media-feature" aria-label="Video dan audio sesuai pilihanmu">
          <div className="media-feature-heading"><span>Lebih sedikit durasi.<br />Lebih banyak cerita.</span><ArrowRight size={23} /></div>
          <MediaArtwork />
          <div className="media-feature-bottom"><p>Ambil bagian terbaiknya.</p><div><span><Film size={15} /> MP4</span><span><Music size={15} /> MP3</span></div></div>
        </aside>
        </div>

        <div className="studio-assurances"><span><Check size={15} /> Tanpa akun</span><span><Monitor size={15} /> Langsung di browser</span><span><Scissors size={15} /> Potong sesuai pilihanmu</span></div>

        {/* Error Alert Box */}
        {state === 'error' && (
          <div id="conversion-error" role="alert" className="conversion-error">
            <AlertCircle size={20} className="shrink-0 mt-0.5 text-rose-500" />
            <div className="min-w-0">
              <p className="font-bold text-rose-600 dark:text-rose-400">Gagal Mengambil Video</p>
              <p className="mt-0.5 break-words leading-relaxed opacity-90">{error}</p>
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* STUDIO WORKSPACE (PREVIEW & TRIMMING CONTROLS)                 */}
        {/* ============================================================== */}
        {(state === 'preview' || busy) && (
          <section className="studio-editor anim-fade-up space-y-4 sm:space-y-5" aria-label="Pratinjau dan pengaturan potongan">
            
            {/* ============================================================== */}
            {/* 1. VIDEO PREVIEW — playback starts on user interaction.       */}
            {/* ============================================================== */}
            <div className="editor-preview glass-studio-card rounded-2xl overflow-hidden bg-black/90 shadow-2xl border border-slate-200/80 dark:border-white/10">
              
              {/* Player Header / Status Bar */}
              <div className="px-4 py-2.5 sm:py-3 bg-slate-900/95 border-b border-white/10 flex items-center justify-between flex-wrap gap-2 text-[11px] sm:text-xs font-mono text-slate-300">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse shadow-[0_0_8px_#f43f5e]" />
                  <span className="font-bold tracking-wider text-slate-200">Pratinjau video</span>
                </div>
                
                {/* Dynamic Auto Aspect Ratio Badge */}
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 text-[10px] sm:text-[11px] font-mono font-bold shadow-sm">
                    <Monitor size={12} className="text-cyan-400" />
                    <span>Rasio: {videoRatio}</span>
                  </span>
                  
                  {active && (
                    <span className={`inline-flex items-center gap-1 text-[10px] sm:text-xs font-bold px-2 py-0.5 rounded-lg border ${active.badgeClass}`}>
                      <img src={active.logo} className="w-3.5 h-3.5 rounded-sm object-cover" alt={active.name} />
                      <span>{active.name}</span>
                    </span>
                  )}
                </div>
              </div>

              {/* Responsive Video Container - Automatically Fits Vertical (TikTok/Reels) or Landscape (YouTube) */}
              <div className="relative overflow-hidden bg-black flex items-center justify-center p-2.5 sm:p-4 min-h-[220px] sm:min-h-[300px]">
                {videoError ? (
                  <div className="p-6 sm:p-8 text-center space-y-3 bg-slate-900/95 flex flex-col items-center justify-center min-h-[200px] sm:min-h-[260px]">
                    <AlertCircle size={36} className="text-rose-400 animate-bounce" />
                    <p className="text-xs sm:text-sm font-semibold text-slate-100">
                      Pratinjau video belum bisa diputar.
                    </p>
                    <p className="text-[11px] sm:text-xs text-slate-400 max-w-md leading-relaxed">
                      Kamu tetap bisa mengatur potongan ({fmt(start)} → {fmt(end)}) dan mencoba mengunduhnya.
                    </p>
                    <div className="flex items-center gap-2 flex-wrap justify-center pt-2">
                      <button
                        onClick={() => {
                          setVideoError(false);
                          setStreamAttempt((prev) => (prev === 0 ? 1 : 0));
                        }}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-cyan-500/20 text-cyan-200 border border-cyan-400/30 text-xs font-bold hover:bg-cyan-500/30 transition cursor-pointer"
                      >
                        <Play size={13} /> {streamAttempt === 0 ? 'Coba pemutar lain' : 'Coba pemutar utama'}
                      </button>
                      <button
                        onClick={() => {
                          setVideoError(false);
                          setStreamAttempt(0);
                          fetchInfo();
                        }}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-rose-500/20 text-rose-200 border border-rose-400/30 text-xs font-bold hover:bg-rose-500/30 transition cursor-pointer"
                      >
                        <RefreshCw size={13} /> Coba Muat Ulang
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <video
                      ref={videoRef}
                      key={`vid-${streamAttempt}-${streamSrc}`}
                      src={streamSrc}
                      poster={video.thumbnail}
                      controls
                      loop
                      playsInline
                      preload="metadata"
                      onPlay={() => {
                        setIsPlaying(true);
                        if (audioRef.current && audioRef.current.paused) audioRef.current.play().catch(() => {});
                      }}
                      onPause={() => {
                        setIsPlaying(false);
                        if (audioRef.current && !audioRef.current.paused) audioRef.current.pause();
                      }}
                      onVolumeChange={(e) => {
                        if (audioRef.current) {
                          audioRef.current.muted = e.target.muted;
                          audioRef.current.volume = e.target.volume;
                        }
                      }}
                      onEnded={(e) => {
                        e.target.currentTime = start || 0;
                        e.target.play().catch(() => {});
                        if (audioRef.current) {
                          audioRef.current.currentTime = start || 0;
                          audioRef.current.play().catch(() => {});
                        }
                      }}
                      onLoadedMetadata={(e) => {
                        const v = e.target;
                        if (audioRef.current) audioRef.current.currentTime = v.currentTime || 0;
                        if (v.videoWidth && v.videoHeight) {
                          const w = v.videoWidth;
                          const h = v.videoHeight;
                          const isVert = h > w;
                          setIsVertical(isVert);
                          const r = w / h;
                          if (r <= 0.65) {
                            setVideoRatio('9:16 (Vertikal / Reels)');
                          } else if (r >= 1.45) {
                            setVideoRatio('16:9 (Lanskap)');
                          } else if (Math.abs(r - 1) < 0.2) {
                            setVideoRatio('1:1 (Persegi)');
                          } else if (isVert) {
                            setVideoRatio(`${w}x${h} (Vertikal)`);
                          } else {
                            setVideoRatio(`${w}x${h} (Lanskap)`);
                          }
                        }
                        if (v.duration && Number.isFinite(v.duration) && v.duration > 0) {
                          const trueDur = Number(v.duration.toFixed(2));
                          setVideo((prev) => ({ ...prev, duration: trueDur }));
                          setEnd((prevEnd) => {
                            if (prevEnd <= 0 || prevEnd === video.duration || prevEnd > trueDur || Math.abs(prevEnd - 30) < 0.1 || Math.abs(prevEnd - 60) < 0.1) {
                              return trueDur;
                            }
                            return prevEnd;
                          });
                        }
                      }}
                      onDurationChange={(e) => {
                        const v = e.target;
                        if (v.duration && Number.isFinite(v.duration) && v.duration > 0) {
                          const trueDur = Number(v.duration.toFixed(2));
                          setVideo((prev) => ({ ...prev, duration: trueDur }));
                          setEnd((prevEnd) => {
                            if (prevEnd <= 0 || prevEnd === video.duration || prevEnd > trueDur || Math.abs(prevEnd - 30) < 0.1 || Math.abs(prevEnd - 60) < 0.1) {
                              return trueDur;
                            }
                            return prevEnd;
                          });
                        }
                      }}
                      onTimeUpdate={(e) => {
                        const ct = e.target.currentTime;
                        setNow(ct);
                        if (audioRef.current && Math.abs(audioRef.current.currentTime - ct) > 0.35) {
                          audioRef.current.currentTime = ct;
                        }
                        // Putar ulang otomatis jika mencapai batas durasi pangkas akhir
                        if (end > start && ct >= end) {
                          e.target.currentTime = start;
                          if (audioRef.current) audioRef.current.currentTime = start;
                        }
                      }}
                      onError={(e) => {
                        console.warn("Video stream load error, trying fallback...", e);
                        if (streamAttempt === 0 && video.streamUrl) {
                          setStreamAttempt(1);
                        } else {
                          setVideoError(true);
                        }
                      }}
                      className={`mx-auto rounded-xl object-contain bg-black shadow-2xl transition-all duration-300 ${
                        isVertical
                          ? 'max-h-[46vh] sm:max-h-[54vh] max-w-[260px] sm:max-w-[300px] md:max-w-[330px] w-auto'
                          : 'max-h-[36vh] sm:max-h-[46vh] w-full max-w-2xl'
                      }`}
                    />
                    {audioSrc && (
                      <audio
                        ref={audioRef}
                        key={`aud-${streamAttempt}-${audioSrc}`}
                        src={audioSrc}
                        preload="auto"
                        loop
                      />
                    )}
                  </>
                )}
              </div>

              {/* Video Title & Meta Bar */}
              <div className="p-3.5 sm:p-4 bg-slate-900/60 border-t border-white/10 flex items-start gap-3">
                {active && (
                  <span className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/20 shrink-0">
                    <img src={active.logo} className="w-5 h-5 rounded-md object-cover shadow-sm" alt={active.name} />
                  </span>
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <h2 className="font-bold text-slate-100 text-xs sm:text-sm leading-snug break-words line-clamp-2">
                      {video.title}
                    </h2>
                    {video.canonicalUrl && (
                      <a
                        href={video.canonicalUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[11px] font-mono text-slate-400 hover:text-cyan-400 inline-flex items-center gap-1 shrink-0"
                      >
                        <ExternalLink size={12} /> <span className="hidden sm:inline">Buka Asli</span>
                      </a>
                    )}
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] sm:text-xs font-mono text-slate-400">
                    <span className="inline-flex items-center gap-1">
                      <Clock size={13} className="text-rose-500" /> Total Durasi: {fmt(video.duration)}
                    </span>
                    <span className="inline-flex items-center gap-1 text-rose-400 font-bold">
                      <Scissors size={13} /> Durasi Klip: {fmt(clipLen)}
                    </span>
                    <span className="inline-flex items-center gap-1 text-cyan-400 font-semibold">
                      <Film size={13} /> Estimasi: ~{estSizeMb} MB
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* ============================================================== */}
            {/* 2. FITUR PANGKAS VIDEO (TIMELINE TEPAT DI BAWAH PREVIEW!)      */}
            {/* ============================================================== */}
            <div className="editor-trim glass-studio-card p-4 sm:p-5 rounded-2xl space-y-4 border border-rose-500/30 shadow-2xl">
              
              {/* Timeline Header & Quick Presets */}
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs sm:text-sm font-mono font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 flex items-center gap-1.5">
                    <Scissors size={15} /> Atur potongan
                  </span>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                    {fmtPrecise(clipLen)}
                  </span>
                </div>

                {/* Presets Chips */}
                <div className="flex items-center gap-1 sm:gap-1.5 flex-wrap">
                  <span className="text-[10px] font-mono text-slate-400 uppercase mr-1">Preset:</span>
                  {[
                    { label: '5s', sec: 5 },
                    { label: '15s Reels', sec: 15 },
                    { label: '30s TikTok', sec: 30 },
                    { label: '60s Shorts', sec: 60 },
                  ].map((p) => (
                    <button
                      key={p.label}
                      disabled={busy}
                      onClick={() => setPreset(p.sec)}
                      className="px-2.5 py-1 text-[10px] sm:text-xs font-mono font-semibold rounded-lg bg-slate-200/70 dark:bg-slate-800/70 text-slate-700 dark:text-slate-300 hover:bg-rose-500 hover:text-white dark:hover:bg-rose-500 transition cursor-pointer"
                    >
                      {p.label}
                    </button>
                  ))}
                  <button
                    disabled={busy}
                    onClick={resetTrim}
                    className="ml-1 px-2.5 py-1 text-[10px] sm:text-xs font-mono text-slate-400 hover:text-rose-500 transition cursor-pointer"
                  >
                    Reset
                  </button>
                </div>
              </div>

              {/* Visual Storyboard & Waveform Track */}
              <div
                ref={trackRef}
                onPointerDown={beginDrag}
                onPointerMove={moveDrag}
                onPointerUp={endDrag}
                onPointerCancel={endDrag}
                className="filmstrip-track relative h-20 sm:h-24 rounded-xl border border-slate-300 dark:border-white/15 overflow-hidden cursor-pointer bg-slate-900 shadow-inner select-none"
                style={{ touchAction: 'none' }}
              >
                {/* Background Storyboard Thumbnails Strip */}
                {video.thumbnail && (
                  <div className="absolute inset-0 flex opacity-40 pointer-events-none">
                    {[...Array(8)].map((_, idx) => (
                      <div
                        key={idx}
                        className="flex-1 bg-cover bg-center border-r border-black/30"
                        style={{ backgroundImage: `url(${video.thumbnail})` }}
                      />
                    ))}
                  </div>
                )}

                {/* Dimmed Left Region */}
                <div
                  className="absolute top-0 bottom-0 left-0 bg-black/75 backdrop-blur-[1px] pointer-events-none"
                  style={{ width: `${pct(start)}%` }}
                />

                {/* Dimmed Right Region */}
                <div
                  className="absolute top-0 bottom-0 right-0 bg-black/75 backdrop-blur-[1px] pointer-events-none"
                  style={{ width: `${100 - pct(end)}%` }}
                />

                {/* Selected Region Box */}
                <div
                  className="absolute top-0 bottom-0 bg-gradient-to-r from-rose-500/25 via-purple-500/25 to-cyan-500/25 border-y-2 border-rose-400 pointer-events-none"
                  style={{ left: `${pct(start)}%`, right: `${100 - pct(end)}%` }}
                />

                {/* Playhead Indicator */}
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-amber-400 pointer-events-none z-10 shadow-[0_0_10px_#f59e0b]"
                  style={{ left: `${pct(now)}%` }}
                >
                  <div className="w-2.5 h-2.5 bg-amber-400 rounded-full -translate-x-[4px] -translate-y-0.5 shadow-md" />
                </div>

                {/* Start Handle */}
                <div
                  role="slider"
                  tabIndex={busy ? -1 : 0}
                  aria-disabled={busy}
                  aria-label="Waktu mulai"
                  aria-valuemin={0}
                  aria-valuemax={Math.floor(video.duration)}
                  aria-valuenow={Math.floor(start)}
                  onKeyDown={(e) => {
                    if (busy) return;
                    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') e.preventDefault();
                    if (e.key === 'ArrowLeft') nudge('start', -1);
                    if (e.key === 'ArrowRight') nudge('start', 1);
                  }}
                  className="absolute top-0 bottom-0 w-9 sm:w-8 -translate-x-1/2 flex items-center justify-center outline-none group z-30 cursor-ew-resize"
                  style={{ left: `${pct(start)}%` }}
                >
                  <div className="w-3.5 sm:w-4 h-14 sm:h-16 rounded-xl bg-gradient-to-b from-rose-400 to-rose-600 border-2 border-white shadow-xl group-hover:scale-110 active:scale-115 transition-transform flex items-center justify-center">
                    <div className="w-0.5 h-6 bg-white/80 rounded" />
                  </div>
                </div>

                {/* End Handle */}
                <div
                  role="slider"
                  tabIndex={busy ? -1 : 0}
                  aria-disabled={busy}
                  aria-label="Waktu selesai"
                  aria-valuemin={0}
                  aria-valuemax={Math.floor(video.duration)}
                  aria-valuenow={Math.floor(end)}
                  onKeyDown={(e) => {
                    if (busy) return;
                    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') e.preventDefault();
                    if (e.key === 'ArrowLeft') nudge('end', -1);
                    if (e.key === 'ArrowRight') nudge('end', 1);
                  }}
                  className="absolute top-0 bottom-0 w-9 sm:w-8 -translate-x-1/2 flex items-center justify-center outline-none group z-30 cursor-ew-resize"
                  style={{ left: `${pct(end)}%` }}
                >
                  <div className="w-3.5 sm:w-4 h-14 sm:h-16 rounded-xl bg-gradient-to-b from-purple-400 to-cyan-500 border-2 border-white shadow-xl group-hover:scale-110 active:scale-115 transition-transform flex items-center justify-center">
                    <div className="w-0.5 h-6 bg-white/80 rounded" />
                  </div>
                </div>
              </div>

              {/* Timecode Steppers & Quick Mark Buttons */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                {/* Mulai (Start) Stepper */}
                <div className="time-stepper bg-slate-100/80 dark:bg-slate-900/80 border border-rose-500/30 rounded-xl p-3 flex items-center justify-between">
                  <div>
                    <div className="text-[10px] font-mono uppercase text-rose-600 dark:text-rose-400 font-bold">Mulai</div>
                    <div className="font-mono text-lg sm:text-xl font-bold text-slate-800 dark:text-slate-100 mt-0.5">{fmtPrecise(start)}</div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button disabled={busy} aria-label="Kurangi waktu mulai 1 detik" onClick={() => nudge('start', -1)} className="py-1 px-2 text-[10px] font-mono font-bold bg-slate-200 dark:bg-slate-800 rounded hover:bg-rose-500 hover:text-white transition cursor-pointer">-1s</button>
                    <button disabled={busy} aria-label="Kurangi waktu mulai 0.1 detik" onClick={() => nudge('start', -0.1)} className="py-1 px-2 text-[10px] font-mono font-bold bg-slate-200 dark:bg-slate-800 rounded hover:bg-rose-500 hover:text-white transition cursor-pointer">-.1</button>
                    <button disabled={busy} aria-label="Tambah waktu mulai 0.1 detik" onClick={() => nudge('start', 0.1)} className="py-1 px-2 text-[10px] font-mono font-bold bg-slate-200 dark:bg-slate-800 rounded hover:bg-rose-500 hover:text-white transition cursor-pointer">+.1</button>
                    <button disabled={busy} aria-label="Tambah waktu mulai 1 detik" onClick={() => nudge('start', 1)} className="py-1 px-2 text-[10px] font-mono font-bold bg-slate-200 dark:bg-slate-800 rounded hover:bg-rose-500 hover:text-white transition cursor-pointer">+1s</button>
                  </div>
                </div>

                {/* Selesai (End) Stepper */}
                <div className="time-stepper bg-slate-100/80 dark:bg-slate-900/80 border border-cyan-500/30 rounded-xl p-3 flex items-center justify-between">
                  <div>
                    <div className="text-[10px] font-mono uppercase text-cyan-600 dark:text-cyan-400 font-bold">Selesai</div>
                    <div className="font-mono text-lg sm:text-xl font-bold text-slate-800 dark:text-slate-100 mt-0.5">{fmtPrecise(end)}</div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button disabled={busy} aria-label="Kurangi waktu selesai 1 detik" onClick={() => nudge('end', -1)} className="py-1 px-2 text-[10px] font-mono font-bold bg-slate-200 dark:bg-slate-800 rounded hover:bg-cyan-500 hover:text-white transition cursor-pointer">-1s</button>
                    <button disabled={busy} aria-label="Kurangi waktu selesai 0.1 detik" onClick={() => nudge('end', -0.1)} className="py-1 px-2 text-[10px] font-mono font-bold bg-slate-200 dark:bg-slate-800 rounded hover:bg-cyan-500 hover:text-white transition cursor-pointer">-.1</button>
                    <button disabled={busy} aria-label="Tambah waktu selesai 0.1 detik" onClick={() => nudge('end', 0.1)} className="py-1 px-2 text-[10px] font-mono font-bold bg-slate-200 dark:bg-slate-800 rounded hover:bg-cyan-500 hover:text-white transition cursor-pointer">+.1</button>
                    <button disabled={busy} aria-label="Tambah waktu selesai 1 detik" onClick={() => nudge('end', 1)} className="py-1 px-2 text-[10px] font-mono font-bold bg-slate-200 dark:bg-slate-800 rounded hover:bg-cyan-500 hover:text-white transition cursor-pointer">+1s</button>
                  </div>
                </div>
              </div>

              {/* Quick Mark Playhead Buttons */}
              <div className="grid grid-cols-2 gap-2 pt-0.5">
                <button
                  disabled={busy}
                  onClick={markStart}
                  className="text-xs font-semibold rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300 py-2.5 px-2 text-center truncate hover:bg-rose-500/20 transition cursor-pointer"
                >
                  Tandai mulai
                </button>
                <button
                  disabled={busy}
                  onClick={markEnd}
                  className="text-xs font-semibold rounded-xl border border-cyan-500/30 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 py-2.5 px-2 text-center truncate hover:bg-cyan-500/20 transition cursor-pointer"
                >
                  Tandai selesai
                </button>
              </div>

            </div>

            {/* ============================================================== */}
            {/* 3. FORMAT SUITE & TOMBOL UNDUH                                 */}
            {/* ============================================================== */}
            <div className="editor-export grid md:grid-cols-12 gap-4">
              
              {/* Left: Format Selector (7 Cols) */}
              <div className="md:col-span-7 glass-studio-card p-4 sm:p-5 rounded-2xl space-y-3.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] sm:text-xs font-mono font-bold uppercase text-rose-600 dark:text-rose-400 flex items-center gap-1">
                    <Sliders size={13} /> PILIH FORMAT KELUARAN
                  </span>
                  <span className="text-[10px] font-mono text-emerald-500 dark:text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    MP4 · MP3
                  </span>
                </div>

                {/* Format 2-Tab Selector */}
                <div className="grid grid-cols-2 gap-2 bg-slate-100 dark:bg-slate-900/90 p-1.5 rounded-xl border border-slate-200 dark:border-white/10">
                  <button
                    disabled={busy} aria-pressed={format === 'mp4'}
                    onClick={() => setFormat('mp4')}
                    className={`flex items-center justify-center gap-2 py-3 px-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                      format === 'mp4'
                        ? 'btn-studio-gradient text-white shadow-md'
                        : 'text-slate-600 dark:text-slate-400 hover:text-rose-500'
                    }`}
                  >
                    <Tv size={16} />
                    <span>MP4 Video</span>
                  </button>
                  <button
                    disabled={busy} aria-pressed={format === 'mp3'}
                    onClick={() => setFormat('mp3')}
                    className={`flex items-center justify-center gap-2 py-3 px-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                      format === 'mp3'
                        ? 'btn-studio-gradient text-white shadow-md'
                        : 'text-slate-600 dark:text-slate-400 hover:text-purple-500'
                    }`}
                  >
                    <Volume2 size={16} />
                    <span>MP3 Audio</span>
                  </button>
                </div>

                {/* Resolution selector for MP4 */}
                {format === 'mp4' && (
                  <div className="anim-fade-up">
                    <label htmlFor="video-resolution" className="block text-[10px] font-mono font-bold uppercase text-slate-500 dark:text-slate-400 mb-1.5">
                      Resolusi video
                    </label>
                    <select id="video-resolution" disabled={busy}
                      value={resolution}
                      onChange={(e) => setResolution(e.target.value)}
                      className="w-full rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-white/15 px-3 py-2.5 text-xs font-semibold text-slate-800 dark:text-slate-100 outline-none focus:ring-2 focus:ring-rose-500/40 shadow-sm cursor-pointer"
                    >
                      {resOptions.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Audio Format Info for MP3 */}
                {format === 'mp3' && (
                  <div className="anim-fade-up p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 text-xs text-purple-700 dark:text-purple-300 font-mono flex items-center gap-2">
                    <Music size={15} className="text-purple-500 shrink-0" />
                    <span>Simpan suara sebagai <b>MP3 320 kbps</b>.</span>
                  </div>
                )}
              </div>

              {/* Right: Metrics & Download Button (5 Cols) */}
              <div className="md:col-span-5 glass-studio-card p-4 sm:p-5 rounded-2xl space-y-3.5 flex flex-col justify-between">
                <div className="space-y-2 text-xs font-mono">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 dark:text-slate-400">Rentang Waktu:</span>
                    <span className="text-rose-600 dark:text-rose-400 font-bold">{fmtPrecise(start)} → {fmtPrecise(end)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 dark:text-slate-400">Estimasi Ukuran:</span>
                    <span className="text-cyan-600 dark:text-cyan-400 font-bold">~{estSizeMb} MB</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 dark:text-slate-400">Koneksi server:</span>
                    <BackendStatus status={backendPing} />
                  </div>
                </div>

                {/* Progress Indicator */}
                {busy && (
                  <div className="anim-fade-up p-3.5 rounded-xl border border-rose-500/30 bg-rose-500/10 space-y-2">
                    <div className="flex items-center justify-between text-xs font-mono font-bold text-rose-600 dark:text-rose-400">
                      <span className="inline-flex items-center gap-1.5">
                        <Clock size={13} className="text-amber-400 animate-spin-slow" /> Waktu: {fmtElapsed(elapsedMs)}
                      </span>
                      {displayPct !== null && <span className="text-cyan-500 dark:text-cyan-400 font-extrabold">{displayPct}%</span>}
                    </div>

                    <div className="flex items-center justify-between text-xs font-semibold text-slate-800 dark:text-slate-200">
                      <span className="inline-flex items-center gap-1.5 text-[11px]">
                        {state === 'processing' ? (
                          <>
                            <Loader2 className="animate-spin text-rose-500 shrink-0" size={13} /> Menyiapkan file…
                          </>
                        ) : (
                          <>
                            <Download size={13} className="text-cyan-400 animate-bounce shrink-0" /> Mengunduh file… {humanBytes(prog?.loaded || 0)}
                          </>
                        )}
                      </span>
                    </div>

                    {displayPct !== null && <div role="progressbar" aria-label="Kemajuan unduhan" aria-valuenow={displayPct} aria-valuemin={0} aria-valuemax={100} className="h-2.5 rounded-full overflow-hidden bg-slate-200 dark:bg-slate-900 border border-rose-500/20 p-0.5 shadow-inner">
                      <div
                        className="h-full bg-gradient-to-r from-rose-500 via-purple-500 to-cyan-400 transition-all duration-300 rounded-full shadow-md"
                        style={{ width: `${displayPct}%` }}
                      />
                    </div>}
                  </div>
                )}

                {/* Big Action Download Button */}
                <button
                  onClick={download}
                  disabled={busy}
                  className="w-full py-3.5 sm:py-4 rounded-xl font-display font-black text-xs sm:text-sm tracking-wide btn-studio-gradient text-white shadow-xl shadow-rose-500/30 transition-all transform hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
                >
                  {busy ? (
                    <>
                      <Loader2 className="animate-spin text-white" size={17} />
                      <span>{state === 'downloading' ? 'Mengunduh…' : 'Memproses…'}</span>
                    </>
                  ) : (
                    <>
                      <Download size={17} />
                      <span>UNDUH {format.toUpperCase()} ({fmt(clipLen)})</span>
                    </>
                  )}
                </button>
              </div>

            </div>

            {/* Sidebar / Bottom Ad Placement */}
            <div className="editor-sponsor pt-2">
              <div className="hidden md:block">
                <AdBanner728 />
              </div>
              <div className="block md:hidden">
                <AdBanner300 />
              </div>
            </div>
          </section>
        )}

        {(state !== 'preview' && !busy) && <div className="sponsor-slot"><div className="hidden md:block"><AdBanner728 /></div><div className="block md:hidden"><AdBanner300 /></div></div>}

        <section id="platforms" className="platform-section content-section">
          <div className="section-heading"><h2>Semua sumber. Satu studio.</h2><p>Video panjang, klip singkat, atau audio favorit. Bawa tautan publiknya ke sini.</p></div>
          <div className="platform-directory">{PLATFORM_DETAILS.map(p => <button key={p.key} className="directory-row" onClick={() => { document.getElementById('video-url')?.focus(); setToast(`Tempel tautan ${p.name} untuk mulai.`); }}>
            <img src={`/logos/logo_${p.key}.png`} width="32" height="32" alt="" /><span>{p.name.split(' ')[0]}</span><ArrowRight size={17} />
          </button>)}</div>
        </section>

        <section id="features" className="features-section content-section">
          <div className="section-heading"><h2>Simpan yang kamu perlukan.</h2><p>Satu ruang kerja untuk video utuh, potongan pendek, dan audio.</p></div>
          <div className="feature-layout">
            <article className="feature-main"><Scissors size={25} /><h3>Pas di momen yang kamu mau.</h3><p>Geser titik mulai dan selesai, atau tentukan waktunya dengan lebih presisi. Simpan bagian pilihanmu tanpa mengedit di aplikasi lain.</p><a className="text-link" href="#converter">Mulai potong video <ArrowRight size={16} /></a></article>
            <div className="feature-notes"><article><Music size={22} /><div><h3>Videonya. Atau cukup suaranya.</h3><p>Pilih MP4 untuk video, atau MP3 untuk menyimpan audio.</p></div></article><article><Monitor size={22} /><div><h3>Dari browser ke perangkatmu.</h3><p>Atur kualitas yang tersedia, lihat pratinjau, lalu unduh hasilnya.</p></div></article></div>
          </div>
        </section>

        <section id="how-it-works" className="guide-section content-section">
          <div className="section-heading"><h2>Dari tautan ke klip.</h2><p>Empat langkah, semuanya di halaman ini.</p></div>
          <ol className="guide-steps">{[
            ['Salin tautan', 'Buka video di platform asal, lalu pilih Salin Tautan.'],
            ['Ambil video', 'Tempel tautan di atas dan klik Ambil video.'],
            ['Pilih bagian', 'Atur awal, akhir, kualitas, dan format file.'],
            ['Simpan hasil', 'Klik Unduh dan tunggu sampai file siap.'],
          ].map(([title, desc], i) => <li key={title}><span className="step-number">0{i + 1}</span><h3>{title}</h3><p>{desc}</p></li>)}</ol>
        </section>

        <section id="faq" className="faq-section content-section">
          <div className="section-heading"><h2>Ada yang ingin ditanyakan?</h2><p>Beberapa hal sebelum kamu mulai.</p><a className="text-link" href="#converter">Kembali ke ruang edit <ArrowRight size={16} /></a></div>
          <div className="faq-list">{FAQS.map((faq, idx) => <div className="faq-item" key={faq.q}>
            <h3><button onClick={() => setOpenFaq(openFaq === idx ? null : idx)} aria-expanded={openFaq === idx} aria-controls={`faq-answer-${idx}`}><span>{faq.q}</span><ChevronDown size={18} className={openFaq === idx ? 'rotate-180' : ''} /></button></h3>
            <div id={`faq-answer-${idx}`} hidden={openFaq !== idx}><p>{faq.a}</p></div>
          </div>)}</div>
        </section>

        {/* Native Ad Placement at the Bottom */}
        <div className="mt-14">
          <AdNativeBanner />
        </div>
      </main>

      {/* Professional Footer */}
      <Footer onOpenModal={(docKey) => setActiveModal(docKey)} backendPing={backendPing} />

      {/* Legal Modals (Privacy, Terms, Disclaimer) */}
      {activeModal && (
        <LegalModal docKey={activeModal} onClose={() => setActiveModal(null)} />
      )}

      {/* Toast Notification */}
      {toast && (
        <div className="studio-toast" role="status">
          <CheckCircle size={18} /> {toast}
        </div>
      )}
    </div>
  );
}

function MediaArtwork() {
  return <svg className="media-artwork" viewBox="0 0 400 300" aria-hidden="true" focusable="false">
    <ellipse cx="207" cy="260" rx="126" ry="13" fill="var(--color-art-shadow)" />
    <g transform="rotate(13 227 139)">
      <rect x="135" y="45" width="196" height="167" rx="18" fill="var(--color-art-sheet)" />
      <rect x="149" y="60" width="168" height="137" rx="9" fill="var(--color-art-ground)" />
      <path d="M161 166L202 126L231 151L254 133L305 183H161Z" fill="var(--color-art-line)" />
      <circle cx="275" cy="94" r="14" fill="var(--color-art-sheet)" />
    </g>
    <g transform="rotate(-13 171 169)">
      <rect x="58" y="102" width="215" height="148" rx="19" fill="var(--color-art-depth)" />
      <rect x="58" y="92" width="215" height="148" rx="19" fill="var(--color-art-lime)" />
      <path d="M149 132L193 159Q202 165 193 171L149 198Q141 203 141 193V137Q141 127 149 132Z" fill="var(--color-art-ground)" />
      {[80,112,144,176,208,240].map(x => <g key={x}><rect x={x} y="103" width="12" height="7" rx="2" fill="var(--color-art-ground)" /><rect x={x} y="222" width="12" height="7" rx="2" fill="var(--color-art-ground)" /></g>)}
    </g>
    <path d="M315 211L345 241M319 247L346 216" stroke="var(--color-art-sheet)" strokeWidth="3" strokeLinecap="round" />
    <circle cx="308" cy="203" r="9" fill="none" stroke="var(--color-art-sheet)" strokeWidth="3" />
    <circle cx="310" cy="255" r="9" fill="none" stroke="var(--color-art-sheet)" strokeWidth="3" />
    <path d="M34 77L100 60" stroke="var(--color-art-line)" strokeWidth="2" strokeDasharray="5 7" />
  </svg>;
}

function mapNetErr(e) {
  const m = (e && e.message) || String(e);
  if (/Failed to fetch|NetworkError|Load failed/i.test(m)) {
    return `Tidak bisa terhubung ke backend server (${API}). Pastikan backend aktif.`;
  }
  if (/Video unavailable/i.test(m)) {
    return 'Video tidak ditemukan, telah dihapus, atau bersifat privat di YouTube.';
  }
  if (/Sign in to confirm you're not a bot/i.test(m)) {
    return 'YouTube meminta verifikasi bot pada server cloud. Coba tautan video lain atau platform lain (TikTok/IG).';
  }
  return m;
}

/* ---- Adsterra Monetization Components -------------------------------------- */

function AdBanner728() {
  const srcDoc = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body { display: flex; justify-content: center; align-items: center; background: transparent; overflow: hidden; }
        </style>
      </head>
      <body>
        <script type="text/javascript">
          atOptions = {
            'key' : '37bfff0b33828fb26595d61a7e75f2c4',
            'format' : 'iframe',
            'height' : 90,
            'width' : 728,
            'params' : {}
          };
        </script>
        <script type="text/javascript" src="https://www.highrevenueformat.com/37bfff0b33828fb26595d61a7e75f2c4/invoke.js"></script>
      </body>
    </html>
  `;

  return (
    <div className="flex flex-col items-center justify-center my-3 overflow-hidden">
      <span className="ad-label text-[9px] font-mono tracking-widest text-slate-400 dark:text-slate-500 uppercase mb-1">
        Sponsored Utility
      </span>
      <div className="ad-surface w-[728px] h-[90px] max-w-full overflow-hidden flex items-center justify-center rounded-2xl bg-slate-100 dark:bg-slate-900/40 border border-slate-200 dark:border-white/10 shadow-sm">
        <iframe
          title="ad-728x90"
          srcDoc={srcDoc}
          width="728"
          height="90"
          style={{ border: 'none', overflow: 'hidden' }}
          scrolling="no"
        />
      </div>
    </div>
  );
}

function AdBanner300() {
  const srcDoc = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body { display: flex; justify-content: center; align-items: center; background: transparent; overflow: hidden; }
        </style>
      </head>
      <body>
        <script type="text/javascript">
          atOptions = {
            'key' : 'd9361be5c0aab62c2c81652f4e02b601',
            'format' : 'iframe',
            'height' : 250,
            'width' : 300,
            'params' : {}
          };
        </script>
        <script type="text/javascript" src="https://www.highrevenueformat.com/d9361be5c0aab62c2c81652f4e02b601/invoke.js"></script>
      </body>
    </html>
  `;

  return (
    <div className="flex flex-col items-center justify-center my-2.5 overflow-hidden">
      <span className="ad-label text-[9px] font-mono tracking-widest text-slate-400 dark:text-slate-500 uppercase mb-1">
        Sponsored Content
      </span>
      <div className="ad-surface w-[300px] h-[250px] overflow-hidden flex items-center justify-center rounded-2xl bg-slate-100 dark:bg-slate-900/40 border border-slate-200 dark:border-white/10 shadow-sm">
        <iframe
          title="ad-300x250"
          srcDoc={srcDoc}
          width="300"
          height="250"
          style={{ border: 'none', overflow: 'hidden' }}
          scrolling="no"
        />
      </div>
    </div>
  );
}

function AdNativeBanner() {
  const adRef = useRef(null);

  useEffect(() => {
    const el = adRef.current;
    if (!el || el.querySelector('script')) return;

    try {
      const invokeScript = document.createElement('script');
      invokeScript.async = true;
      invokeScript.setAttribute('data-cfasync', 'false');
      invokeScript.src = 'https://pl31025851.profitableratecpmnetwork.com/b52019ce5352c5da703df76d0a336b9a/invoke.js';

      el.appendChild(invokeScript);
    } catch (_) {}
  }, []);

  return (
    <div className="w-full max-w-4xl mx-auto my-4 px-2" ref={adRef}>
      <div className="flex items-center justify-center mb-1">
        <span className="ad-label text-[9px] font-mono tracking-widest text-slate-400 dark:text-slate-500 uppercase">
          Sponsored Recommendation
        </span>
      </div>
      <div
        id="container-b52019ce5352c5da703df76d0a336b9a"
        className="ad-surface min-h-[60px] rounded-2xl overflow-hidden flex items-center justify-center bg-slate-100 dark:bg-slate-900/30 border border-slate-200 dark:border-white/10"
      />
    </div>
  );
}

/* ---- Professional Footer & Compliance Modals ----------------------------- */

function BackendStatus({ status }) {
  return <span role="status" className={status.online ? 'text-emerald-500' : 'text-slate-500'}>
    {status.online === null ? 'Memeriksa server…' : status.online ? `Server Online (${status.latency}ms)` : 'Server Offline'}
  </span>;
}

function Footer({ onOpenModal, backendPing }) {
  return <footer className="studio-footer page-width">
    <div className="footer-top"><a href="#" className="studio-brand"><span>Kliprava<span className="brand-period">.</span></span></a><p>Potongan kecil. Cerita yang berarti.</p><BackendStatus status={backendPing} /></div>
    <div className="footer-bottom"><p>© 2026 Kliprava · Dav’site</p><nav aria-label="Kebijakan"><button onClick={() => onOpenModal('privacy')}>Privasi</button><button onClick={() => onOpenModal('terms')}>Ketentuan</button><button onClick={() => onOpenModal('disclaimer')}>Hak cipta</button><a href="#faq">Bantuan</a></nav></div>
  </footer>;
}

function LegalModal({ docKey, onClose }) {
  const doc = LEGAL_DOCS[docKey];
  const dialogRef = useRef(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);
  if (!doc) return null;

  return (
    <dialog ref={dialogRef} aria-labelledby="legal-modal-title" className="legal-dialog" onCancel={onClose} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div
        className="legal-content relative w-full max-w-2xl max-h-[85vh] flex flex-col rounded-2xl glass-studio-card bg-white/95 dark:bg-[#0c101c]/95 border border-slate-200 dark:border-white/15 shadow-2xl overflow-hidden"
      >
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-slate-200 dark:border-white/10 flex items-center justify-between">
          <div>
            <h3 id="legal-modal-title" className="font-display font-bold text-base text-slate-900 dark:text-slate-100">
              {doc.title}
            </h3>
            <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
              Terakhir diperbarui: {doc.updated}
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Tutup dialog dokumen legalitas"
            className="p-1.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-5 overflow-y-auto space-y-4 text-slate-700 dark:text-slate-300 text-xs sm:text-sm">
          {doc.sections.map((sec, idx) => (
            <div key={idx} className="space-y-1.5 pb-2">
              <h4 className="font-bold text-slate-900 dark:text-slate-100 text-xs sm:text-sm">
                {sec.heading}
              </h4>
              <p className="text-slate-600 dark:text-slate-400 text-xs leading-relaxed">
                {sec.content}
              </p>
            </div>
          ))}
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-slate-200 dark:border-white/10 bg-slate-50/80 dark:bg-slate-900/80 flex items-center justify-between">
          <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">
            Dokumen Kliprava
          </span>
          <button
            onClick={onClose}
            className="btn-studio-gradient px-4 py-2 rounded-xl text-xs font-bold text-white shadow-md cursor-pointer hover:opacity-95"
          >
            Saya Mengerti
          </button>
        </div>
      </div>
    </dialog>
  );
}



