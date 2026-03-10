import { goto } from '$app/navigation';
import { feeds as feedsApi, topics as topicsApi, savedSearches as savedSearchesApi } from '$lib/api.js';

class AppState {
  // Navigation
  selectedTopicId = $state(null);
  selectedFeedId = $state(null);
  activeView = $state('feed'); // feed | bookmarks | saved | search | digest | settings | smart-search

  // Bump to trigger article list refresh (e.g. after feed fetch completes)
  refreshToken = $state(0);

  // Article reader
  selectedArticleId = $state(null);
  readerOpen = $state(false);
  articleIds = $state([]);

  // UI
  sidebarOpen = $state(true);
  addFeedOpen = $state(false);
  bulkAddOpen = $state(false);
  addTopicOpen = $state(false);
  addSmartSearchOpen = $state(false);
  shortcutsVisible = $state(false);

  // Data
  feeds = $state([]);
  topics = $state([]);
  savedSearches = $state([]);
  selectedSmartSearchId = $state(null);

  get unreadTotal() {
    return this.feeds.reduce((sum, f) => sum + (f.unread_count || 0), 0);
  }

  get currentTopicFeeds() {
    if (this.selectedTopicId === null) return this.feeds;
    return this.feeds.filter((f) => f.topics?.some((t) => t.id === this.selectedTopicId));
  }

  feedsForTopic(topicId) {
    return this.feeds.filter((f) => f.topics?.some((t) => t.id === topicId));
  }

  get uncategorizedFeeds() {
    return this.feeds.filter((f) => !f.topics || f.topics.length === 0);
  }

  openArticle(id) {
    this.selectedArticleId = id;
    this.readerOpen = true;
  }

  openNextArticle() {
    const idx = this.articleIds.indexOf(this.selectedArticleId);
    if (idx !== -1 && idx < this.articleIds.length - 1) {
      this.selectedArticleId = this.articleIds[idx + 1];
    }
  }

  openPrevArticle() {
    const idx = this.articleIds.indexOf(this.selectedArticleId);
    if (idx > 0) {
      this.selectedArticleId = this.articleIds[idx - 1];
    }
  }

  closeReader() {
    this.readerOpen = false;
    setTimeout(() => { this.selectedArticleId = null; }, 250);
  }

  /** Navigate to the main page if we're on a sub-route (search, digest, settings…) */
  _ensureHome() {
    if (typeof window !== 'undefined' && window.location.pathname !== '/') {
      goto('/');
    }
  }

  selectAll() {
    this.selectedTopicId = null;
    this.selectedFeedId = null;
    this.activeView = 'feed';
    this.closeReader();
    this._ensureHome();
    if (window.innerWidth < 768) this.sidebarOpen = false;
  }

  selectTopic(id) {
    this.selectedTopicId = id;
    this.selectedFeedId = null;
    this.activeView = 'feed';
    this.closeReader();
    this._ensureHome();
    if (window.innerWidth < 768) this.sidebarOpen = false;
  }

  selectFeed(id) {
    this.selectedFeedId = id;
    this.selectedTopicId = null;
    this.activeView = 'feed';
    this.closeReader();
    this._ensureHome();
    if (window.innerWidth < 768) this.sidebarOpen = false;
  }

  selectSmartSearch(id) {
    this.selectedSmartSearchId = id;
    this.selectedFeedId = null;
    this.selectedTopicId = null;
    this.activeView = 'smart-search';
    this.closeReader();
    this._ensureHome();
    if (window.innerWidth < 768) this.sidebarOpen = false;
  }

  /** Call after feed refresh completes to reload the article list */
  triggerArticleRefresh() {
    this.refreshToken++;
  }

  async loadFeeds() {
    try {
      this.feeds = await feedsApi.list();
    } catch (e) {
      console.error('Failed to load feeds:', e);
    }
  }

  async loadTopics() {
    try {
      this.topics = await topicsApi.list();
    } catch (e) {
      console.error('Failed to load topics:', e);
    }
  }

  async loadSavedSearches() {
    try {
      this.savedSearches = await savedSearchesApi.list();
    } catch (e) {
      console.error('Failed to load saved searches:', e);
    }
  }

  async init() {
    await Promise.all([this.loadFeeds(), this.loadTopics(), this.loadSavedSearches()]);
  }
}

export const app = new AppState();
