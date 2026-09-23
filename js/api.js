// Ghost Frame — API client
// All pages import this to talk to the backend

const API_BASE = 'http://localhost:8000';

function getToken() {
  try {
    const raw = localStorage.getItem('sb-session');
    if (!raw) return null;
    return JSON.parse(raw)?.access_token || null;
  } catch { return null; }
}

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }
  const res = await fetch(API_BASE + path, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  if (res.status === 204) return null;
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res;
}

// ── Projects ──────────────────────────────────────────────────────────────
export const projects = {
  list:   ()           => apiFetch('/api/projects'),
  get:    (id)         => apiFetch(`/api/projects/${id}`),
  create: (data)       => apiFetch('/api/projects', { method: 'POST', body: data }),
  update: (id, data)   => apiFetch(`/api/projects/${id}`, { method: 'PATCH', body: data }),
  remove: (id)         => apiFetch(`/api/projects/${id}`, { method: 'DELETE' }),
};

// ── Discover ──────────────────────────────────────────────────────────────
export const discover = {
  list:   (params = {}) => apiFetch('/api/discover?' + new URLSearchParams(params)),
  get:    (id)           => apiFetch(`/api/discover/${id}`),
  create: (data)         => apiFetch('/api/discover', { method: 'POST', body: data }),
  remove: (id)           => apiFetch(`/api/discover/${id}`, { method: 'DELETE' }),
  like:   (id)           => apiFetch(`/api/discover/${id}/like`, { method: 'POST' }),
};

// ── Process (AI effects) ──────────────────────────────────────────────────
export const process = {
  run: async (effect, file, save = false) => {
    const form = new FormData();
    form.append('file', file);
    form.append('save', save);
    const res = await apiFetch(`/api/process/${effect}`, { method: 'POST', body: form });
    // Returns raw Response — caller converts to blob/objectURL
    return res;
  },
};

// ── Profile ───────────────────────────────────────────────────────────────
export const profile = {
  me:     ()       => apiFetch('/api/profiles/me'),
  update: (data)   => apiFetch('/api/profiles/me', { method: 'PATCH', body: data }),
  get:    (username) => apiFetch(`/api/profiles/${username}`),
};

export default { projects, discover, process, profile };
