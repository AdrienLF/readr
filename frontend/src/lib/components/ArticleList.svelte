<script>
  import { untrack } from 'svelte';
  import { articles as articlesApi } from '$lib/api.js';
  import { app } from '$lib/stores/app.svelte.js';
  import ArticleCard from './ArticleCard.svelte';
  import { RefreshCw, AlignJustify, List, Grid2X2, LayoutGrid, TrendingUp } from 'lucide-svelte';

  // Infinite scroll sentinel
  let sentinelEl = $state(null);
  // Keyboard nav focused index
  let focusedIndex = $state(-1);
  let cardEls = $state([]);

  let { topicId = null, feedId = null, bookmarksOnly = false, savedOnly = false } = $props();

  let items = $state([]);
  let total = $state(0);
  let page = $state(1);
  let loading = $state(false);
  let hasMore = $state(false);

  // Density: 'magazine' | 'list' | 'grid' | 'card'
  let density = $state(typeof localStorage !== 'undefined' ? (localStorage.getItem('density') || 'magazine') : 'magazine');
  // Sort: 'date' | 'priority'
  let sort = $state('date');

  $effect(() => { localStorage.setItem('density', density); });

  async function load(reset = false) {
    if (loading) return;
    loading = true;
    if (reset) { page = 1; items = []; }
    try {
      const params = {
        page, page_size: 50,
        sort,
        ...(topicId !== null && { topic_id: topicId }),
        ...(feedId !== null && { feed_id: feedId }),
        ...(bookmarksOnly && { is_bookmarked: true }),
        ...(savedOnly && { is_saved: true }),
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

  // Infinite scroll
  $effect(() => {
    if (!sentinelEl || !hasMore) return;
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) untrack(() => loadMore());
    }, { rootMargin: '300px' });
    observer.observe(sentinelEl);
    return () => observer.disconnect();
  });

  // Keyboard navigation
  function handleKeydown(e) {
    const tag = e.target?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target?.isContentEditable) return;
    if (app.activeView !== 'feed' && !bookmarksOnly && !savedOnly) return;

    const flat = grouped ? grouped.flatMap((g) => g.items) : items;

    switch (e.key) {
      case 'j': {
        e.preventDefault();
        focusedIndex = Math.min(focusedIndex + 1, flat.length - 1);
        cardEls[focusedIndex]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        break;
      }
      case 'k': {
        e.preventDefault();
        focusedIndex = Math.max(focusedIndex - 1, 0);
        cardEls[focusedIndex]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        break;
      }
      case 'o':
      case 'Enter': {
        const a = flat[focusedIndex];
        if (a) { app.openArticle(a.id); markRead(a); }
        break;
      }
      case 'b': {
        const a = flat[focusedIndex];
        if (a) articlesApi.toggleBookmark(a.id).then((u) => handleUpdate({ ...a, is_bookmarked: u.is_bookmarked }));
        break;
      }
      case 'u': {
        const a = flat[focusedIndex];
        if (a) {
          const next = !a.is_read;
          articlesApi.markRead(a.id, next);
          handleUpdate({ ...a, is_read: next });
        }
        break;
      }
      case 'r': {
        if (!e.ctrlKey && !e.metaKey) { e.preventDefault(); untrack(() => load(true)); }
        break;
      }
    }
  }

  function markRead(article) {
    if (!article.is_read) {
      articlesApi.markRead(article.id);
      handleUpdate({ ...article, is_read: true });
    }
  }

  // Reset focus and reload when sort changes
  $effect(() => {
    void sort;
    untrack(() => load(true));
  });

  // Reset focus when content changes
  $effect(() => {
    void [topicId, feedId, bookmarksOnly, savedOnly];
    focusedIndex = -1;
  });

  function handleUpdate(updated) {
    items = items.map((a) => (a.id === updated.id ? updated : a));
    if (bookmarksOnly && !updated.is_bookmarked) items = items.filter((a) => a.id !== updated.id);
    if (savedOnly && !updated.is_saved) items = items.filter((a) => a.id !== updated.id);
  }

  $effect(() => {
    void [topicId, feedId, bookmarksOnly, savedOnly];
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
          : savedOnly
            ? 'Saved for Later'
            : 'All Articles'
  );
</script>

<svelte:window onkeydown={handleKeydown} />

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

      <div class="ml-auto flex items-center gap-2">
        <button
          onclick={() => { sort = sort === 'date' ? 'priority' : 'date'; }}
          title={sort === 'priority' ? 'Sorted by priority — click for latest' : 'Sorted by date — click for priority'}
          class="btn-ghost text-xs gap-1.5 {sort === 'priority' ? 'text-violet-400' : ''}"
        >
          <TrendingUp size={13} />
          <span class="hidden sm:inline">{sort === 'priority' ? 'Priority' : 'Latest'}</span>
        </button>
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
  <div data-testid="article-list-scroll" class="flex-1 overflow-y-auto min-h-0">
    {#if items.length === 0 && !loading}
      <div class="flex flex-col items-center justify-center h-64 text-zinc-600">
        <p class="text-lg">No articles yet</p>
        <p class="text-sm mt-1">Add a feed to get started</p>
      </div>
    {:else if grouped}
      <!-- Grouped layout (magazine / list) -->
      <div class="px-5 pb-4">
        {#each grouped as group}
          <h2 class="text-xs font-semibold text-zinc-500 uppercase tracking-widest mt-6 mb-3 first:mt-4">
            {group.label}
          </h2>
          {#each group.items as article, gi (article.id)}
            {@const flatIndex = grouped.slice(0, grouped.indexOf(group)).reduce((s, g) => s + g.items.length, 0) + gi}
            <div bind:this={cardEls[flatIndex]}>
              <ArticleCard
                {article}
                onUpdate={handleUpdate}
                {density}
                focused={focusedIndex === flatIndex}
              />
            </div>
          {/each}
        {/each}
        <!-- Infinite scroll sentinel -->
        {#if hasMore}
          <div bind:this={sentinelEl} class="h-8 flex items-center justify-center">
            {#if loading}<span class="text-xs text-zinc-600">Loading…</span>{/if}
          </div>
        {/if}
      </div>
    {:else}
      <!-- Grid / card layout -->
      <div class={gridClass}>
        {#each items as article, i (article.id)}
          <div bind:this={cardEls[i]} class="h-full">
            <ArticleCard
              {article}
              onUpdate={handleUpdate}
              {density}
              focused={focusedIndex === i}
              onMarkRead={() => markRead(article)}
            />
          </div>
        {/each}
      </div>
      <!-- Infinite scroll sentinel -->
      {#if hasMore}
        <div bind:this={sentinelEl} class="h-12 flex items-center justify-center pb-4">
          {#if loading}<span class="text-xs text-zinc-600">Loading…</span>{/if}
        </div>
      {/if}
    {/if}
  </div>
</div>
