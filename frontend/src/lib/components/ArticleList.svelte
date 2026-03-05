<script>
  import { untrack } from 'svelte';
  import { articles as articlesApi } from '$lib/api.js';
  import { app } from '$lib/stores/app.svelte.js';
  import ArticleCard from './ArticleCard.svelte';
  import { RefreshCw, List, Grid2X2, LayoutGrid } from 'lucide-svelte';

  let { topicId = null, feedId = null, bookmarksOnly = false } = $props();

  let items = $state([]);
  let total = $state(0);
  let page = $state(1);
  let loading = $state(false);
  let hasMore = $state(false);

  // Density: 'list' | 'grid' | 'card'
  let density = $state(typeof localStorage !== 'undefined' ? (localStorage.getItem('density') || 'card') : 'card');
  // Local feed filter (overrides feedId prop when set)
  let filterFeedId = $state(null);

  $effect(() => {
    localStorage.setItem('density', density);
  });

  // Effective feed id: local filter takes precedence over prop
  let effectiveFeedId = $derived(filterFeedId ?? feedId);

  // Feeds available for the filter dropdown — respect current topic if set
  let filterableFeeds = $derived(
    topicId !== null ? app.currentTopicFeeds : app.feeds
  );

  async function load(reset = false) {
    if (loading) return;
    loading = true;
    if (reset) { page = 1; items = []; }
    try {
      const params = {
        page, page_size: 50,
        ...(topicId !== null && { topic_id: topicId }),
        ...(effectiveFeedId !== null && { feed_id: effectiveFeedId }),
        ...(bookmarksOnly && { is_bookmarked: true }),
      };
      const res = await articlesApi.list(params);
      items = reset ? res.items : [...items, ...res.items];
      total = res.total;
      hasMore = res.has_more;
    } finally {
      loading = false;
    }
  }

  function loadMore() { page += 1; load(); }

  function handleUpdate(updated) {
    items = items.map((a) => (a.id === updated.id ? updated : a));
    if (bookmarksOnly && !updated.is_bookmarked) items = items.filter((a) => a.id !== updated.id);
  }

  $effect(() => {
    void [topicId, feedId, effectiveFeedId, bookmarksOnly];
    untrack(() => load(true));
  });

  const densityOptions = [
    { value: 'list',  Icon: List,       label: 'List' },
    { value: 'grid',  Icon: Grid2X2,    label: 'Grid' },
    { value: 'card',  Icon: LayoutGrid, label: 'Cards' },
  ];

  const gridClass = $derived(
    density === 'list'
      ? ''
      : density === 'grid'
        ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-3 p-4'
        : 'grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4 p-4'
  );
</script>

<div class="flex flex-col h-full min-h-0" data-testid="article-list">
  <!-- Toolbar -->
  <div class="shrink-0 sticky top-0 z-10 bg-zinc-950/90 backdrop-blur border-b border-zinc-800/50 px-4 py-2.5 flex items-center gap-3">
    <span class="text-sm text-zinc-400 shrink-0">
      {#if loading && items.length === 0}Loading…{:else}{total} articles{/if}
    </span>

    <!-- Feed filter -->
    {#if filterableFeeds.length > 1}
      <select
        class="text-xs bg-zinc-900 border border-zinc-800 text-zinc-300 rounded px-2 py-1 cursor-pointer hover:border-zinc-600 transition-colors focus:outline-none focus:border-violet-500 max-w-[180px] truncate"
        value={filterFeedId ?? ''}
        onchange={(e) => { filterFeedId = e.currentTarget.value ? Number(e.currentTarget.value) : null; }}
      >
        <option value="">All feeds</option>
        {#each filterableFeeds as feed (feed.id)}
          <option value={feed.id}>{feed.title}</option>
        {/each}
      </select>
    {/if}

    <div class="ml-auto flex items-center gap-1">
      <!-- Density toggle -->
      <div class="flex items-center bg-zinc-900 border border-zinc-800 rounded p-0.5 gap-0.5">
        {#each densityOptions as opt}
          {@const Icon = opt.Icon}
          <button
            onclick={() => density = opt.value}
            title={opt.label}
            class="p-1.5 rounded transition-colors {density === opt.value
              ? 'bg-violet-600 text-white'
              : 'text-zinc-500 hover:text-zinc-200'}"
          >
            <Icon size={14} />
          </button>
        {/each}
      </div>

      <button onclick={() => load(true)} class="btn-ghost text-xs ml-1" disabled={loading} title="Refresh">
        <RefreshCw size={14} class={loading ? 'animate-spin' : ''} />
      </button>
    </div>
  </div>

  <!-- List header for compact mode -->
  {#if density === 'list' && items.length > 0}
    <div class="shrink-0 flex items-center gap-3 px-4 py-1.5 border-b border-zinc-800/60 bg-zinc-900/30">
      <div class="w-1.5 shrink-0"></div>
      <span class="text-xs text-zinc-600 w-32 shrink-0">Feed</span>
      <span class="flex-1 text-xs text-zinc-600">Title</span>
      <span class="text-xs text-zinc-600 w-24 shrink-0 text-right hidden sm:block">Date</span>
      <div class="w-6 shrink-0"></div>
    </div>
  {/if}

  <!-- Scrollable content -->
  <div class="flex-1 overflow-y-auto min-h-0">
    {#if items.length === 0 && !loading}
      <div class="flex flex-col items-center justify-center h-64 text-zinc-600">
        <p class="text-lg">No articles yet</p>
        <p class="text-sm mt-1">Add a feed to get started</p>
      </div>
    {:else}
      <div class={gridClass}>
        {#each items as article (article.id)}
          <ArticleCard {article} onUpdate={handleUpdate} {density} />
        {/each}
      </div>
      {#if hasMore}
        <div class="flex justify-center pb-8 pt-2">
          <button onclick={loadMore} class="btn-ghost" disabled={loading}>{loading ? 'Loading…' : 'Load more'}</button>
        </div>
      {/if}
    {/if}
  </div>
</div>
