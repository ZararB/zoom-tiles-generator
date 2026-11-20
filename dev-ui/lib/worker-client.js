/**
 * Same-origin calls via serve_dev_ui.py proxy → pod_server.py
 */
const PREFIX = '/api/tile-worker';

export async function workerHealth() {
  const res = await fetch(`${PREFIX}/health`);
  if (!res.ok) throw new Error(`health ${res.status}`);
  return res.json();
}

export async function workerEdit(body) {
  const res = await fetch(`${PREFIX}/edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || data.error || `edit ${res.status}`);
  }
  return data;
}
