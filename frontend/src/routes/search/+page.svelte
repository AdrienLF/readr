<script>
  import { Search } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import { articles as articlesApi } from '$lib/api.js';
  import ArticleCard from '$lib/components/ArticleCard.svelte';

  app.activeView = 'search';

  let query = $state('');
  let results = $state([]);
  let total = $state(0);
  let page = $state(1);
  let hasMore = $state(false);
  let loading = $state(false);
  let searched = $state(false);

  let debounce;

  function onInput() {
    clearTimeout(debounce);
    if (query.length < 2) {
      results = [];
      searched = false;
      return;
    }
    debounce = setTimeout(() => doSearch(true), 350);
  }

  async function doSearch(reset = false) {
    loading = true;
    if (reset) {
      page = 1;
      results = [];
    }
    try {
      const res = await articlesApi.search(query, page);
      results = reset ? res.items : [...results, ...res.items];
      total = res.total;
      hasMore = res.has_more;
      searched = true;
    } finally {
      loading = false;
    }
  }

  function loadMore() {
    page += 1;
    doSearch();
  }

  function handleUpdate(updated) {
    results = results.map((a) => (a.id === updated.id ? updated : a));
  }
</script>

<svelte:head>
  <title>Search · Readr</title>
</svelte:head>

<div class="flex flex-col h-full">
  <!-- Search bar -->
  <div class="sticky top-0 z-10 bg-zinc-950/90 backdrop-blur border-b border-zinc-800/50 px-4 py-3">
    <div class="relative max-w-xl mx-auto">
      <Search size={16} class="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
      <input
        data-testid="search-input"
        class="input pl-9"
        type="search"
        placeholder="Search articles, titles, content…"
        bind:value={query}
        oninput={onInput}
        autofocus={true}
      />
    </div>
  </div>

  <div class="flex-1 overflow-y-auto">
    {#if !searched && !loading}
      <div class="flex flex-col items-center justify-center h-64 text-zinc-600">
        <Search size={32} class="mb-3 opacity-30" />
        <p>Start typing to search</p>
      </div>
    {:else if loading && results.length === 0}
      <div class="flex items-center justify-center h-40 text-zinc-500">Searching…</div>
    {:else if searched && results.length === 0}
      <div class="flex flex-col items-center justify-center h-64 text-zinc-600">
        <p>No results for "{query}"</p>
      </div>
    {:else}
      <div class="px-4 py-3">
        <p class="text-sm text-zinc-500 mb-4">{total} results for "{query}"</p>
        <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {#each results as article (article.id)}
            <ArticleCard {article} onUpdate={handleUpdate} />
          {/each}
        </div>
        {#if hasMore}
          <div class="flex justify-center mt-6">
            <button onclick={loadMore} class="btn-ghost" disabled={loading}>
              {loading ? 'Loading…' : 'Load more'}
            </button>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>
