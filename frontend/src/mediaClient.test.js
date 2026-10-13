import test from 'node:test';
import assert from 'node:assert/strict';
import { backendUrl, checkBackend, processPayload, DEFAULT_API } from './mediaClient.js';

test('explicit API URLs including localhost are honored', () => {
  assert.equal(backendUrl('http://localhost:8000/'), 'http://localhost:8000');
  assert.equal(backendUrl('http://127.0.0.1:8000'), 'http://127.0.0.1:8000');
  assert.equal(backendUrl('https://api.example.com/'), 'https://api.example.com');
  assert.equal(backendUrl('', true), 'http://localhost:8000');
  assert.equal(backendUrl('', false), DEFAULT_API);
});

test('export uses the preview URL and trim even if input is subsequently edited', () => {
  const preview = { canonicalUrl: 'https://youtube.com/watch?v=videoA' };
  const payload = processPayload(preview, 1.234, 4.567, 'mp4', '1080');
  assert.deepEqual(payload, { url: preview.canonicalUrl, start_time: 1.23, end_time: 4.57, format: 'mp4', resolution: '1080' });
  assert.equal(processPayload(preview, 0, 10, 'mp3', '1080').resolution, 'best');
  assert.throws(() => processPayload({}, 0, 1, 'mp4', 'best'));
});

test('health distinguishes healthy responses, HTTP errors, network errors and unhealthy bodies', async (t) => {
  for (const [name, fetchImpl, expected] of [
    ['healthy', async () => ({ ok: true, json: async () => ({ status: 'HEALTHY' }) }), true],
    ['http error', async () => ({ ok: false }), false],
    ['offline', async () => { throw new Error('offline'); }, false],
    ['unhealthy', async () => ({ ok: true, json: async () => ({ status: 'UNHEALTHY' }) }), false],
  ]) {
    await t.test(name, async (t) => {
      t.mock.method(globalThis, 'fetch', fetchImpl);
      const result = await checkBackend('https://example.invalid');
      assert.equal(result.online, expected);
      if (!expected) assert.equal(result.latency, null);
    });
  }
});
