<script>
  import { untrack } from 'svelte';
  import { articles as articlesApi } from '$lib/api.js';
  import { app } from '$lib/stores/app.svelte.js';
  import ArticleCard from './ArticleCard.svelte';
  import { RefreshCw, AlignJustify, List, Grid2X2, LayoutGrid } from 'lucide-svelte';

  let { topicId = null, feedId = null, bookmarksOnly = false } = $props();

  let items = $state([]);
  let total = $state(0);
  let page = $state(1);
  let loading = $state(false);
  let hasMore = $state(false);

  // Density: 'magazine' | 'list' | 'grid' | 'card'
  let density = $state(typeof localStorage !== 'undefined' ? (localStorage.getItem('density') || 'magazine') : 'magazine');

  $effect(() => { localStorage.setItem('density', density); });

  async function load(reset = false) {
    if (loading) return;
    loading = true;
    if (reset) { page = 1; items = []; }
    try {
      const params = {
        page, page_size: 50,
        ...(topicId !== null && { topic_id: topicId }),
        ...(feedId !== null && { feed_id: feedId }),
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
    void [topicId, feedId, bookmarksOnly];
    untrack(() => load(true));
  });

  const densityOptions = [
    { value: 'magazine', Icon: AlignJustify, label: 'Magazine' },
    { value: 'list',     Icon: List,         label: 'List' },
    { value: 'grid',     Icon: Grid2X2,      label: 'Grid' },
    { value: 'card',     Icon: LayoutGrid,   label: 'Cards' },
  ];

  const gridClass = $derived(
    density === 'magazine' || density === 'list'
      ? ''
      : density === 'grid'
        ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-3 p-4'
        : 'grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4 p-4'
  );

  // Date grouping for magazine/list mode
  function groupArticles(articles) {
    const now = new Date();
    const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
    const today     = startOfDay(now);
    const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
    const weekAgo   = new Date(today); weekAgo.setDate(today.getDate() - 7);
    const monthAgo  = new Date(today); monthAgo.setDate(today.getDate() - 30);

    const buckets = [
      { label: 'Today',      items: [] },
      { label: 'Yesterday',  items: [] },
      { label: 'This week',  items: [] },
      { label: 'This month', items: [] },
      { label: 'Older',      items: [] },
    ];

    for (const a of articles) {
      const d = a.published_at ? new Date(a.published_at) : new Date(0);
      if (d >= today)     buckets[0].items.push(a);
      else if (d >= yesterday) buckets[1].items.push(a);
      else if (d >= weekAgo)   buckets[2].items.push(a);
      else if (d >= monthAgo)  buckets[3].items.push(a);
      else                     buckets[4].items.push(a);
    }

    return buckets.filter((b) => b.items.length > 0);
  }

  let grouped = $derived(
    (density === 'magazine' || density === 'list') ? groupArticles(items) : null
  );

  // Context label for the page header
  let contextLabel = $derived(
    feedId
      ? (app.feeds.find((f) => f.id === feedId)?.title ?? 'Feed')
      : topicId
        ? (app.topics.find((t) => t.id === topicId)?.name ?? 'Topic')
        : bookmarksOnly
          ? 'Bookmarks'
          : 'All Articles'
  );
</script>

<div class="flex flex-col h-full min-h-0" data-testid="article-list">
  <!-- Toolbar -->
  <div class="shrink-0 bg-zinc-950/90 backdrop-blur border-b border-zinc-800/50 px-5 py-3">
    <!-- Context heading -->
    <div class="flex items-end justify-between mb-2">
      <h1 class="text-xl font-bold text-zinc-100 truncate">{contextLabel}</h1>
      <span class="text-xs text-zinc-600 shrink-0 ml-3 mb-0.5">
        {#if loading && items.length === 0}Loading…{:else}{total} articles{/if}
      </span>
    </div>

    <!-- Controls row -->
    <div class="flex items-center gap-2">
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
            <Icon size={13} />
          </button>
        {/each}
      </div>

      <div class="ml-auto">
        <button onclick={() => load(true)} class="btn-ghost text-xs" disabled={loading} title="Refresh">
          <RefreshCw size={13} class={loading ? 'animate-spin' : ''} />
          <span class="hidden sm:inline">Refresh</span>
        </button>
      </div>
    </div>
  </div>

  <!-- List header for compact mode -->
  {#if density === 'list' && items.length > 0}
    <div class="shrink-0 flex items-center gap-3 px-5 py-1.5 border-b border-zinc-800/60 bg-zinc-900/30">
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
    {:else if grouped}
      <!-- Grouped layout (magazine / list) -->
      <div class="px-5 pb-8">
        {#each grouped as group}
          <h2 class="text-xs font-semibold text-zinc-500 uppercase tracking-widest mt-6 mb-3 first:mt-4">
            {group.label}
          </h2>
          {#each group.items as article (article.id)}
            <ArticleCard {article} onUpdate={handleUpdate} {density} />
          {/each}
        {/each}
        {#if hasMore}
          <div class="flex justify-center pt-6">
            <button onclick={loadMore} class="btn-ghost" disabled={loading}>{loading ? 'Loading…' : 'Load more'}</button>
          </div>
        {/if}
      </div>
    {:else}
      <!-- Grid / card layout -->
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
