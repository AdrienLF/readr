import { feeds as feedsApi, topics as topicsApi } from '$lib/api.js';

class AppState {
  // Navigation
  selectedTopicId = $state(null); // null = all
  activeView = $state('feed'); // feed | bookmarks | search | digest | settings

  // Article reader
  selectedArticleId = $state(null);
  readerOpen = $state(false);

  // UI
  sidebarOpen = $state(true);
  addFeedOpen = $state(false);
  addTopicOpen = $state(false);

  // Data
  feeds = $state([]);
  topics = $state([]);

  // Derived
  get unreadTotal() {
    return this.feeds.reduce((sum, f) => sum + (f.unread_count || 0), 0);
  }

  get currentTopicFeeds() {
    if (this.selectedTopicId === null) return this.feeds;
    const topic = this.topics.find((t) => t.id === this.selectedTopicId);
    if (!topic) return [];
    return this.feeds.filter((f) => f.topics?.some((t) => t.id === this.selectedTopicId));
  }

  openArticle(id) {
    this.selectedArticleId = id;
    this.readerOpen = true;
  }

  closeReader() {
    this.readerOpen = false;
    setTimeout(() => {
      this.selectedArticleId = null;
    }, 250);
  }

  selectTopic(id) {
    this.selectedTopicId = id;
    this.activeView = 'feed';
    this.closeReader();
    if (window.innerWidth < 768) {
      this.sidebarOpen = false;
    }
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

  async init() {
    await Promise.all([this.loadFeeds(), this.loadTopics()]);
  }
}

export const app = new AppState();
