<script>
  import { ChevronDown, Search, X, Rss } from 'lucide-svelte';

  let { feeds = [], value = null, onchange } = $props();

  let open = $state(false);
  let query = $state('');
  let searchEl = $state(null);
  let panelEl = $state(null);
  let anchorEl = $state(null);

  const selected = $derived(value !== null ? feeds.find((f) => f.id === value) : null);

  const filtered = $derived(
    query.trim()
      ? feeds.filter((f) => f.title.toLowerCase().includes(query.trim().toLowerCase()))
      : feeds
  );

  function toggle() {
    open = !open;
    if (open) {
      query = '';
      // Focus search on next tick
      setTimeout(() => searchEl?.focus(), 0);
    }
  }

  function select(id) {
    onchange?.(id);
    open = false;
    query = '';
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') { open = false; query = ''; }
  }

  function handleOutside(e) {
    if (!panelEl?.contains(e.target) && !anchorEl?.contains(e.target)) {
      open = false;
      query = '';
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} onmousedown={handleOutside} />

<div class="relative">
  <!-- Trigger button -->
  <button
    bind:this={anchorEl}
    onclick={toggle}
    class="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded border transition-colors
           {open
             ? 'bg-zinc-800 border-violet-500 text-zinc-200'
             : value !== null
               ? 'bg-violet-950/60 border-violet-700/60 text-violet-300'
               : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200'}"
  >
    <Rss size={12} class="shrink-0" />
    <span class="max-w-[140px] truncate">
      {selected ? selected.title : 'All feeds'}
    </span>
    {#if value !== null}
      <button
        onclick={(e) => { e.stopPropagation(); select(null); }}
        class="ml-0.5 text-violet-400 hover:text-white transition-colors"
        aria-label="Clear feed filter"
      >
        <X size={11} />
      </button>
    {:else}
      <ChevronDown size={12} class="shrink-0 transition-transform {open ? 'rotate-180' : ''}" />
    {/if}
  </button>

  <!-- Popover panel -->
  {#if open}
    <div
      bind:this={panelEl}
      class="absolute left-0 top-full mt-1.5 w-72 z-50
             bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl shadow-black/60
             flex flex-col overflow-hidden"
      style="max-height: min(420px, 60vh)"
    >
      <!-- Search -->
      <div class="p-2 border-b border-zinc-800 shrink-0">
        <div class="relative">
          <Search size={13} class="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none" />
          <input
            bind:this={searchEl}
            bind:value={query}
            type="text"
            placeholder="Search feeds…"
            class="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 pl-7
                   text-xs text-zinc-200 placeholder-zinc-600
                   focus:outline-none focus:border-violet-500 transition-colors"
          />
          {#if query}
            <button
              onclick={() => query = ''}
              class="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
            >
              <X size={12} />
            </button>
          {/if}
        </div>
      </div>

      <!-- Feed list -->
      <div class="overflow-y-auto flex-1">
        <!-- All feeds option -->
        <button
          onclick={() => select(null)}
          class="w-full flex items-center gap-2.5 px-3 py-2 text-xs transition-colors text-left
                 {value === null
                   ? 'bg-violet-600/20 text-violet-300'
                   : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200'}"
        >
          <span class="w-4 h-4 rounded-sm bg-zinc-700 flex items-center justify-center shrink-0">
            <Rss size={9} />
          </span>
          <span class="flex-1 font-medium">All feeds</span>
          <span class="text-zinc-600 tabular-nums">{feeds.length}</span>
        </button>

        {#if filtered.length === 0}
          <p class="px-3 py-4 text-xs text-zinc-600 text-center">No feeds match "{query}"</p>
        {:else}
          {#each filtered as feed (feed.id)}
            <button
              onclick={() => select(feed.id)}
              class="w-full flex items-center gap-2.5 px-3 py-2 text-xs transition-colors text-left
                     {value === feed.id
                       ? 'bg-violet-600/20 text-violet-300'
                       : 'text-zinc-300 hover:bg-zinc-800'}"
            >
              {#if feed.favicon_url}
                <img
                  src={feed.favicon_url}
                  alt=""
                  class="w-4 h-4 rounded-sm shrink-0 object-contain bg-zinc-800"
                  onerror={(e) => e.currentTarget.style.display = 'none'}
                />
              {:else}
                <span class="w-4 h-4 rounded-sm bg-zinc-800 shrink-0"></span>
              {/if}
              <span class="flex-1 truncate">{feed.title}</span>
              {#if feed.unread_count > 0}
                <span class="shrink-0 text-[10px] font-semibold text-violet-400 tabular-nums">
                  {feed.unread_count}
                </span>
              {/if}
            </button>
          {/each}
        {/if}
      </div>
    </div>
  {/if}
</div>
