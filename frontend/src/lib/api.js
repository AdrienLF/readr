const BASE = '/api';

async function req(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

const get = (path) => req('GET', path);
const post = (path, body) => req('POST', path, body);
const put = (path, body) => req('PUT', path, body);
const patch = (path, body) => req('PATCH', path, body);
const del = (path) => req('DELETE', path);

// Feeds
export const feeds = {
  list: () => get('/feeds'),
  get: (id) => get(`/feeds/${id}`),
  add: (url, topic_ids = []) => post('/feeds', { url, topic_ids }),
  update: (id, data) => put(`/feeds/${id}`, data),
  delete: (id) => del(`/feeds/${id}`),
  refresh: (id) => post(`/feeds/${id}/refresh`),
  refreshAll: () => post('/feeds/refresh-all'),
};

// Articles
export const articles = {
  list: (params = {}) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) q.set(k, v);
    }
    return get(`/articles?${q}`);
  },
  get: (id) => get(`/articles/${id}`),
  search: (q, page = 1) => get(`/articles/search?q=${encodeURIComponent(q)}&page=${page}`),
  markRead: (id, is_read = true) => patch(`/articles/${id}/read?is_read=${is_read}`),
  toggleBookmark: (id) => patch(`/articles/${id}/bookmark`),
  getComments: (id) => get(`/articles/${id}/comments`),
};

// Topics
export const topics = {
  list: () => get('/topics'),
  create: (data) => post('/topics', data),
  update: (id, data) => put(`/topics/${id}`, data),
  delete: (id) => del(`/topics/${id}`),
};

// Digests
export const digests = {
  list: (date) => get(`/digests${date ? `?target_date=${date}` : ''}`),
  generate: (topic_id, date) => post('/digests/generate', { topic_id, date }),
};

// Settings
export const settings = {
  get: () => get('/settings'),
  update: (data) => put('/settings', data),
};
