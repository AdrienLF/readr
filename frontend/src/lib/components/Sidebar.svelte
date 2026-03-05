<script>
  import { Home, Bookmark, Search, Zap, Settings, Plus, Rss, RefreshCw, ChevronRight, BookOpen } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import { feeds as feedsApi } from '$lib/api.js';

  let refreshing = $state(false);
  // Set of topic IDs that are expanded in the sidebar
  let expanded = $state(new Set());

  function toggleExpanded(topicId, e) {
    e.stopPropagation();
    expanded = new Set(expanded); // trigger reactivity
    if (expanded.has(topicId)) expanded.delete(topicId);
    else expanded.add(topicId);
  }

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
    { id: 'bookmarks', label: 'Bookmarks', icon: Bookmark, path: '/bookmarks' },
    { id: 'search',    label: 'Search',    icon: Search,   path: '/search' },
    { id: 'digest',    label: 'Digest',    icon: Zap,      path: '/digest' },
    { id: 'settings',  label: 'Settings',  icon: Settings, path: '/settings' },
    { id: 'docs',      label: 'Docs',      icon: BookOpen, path: '/docs' },
  ];

  function unreadForTopic(topicId) {
    return app.feedsForTopic(topicId).reduce((s, f) => s + (f.unread_count || 0), 0);
  }

  const healthColor = {
    ok:    '',
    never: 'bg-zinc-600',
    stale: 'bg-amber-500',
    error: 'bg-red-500',
  };
</script>

<aside
  data-testid="sidebar"
  class="flex flex-col w-60 shrink-0 bg-zinc-900 border-r border-zinc-800 h-full
         transition-transform duration-250
         {app.sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
         fixed md:relative z-20 md:z-auto"
>
  <!-- Logo -->
  <div class="px-4 py-4 border-b border-zinc-800 shrink-0">
    <div class="flex items-center gap-2">
      <Rss size={16} class="text-violet-400" />
      <span class="font-bold text-sm tracking-tight">Readr</span>
    </div>
  </div>

  <!-- Scrollable nav body -->
  <div class="flex-1 overflow-y-auto min-h-0 py-2">

    <!-- All Articles -->
    <a
      href="/"
      onclick={() => app.selectAll()}
      class="flex items-center gap-2.5 px-3 py-2 mx-2 rounded-lg text-sm transition-colors
             {app.activeView === 'feed' && !app.selectedTopicId && !app.selectedFeedId
               ? 'bg-violet-500/15 text-violet-300'
               : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800'}"
    >
      <Home size={15} />
      <span class="flex-1">All Articles</span>
      {#if app.unreadTotal > 0}
        <span class="text-xs font-semibold text-zinc-500 tabular-nums">
          {app.unreadTotal > 9999 ? '9999+' : app.unreadTotal}
        </span>
      {/if}
    </a>

    <!-- Other nav -->
    {#each NAV as item (item.id)}
      {@const Icon = item.icon}
      <a
        href={item.path}
        onclick={() => (app.activeView = item.id)}
        class="flex items-center gap-2.5 px-3 py-2 mx-2 rounded-lg text-sm transition-colors
               {app.activeView === item.id
                 ? 'bg-violet-500/15 text-violet-300'
                 : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800'}"
      >
        <Icon size={15} />
        {item.label}
      </a>
    {/each}

    <!-- Divider + Topics header -->
    <div class="mx-3 mt-4 mb-1 flex items-center justify-between">
      <span class="text-[11px] font-semibold text-zinc-600 uppercase tracking-wider">Topics</span>
      <button
        data-testid="add-topic-btn"
        onclick={() => (app.addTopicOpen = true)}
        class="text-zinc-600 hover:text-zinc-400 transition-colors p-0.5 rounded"
        aria-label="Add topic"
      >
        <Plus size={11} />
      </button>
    </div>

    {#each app.topics as topic (topic.id)}
      {@const topicFeeds = app.feedsForTopic(topic.id)}
      {@const isExpanded = expanded.has(topic.id)}
      {@const topicUnread = unreadForTopic(topic.id)}

      <!-- Topic row -->
      <div class="mx-2">
        <button
          onclick={() => app.selectTopic(topic.id)}
          class="group w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm transition-colors
                 {app.selectedTopicId === topic.id && !app.selectedFeedId
                   ? 'bg-zinc-800 text-zinc-100'
                   : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50'}"
        >
          <!-- Expand chevron -->
          {#if topicFeeds.length > 0}
            <button
              onclick={(e) => toggleExpanded(topic.id, e)}
              class="p-0.5 rounded hover:bg-zinc-700 transition-colors shrink-0 text-zinc-600 hover:text-zinc-300"
              tabindex="-1"
              aria-label={isExpanded ? 'Collapse' : 'Expand'}
            >
              <ChevronRight size={13} class="transition-transform duration-150 {isExpanded ? 'rotate-90' : ''}" />
            </button>
          {:else}
            <span class="w-5 shrink-0"></span>
          {/if}

          <span class="w-2 h-2 rounded-full shrink-0" style="background-color: {topic.color}"></span>
          <span class="flex-1 truncate text-left text-[13px]">{topic.name}</span>
          {#if topicUnread > 0}
            <span class="text-xs text-zinc-500 tabular-nums shrink-0">{topicUnread > 9999 ? '9999+' : topicUnread}</span>
          {/if}
        </button>

        <!-- Feed rows under topic -->
        {#if isExpanded && topicFeeds.length > 0}
          <div class="ml-4 border-l border-zinc-800 pl-1 mt-0.5 mb-1">
            {#each topicFeeds as feed (feed.id)}
              <button
                onclick={() => app.selectFeed(feed.id)}
                title={feed.last_error || undefined}
                class="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-[12px] transition-colors
                       {app.selectedFeedId === feed.id
                         ? 'bg-violet-600/15 text-violet-300'
                         : 'text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/60'}"
              >
                {#if feed.favicon_url}
                  <img
                    src={feed.favicon_url}
                    alt=""
                    class="w-3.5 h-3.5 rounded-sm shrink-0 object-contain"
                    onerror={(e) => e.currentTarget.style.display = 'none'}
                  />
                {:else}
                  <Rss size={11} class="shrink-0 text-zinc-700" />
                {/if}
                <span class="flex-1 truncate text-left">{feed.title}</span>
                {#if feed.health && feed.health !== 'ok'}
                  <span class="w-1.5 h-1.5 rounded-full shrink-0 {healthColor[feed.health]}" title={feed.last_error || feed.health}></span>
                {:else if feed.unread_count > 0}
                  <span class="text-[11px] text-zinc-500 tabular-nums shrink-0">{feed.unread_count}</span>
                {/if}
              </button>
            {/each}
          </div>
        {/if}
      </div>
    {/each}

    {#if app.topics.length === 0}
      <p class="px-4 py-2 text-xs text-zinc-600 italic">No topics yet</p>
    {/if}

    <!-- Uncategorized feeds -->
    {#if app.uncategorizedFeeds.length > 0}
      <div class="mx-3 mt-4 mb-1">
        <span class="text-[11px] font-semibold text-zinc-600 uppercase tracking-wider">Feeds</span>
      </div>
      <div class="mx-2">
        {#each app.uncategorizedFeeds as feed (feed.id)}
          <button
            onclick={() => app.selectFeed(feed.id)}
            title={feed.last_error || undefined}
            class="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-[13px] transition-colors
                   {app.selectedFeedId === feed.id
                     ? 'bg-violet-600/15 text-violet-300'
                     : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'}"
          >
            {#if feed.favicon_url}
              <img
                src={feed.favicon_url}
                alt=""
                class="w-3.5 h-3.5 rounded-sm shrink-0 object-contain"
                onerror={(e) => e.currentTarget.style.display = 'none'}
              />
            {:else}
              <Rss size={12} class="shrink-0 text-zinc-700" />
            {/if}
            <span class="flex-1 truncate text-left">{feed.title}</span>
            {#if feed.health && feed.health !== 'ok'}
              <span class="w-1.5 h-1.5 rounded-full shrink-0 {healthColor[feed.health]}"></span>
            {:else if feed.unread_count > 0}
              <span class="text-[11px] text-zinc-500 tabular-nums shrink-0">{feed.unread_count}</span>
            {/if}
          </button>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Footer -->
  <div class="px-2 py-3 border-t border-zinc-800 shrink-0 flex items-center gap-2">
    <button
      data-testid="add-feed-btn"
      onclick={() => (app.addFeedOpen = true)}
      class="btn-primary flex-1 justify-center text-xs py-1.5"
    >
      <Plus size={13} /> Add Feed
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
