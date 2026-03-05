<script>
  import { Home, Bookmark, Search, Zap, Settings, Plus, Rss, RefreshCw } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import { feeds as feedsApi } from '$lib/api.js';

  let refreshing = $state(false);

  async function refreshAll() {
    refreshing = true;
    try {
      await feedsApi.refreshAll();
      setTimeout(() => app.loadFeeds(), 2000);
    } finally {
      setTimeout(() => (refreshing = false), 2000);
    }
  }

  const NAV = [
    { id: 'feed', label: 'All Articles', icon: Home, path: '/' },
    { id: 'bookmarks', label: 'Bookmarks', icon: Bookmark, path: '/bookmarks' },
    { id: 'search', label: 'Search', icon: Search, path: '/search' },
    { id: 'digest', label: 'Digest', icon: Zap, path: '/digest' },
    { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
  ];
</script>

<aside
  data-testid="sidebar"
  class="flex flex-col w-64 shrink-0 bg-zinc-900 border-r border-zinc-800 h-full overflow-y-auto
         transition-transform duration-250
         {app.sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
         fixed md:relative z-20 md:z-auto"
>
  <div class="px-4 py-5 border-b border-zinc-800">
    <div class="flex items-center gap-2">
      <Rss size={18} class="text-violet-400" />
      <span class="font-bold text-sm tracking-tight">Readr</span>
    </div>
  </div>

  <nav class="px-2 py-3">
    {#each NAV as item (item.id)}
      {@const Icon = item.icon}
      <a
        href={item.path}
        onclick={() => (app.activeView = item.id)}
        class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors
               {app.activeView === item.id
                 ? 'bg-violet-500/15 text-violet-300'
                 : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800'}"
      >
        <Icon size={16} />
        {item.label}
        {#if item.id === 'feed' && app.unreadTotal > 0}
          <span class="ml-auto bg-violet-600 text-white text-xs px-1.5 py-0.5 rounded-full">
            {app.unreadTotal > 99 ? '99+' : app.unreadTotal}
          </span>
        {/if}
      </a>
    {/each}
  </nav>

  <div class="border-t border-zinc-800 mx-2 my-1"></div>

  <div class="px-2 py-2 flex-1">
    <div class="flex items-center justify-between px-3 mb-1">
      <span class="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Topics</span>
      <button
        data-testid="add-topic-btn"
        onclick={() => (app.addTopicOpen = true)}
        class="text-zinc-600 hover:text-zinc-400 transition-colors p-0.5 rounded"
        aria-label="Add topic"
      >
        <Plus size={12} />
      </button>
    </div>

    {#each app.topics as topic (topic.id)}
      <button
        onclick={() => app.selectTopic(topic.id)}
        class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors
               {app.selectedTopicId === topic.id
                 ? 'bg-zinc-800 text-zinc-100'
                 : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50'}"
      >
        <span
          class="w-2.5 h-2.5 rounded-full shrink-0"
          style="background-color: {topic.color}"
        ></span>
        <span class="truncate">{topic.name}</span>
        <span class="ml-auto text-xs text-zinc-600">{topic.feed_count}</span>
      </button>
    {/each}

    {#if app.topics.length === 0}
      <p class="px-3 py-2 text-xs text-zinc-600 italic">No topics yet</p>
    {/if}
  </div>

  <div class="px-2 py-3 border-t border-zinc-800 flex items-center gap-2">
    <button
      data-testid="add-feed-btn"
      onclick={() => (app.addFeedOpen = true)}
      class="btn-primary flex-1 justify-center text-xs py-1.5"
    >
      <Plus size={14} /> Add Feed
    </button>
    <button
      onclick={refreshAll}
      class="btn-ghost p-2"
      disabled={refreshing}
      aria-label="Refresh all feeds"
    >
      <RefreshCw size={14} class={refreshing ? 'animate-spin' : ''} />
    </button>
  </div>
</aside>
