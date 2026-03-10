const BASE = '/api';

async function req(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    const message = Array.isArray(detail)
      ? detail.map((e) => e.msg || JSON.stringify(e)).join('; ')
      : detail || `HTTP ${res.status}`;
    throw new Error(message);
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
  exportOpml: () => fetch('/api/feeds/opml').then((r) => r.blob()),
  importOpml: (file) => {
    const form = new FormData();
    form.append('file', file);
    return fetch('/api/feeds/opml', { method: 'POST', body: form }).then((r) => r.json());
  },
  discover: (url) => get(`/feeds/discover?url=${encodeURIComponent(url)}`),
  bulkClassify: (urls) => post('/feeds/bulk-classify', { urls }),
  bulkImport: (data) => post('/feeds/bulk-import', data),
};

// Mute filters
export const filters = {
  list: () => get('/filters'),
  create: (data) => post('/filters', data),
  delete: (id) => del(`/filters/${id}`),
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
  toggleSaved: (id) => patch(`/articles/${id}/saved`),
  updateNote: (id, note) => patch(`/articles/${id}/note`, { note }),
  summarize: (id) => post(`/articles/${id}/summarize`),
  addTag: (id, tag_id) => post(`/articles/${id}/tags/${tag_id}`),
  removeTag: (id, tag_id) => del(`/articles/${id}/tags/${tag_id}`),
  getComments: (id) => get(`/articles/${id}/comments`),
  signal: (id, signal) => post(`/articles/${id}/signal`, { signal }),
  addHighlight: (id, data) => post(`/articles/${id}/highlights`, data),
  deleteHighlight: (id, highlight_id) => del(`/articles/${id}/highlights/${highlight_id}`),
  extractEntities: (id) => post(`/articles/${id}/entities`),
};

// Entities
export const entities = {
  trending: (hours = 24) => get(`/entities/trending?hours=${hours}`),
};

// Tags
export const tags = {
  list: () => get('/tags'),
  create: (data) => post('/tags', data),
  delete: (id) => del(`/tags/${id}`),
};

// Rules
export const rules = {
  list: () => get('/rules'),
  create: (data) => post('/rules', data),
  update: (id, data) => patch(`/rules/${id}`, data),
  delete: (id) => del(`/rules/${id}`),
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
  generate: (topic_id, date, force = true) => post('/digests/generate', { topic_id: topic_id ?? null, date: date ?? null, force }),
};

// Saved searches
export const savedSearches = {
  list: () => get('/saved-searches'),
  create: (data) => post('/saved-searches', data),
  update: (id, data) => put(`/saved-searches/${id}`, data),
  delete: (id) => del(`/saved-searches/${id}`),
  articles: (id, params = {}) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) q.set(k, v);
    }
    return get(`/saved-searches/${id}/articles?${q}`);
  },
  refreshTerms: (id) => post(`/saved-searches/${id}/refresh-terms`),
};

// Settings
export const settings = {
  get: () => get('/settings'),
  update: (data) => put('/settings', data),
  ollamaModels: () => get('/settings/ollama-models'),
};
