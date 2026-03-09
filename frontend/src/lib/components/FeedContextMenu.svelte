<script>
  import { Check, FolderInput, X, Loader2 } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import { feeds as feedsApi } from '$lib/api.js';

  let { feed = $bindable(null), x = 0, y = 0 } = $props();

  let menuEl = $state(null);
  let busy = $state(false);

  // Keep feed in sync with store after reloads
  let liveFeed = $derived(feed ? app.feeds.find((f) => f.id === feed.id) ?? feed : null);

  function close() {
    feed = null;
  }

  function handleClickOutside(e) {
    if (menuEl && !menuEl.contains(e.target)) close();
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') close();
  }

  async function toggleTopic(topicId) {
    if (busy) return;
    busy = true;
    try {
      const current = liveFeed.topics?.map((t) => t.id) ?? [];
      const next = current.includes(topicId)
        ? current.filter((id) => id !== topicId)
        : [...current, topicId];
      await feedsApi.update(liveFeed.id, { topic_ids: next });
      await Promise.all([app.loadFeeds(), app.loadTopics()]);
    } finally {
      busy = false;
    }
  }

  async function removeAllTopics() {
    if (busy) return;
    busy = true;
    try {
      await feedsApi.update(liveFeed.id, { topic_ids: [] });
      await Promise.all([app.loadFeeds(), app.loadTopics()]);
    } finally {
      busy = false;
    }
  }

  // Clamp menu position to viewport
  let style = $derived.by(() => {
    if (!feed) return '';
    const maxX = typeof window !== 'undefined' ? window.innerWidth - 220 : x;
    const maxY = typeof window !== 'undefined' ? window.innerHeight - 300 : y;
    return `left: ${Math.min(x, maxX)}px; top: ${Math.min(y, maxY)}px;`;
  });
</script>

<svelte:window onclick={handleClickOutside} onkeydown={handleKeydown} />

{#if feed}
  <div
    bind:this={menuEl}
    class="fixed z-50 w-52 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl py-1 text-sm"
    style={style}
  >
    <div class="px-3 py-1.5 text-[11px] text-zinc-500 uppercase tracking-wider font-semibold flex items-center gap-1.5">
      <FolderInput size={11} /> Move to topic
      {#if busy}
        <Loader2 size={10} class="animate-spin ml-auto" />
      {/if}
    </div>

    <div class="max-h-60 overflow-y-auto">
      {#each app.topics as topic (topic.id)}
        {@const isAssigned = liveFeed?.topics?.some((t) => t.id === topic.id)}
        <button
          onclick={() => toggleTopic(topic.id)}
          disabled={busy}
          class="w-full flex items-center gap-2 px-3 py-1.5 text-left text-[13px] transition-colors
                 hover:bg-zinc-800 {isAssigned ? 'text-zinc-200' : 'text-zinc-400'}
                 {busy ? 'opacity-50 cursor-wait' : ''}"
        >
          <span class="w-2 h-2 rounded-full shrink-0" style="background-color: {topic.color}"></span>
          <span class="flex-1 truncate">{topic.name}</span>
          {#if isAssigned}
            <Check size={13} class="text-violet-400 shrink-0" />
          {/if}
        </button>
      {/each}
    </div>

    {#if liveFeed?.topics?.length > 0}
      <div class="border-t border-zinc-800 mt-1 pt-1">
        <button
          onclick={removeAllTopics}
          disabled={busy}
          class="w-full flex items-center gap-2 px-3 py-1.5 text-left text-[13px] text-zinc-500 hover:text-red-400 hover:bg-zinc-800 transition-colors
                 {busy ? 'opacity-50 cursor-wait' : ''}"
        >
          <X size={13} class="shrink-0" />
          <span>Remove from all topics</span>
        </button>
      </div>
    {/if}

    {#if app.topics.length === 0}
      <p class="px-3 py-2 text-xs text-zinc-600 italic">No topics yet</p>
    {/if}
  </div>
{/if}
