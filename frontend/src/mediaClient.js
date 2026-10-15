export const DEFAULT_API = 'https://kliprava-api-production.up.railway.app';

export function backendUrl(configuredUrl, development = false) {
  const fallback = development ? 'http://localhost:8000' : DEFAULT_API;
  const value = configuredUrl?.trim();
  if (!value) return fallback;

  try {
    const address = value.startsWith('//')
      ? `https:${value}`
      : /^[a-z][a-z\d+.-]*:\/\//i.test(value) ? value : `https://${value}`;
    const parsed = new URL(address);
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      throw new Error('VITE_API_URL harus menggunakan HTTP atau HTTPS.');
    }
    return parsed.href.replace(/\/+$/, '');
  } catch (_) {
    console.warn('VITE_API_URL tidak valid; memakai alamat backend bawaan.');
    return fallback;
  }
}

export async function checkBackend(api, signal) {
  const started = Date.now();
  try {
    const response = await fetch(`${api}/api/health`, { signal });
    if (!response.ok) throw new Error('Backend unavailable');
    const health = await response.json();
    if (health.status !== 'HEALTHY') throw new Error('Backend unhealthy');
    return { online: true, latency: Date.now() - started };
  } catch (_) {
    return { online: false, latency: null };
  }
}

export function processPayload(video, start, end, format, resolution) {
  if (!video.canonicalUrl) throw new Error('Muat video sebelum mengunduh.');
  return {
    url: video.canonicalUrl,
    start_time: Number(start.toFixed(2)),
    end_time: Number(end.toFixed(2)),
    format,
    resolution: format === 'mp4' ? resolution : 'best',
  };
}
