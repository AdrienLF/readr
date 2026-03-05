/**
 * Unit tests for the AppState store (app.svelte.js).
 * Uses Svelte 5 runes — requires vitest with svelte plugin.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the API module
vi.mock('$lib/api.js', () => ({
  feeds: {
    list: vi.fn().mockResolvedValue([
      { id: 1, title: 'Feed A', unread_count: 5, topics: [{ id: 10, name: 'Tech', color: '#6366f1' }] },
      { id: 2, title: 'Feed B', unread_count: 3, topics: [] },
    ]),
  },
  topics: {
    list: vi.fn().mockResolvedValue([
      { id: 10, name: 'Tech', color: '#6366f1', feed_count: 1 },
      { id: 11, name: 'Finance', color: '#f59e0b', feed_count: 0 },
    ]),
  },
}));

// Import AFTER mocking
const { app } = await import('$lib/stores/app.svelte.js');

describe('AppState — navigation', () => {
  beforeEach(() => {
    app.selectedTopicId = null;
    app.activeView = 'feed';
    app.readerOpen = false;
    app.selectedArticleId = null;
  });

  it('initial state is correct', () => {
    expect(app.selectedTopicId).toBeNull();
    expect(app.activeView).toBe('feed');
    expect(app.readerOpen).toBe(false);
    expect(app.selectedArticleId).toBeNull();
  });

  it('selectTopic sets selectedTopicId and closes reader', () => {
    app.readerOpen = true;
    app.selectTopic(10);
    expect(app.selectedTopicId).toBe(10);
    expect(app.activeView).toBe('feed');
  });

  it('selectTopic(null) selects all topics', () => {
    app.selectedTopicId = 10;
    app.selectTopic(null);
    expect(app.selectedTopicId).toBeNull();
  });
});

describe('AppState — article reader', () => {
  beforeEach(() => {
    app.selectedArticleId = null;
    app.readerOpen = false;
  });

  it('openArticle sets id and opens reader', () => {
    app.openArticle(42);
    expect(app.selectedArticleId).toBe(42);
    expect(app.readerOpen).toBe(true);
  });

  it('closeReader sets readerOpen to false', () => {
    app.openArticle(42);
    app.closeReader();
    expect(app.readerOpen).toBe(false);
  });
});

describe('AppState — data loading', () => {
  it('loadFeeds populates feeds from API', async () => {
    await app.loadFeeds();
    expect(app.feeds).toHaveLength(2);
    expect(app.feeds[0].title).toBe('Feed A');
  });

  it('loadTopics populates topics from API', async () => {
    await app.loadTopics();
    expect(app.topics).toHaveLength(2);
    expect(app.topics[0].name).toBe('Tech');
  });

  it('unreadTotal sums unread_count across all feeds', async () => {
    await app.loadFeeds();
    expect(app.unreadTotal).toBe(8); // 5 + 3
  });

  it('init loads both feeds and topics', async () => {
    await app.init();
    expect(app.feeds.length).toBeGreaterThan(0);
    expect(app.topics.length).toBeGreaterThan(0);
  });
});

describe('AppState — modal state', () => {
  it('addFeedOpen defaults to false', () => {
    expect(app.addFeedOpen).toBe(false);
  });

  it('can toggle addFeedOpen', () => {
    app.addFeedOpen = true;
    expect(app.addFeedOpen).toBe(true);
    app.addFeedOpen = false;
    expect(app.addFeedOpen).toBe(false);
  });
});
