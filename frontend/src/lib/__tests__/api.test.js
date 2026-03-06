/**
 * Unit tests for the API client (src/lib/api.js).
 * fetch is mocked globally — no real HTTP.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// We test the module in isolation by mocking global fetch
function mockFetch(status, body) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  });
}

function mockFetch204() {
  return vi.fn().mockResolvedValue({
    ok: true,
    status: 204,
    json: () => Promise.reject(new Error('no body')),
  });
}

// Dynamic import so we can re-import after setting up fetch mock
async function getApi() {
  return await import('$lib/api.js');
}

describe('feeds API', () => {
  afterEach(() => vi.restoreAllMocks());

  it('feeds.list() calls GET /api/feeds', async () => {
    global.fetch = mockFetch(200, [{ id: 1, title: 'Test Feed' }]);
    const { feeds } = await import('$lib/api.js');
    const result = await feeds.list();
    expect(fetch).toHaveBeenCalledWith('/api/feeds', expect.objectContaining({ method: 'GET' }));
    expect(result).toEqual([{ id: 1, title: 'Test Feed' }]);
  });

  it('feeds.add() calls POST /api/feeds with body', async () => {
    global.fetch = mockFetch(201, { id: 1, url: 'https://example.com/feed.rss' });
    const { feeds } = await import('$lib/api.js');
    const result = await feeds.add('https://example.com/feed.rss', [1, 2]);
    expect(fetch).toHaveBeenCalledWith(
      '/api/feeds',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ url: 'https://example.com/feed.rss', topic_ids: [1, 2] }),
      }),
    );
    expect(result.id).toBe(1);
  });

  it('feeds.delete() calls DELETE /api/feeds/:id', async () => {
    global.fetch = mockFetch204();
    const { feeds } = await import('$lib/api.js');
    const result = await feeds.delete(42);
    expect(fetch).toHaveBeenCalledWith('/api/feeds/42', expect.objectContaining({ method: 'DELETE' }));
    expect(result).toBeNull();
  });

  it('throws on error response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: () => Promise.resolve({ detail: 'Feed URL already exists' }),
    });
    const { feeds } = await import('$lib/api.js');
    await expect(feeds.add('duplicate-url')).rejects.toThrow('Feed URL already exists');
  });
});

describe('articles API', () => {
  afterEach(() => vi.restoreAllMocks());

  it('articles.list() builds correct query string', async () => {
    global.fetch = mockFetch(200, { items: [], total: 0, page: 1, page_size: 30, has_more: false });
    const { articles } = await import('$lib/api.js');
    await articles.list({ topic_id: 5, page: 2, page_size: 10 });
    const calledUrl = fetch.mock.calls[0][0];
    expect(calledUrl).toContain('topic_id=5');
    expect(calledUrl).toContain('page=2');
    expect(calledUrl).toContain('page_size=10');
  });

  it('articles.list() omits null/undefined params', async () => {
    global.fetch = mockFetch(200, { items: [], total: 0, page: 1, page_size: 30, has_more: false });
    const { articles } = await import('$lib/api.js');
    await articles.list({ topic_id: null, feed_id: undefined, page: 1 });
    const calledUrl = fetch.mock.calls[0][0];
    expect(calledUrl).not.toContain('topic_id');
    expect(calledUrl).not.toContain('feed_id');
  });

  it('articles.search() encodes query string', async () => {
    global.fetch = mockFetch(200, { items: [], total: 0, page: 1, page_size: 30, has_more: false });
    const { articles } = await import('$lib/api.js');
    await articles.search('hello world');
    const calledUrl = fetch.mock.calls[0][0];
    expect(calledUrl).toContain('hello%20world');
  });

  it('articles.markRead() calls PATCH with correct param', async () => {
    global.fetch = mockFetch(200, { id: 1, is_read: true });
    const { articles } = await import('$lib/api.js');
    await articles.markRead(1, true);
    expect(fetch).toHaveBeenCalledWith(
      '/api/articles/1/read?is_read=true',
      expect.anything(),
    );
  });

  it('articles.toggleBookmark() calls PATCH', async () => {
    global.fetch = mockFetch(200, { id: 1, is_bookmarked: true });
    const { articles } = await import('$lib/api.js');
    await articles.toggleBookmark(1);
    expect(fetch).toHaveBeenCalledWith('/api/articles/1/bookmark', expect.anything());
  });
});

describe('topics API', () => {
  afterEach(() => vi.restoreAllMocks());

  it('topics.create() sends correct payload', async () => {
    global.fetch = mockFetch(201, { id: 1, name: 'Tech', color: '#6366f1' });
    const { topics } = await import('$lib/api.js');
    await topics.create({ name: 'Tech', color: '#6366f1' });
    expect(fetch).toHaveBeenCalledWith(
      '/api/topics',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'Tech', color: '#6366f1' }),
      }),
    );
  });
});

describe('settings API', () => {
  afterEach(() => vi.restoreAllMocks());

  it('settings.get() calls GET /api/settings', async () => {
    const mockSettings = { digest_time: '07:00', ollama_model: 'qwen3.5:9b', fetch_interval: 3600 };
    global.fetch = mockFetch(200, mockSettings);
    const { settings } = await import('$lib/api.js');
    const result = await settings.get();
    expect(result).toEqual(mockSettings);
  });

  it('settings.update() sends PUT with body', async () => {
    global.fetch = mockFetch(200, { digest_time: '08:00', ollama_model: 'qwen3.5:9b', fetch_interval: 3600 });
    const { settings } = await import('$lib/api.js');
    await settings.update({ digest_time: '08:00' });
    expect(fetch).toHaveBeenCalledWith(
      '/api/settings',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ digest_time: '08:00' }),
      }),
    );
  });
});
