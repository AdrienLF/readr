<script>
  import { X, Rss, Plus } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import { feeds as feedsApi } from '$lib/api.js';

  let url = $state('');
  let selectedTopics = $state([]);
  let loading = $state(false);
  let error = $state('');

  function toggleTopic(id) {
    if (selectedTopics.includes(id)) {
      selectedTopics = selectedTopics.filter((t) => t !== id);
    } else {
      selectedTopics = [...selectedTopics, id];
    }
  }

  async function submit() {
    if (!url.trim()) return;
    loading = true;
    error = '';
    try {
      await feedsApi.add(url.trim(), selectedTopics);
      await app.loadFeeds();
      close();
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  function close() {
    app.addFeedOpen = false;
    url = '';
    selectedTopics = [];
    error = '';
  }

  function handleKey(e) {
    if (e.key === 'Escape') close();
  }
</script>

<svelte:window onkeydown={handleKey} />

{#if app.addFeedOpen}
  <div
    class="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 animate-fade-in"
    onclick={(e) => e.target === e.currentTarget && close()}
    onkeydown={(e) => e.key === 'Escape' && close()}
    role="dialog"
    tabindex="-1"
    aria-modal="true"
    aria-label="Add feed"
  >
    <div class="card w-full max-w-md p-6 animate-slide-in-up">
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-2">
          <Rss size={18} class="text-violet-400" />
          <h2 class="text-base font-semibold">Add Feed</h2>
        </div>
        <button onclick={close} class="btn-ghost p-1"><X size={16} /></button>
      </div>

      <div class="space-y-4">
        <div>
          <label class="block text-xs text-zinc-400 mb-1.5" for="feed-url">Feed URL</label>
          <input
            id="feed-url"
            class="input"
            type="url"
            placeholder="https://reddit.com/r/programming.rss"
            bind:value={url}
            onkeydown={(e) => e.key === 'Enter' && submit()}
          />
          <p class="text-xs text-zinc-600 mt-1">
            Supports RSS, Atom, and Reddit subreddit URLs
          </p>
        </div>

        {#if app.topics.length > 0}
          <div>
            <span class="block text-xs text-zinc-400 mb-1.5">Topics (optional)</span>
            <div class="flex flex-wrap gap-2">
              {#each app.topics as topic (topic.id)}
                <button
                  type="button"
                  onclick={() => toggleTopic(topic.id)}
                  class="px-3 py-1 rounded-full text-xs font-medium border transition-all
                         {selectedTopics.includes(topic.id)
                           ? 'border-transparent text-white'
                           : 'border-zinc-700 text-zinc-400 hover:border-zinc-500'}"
                  style={selectedTopics.includes(topic.id)
                    ? `background-color: ${topic.color}`
                    : ''}
                >
                  {topic.name}
                </button>
              {/each}
            </div>
          </div>
        {/if}

        {#if error}
          <p class="text-sm text-red-400">{error}</p>
        {/if}

        <div class="flex justify-end gap-2 pt-2">
          <button onclick={close} class="btn-ghost">Cancel</button>
          <button
            onclick={submit}
            class="btn-primary"
            disabled={loading || !url.trim()}
          >
            <Plus size={14} />
            {loading ? 'Adding…' : 'Add Feed'}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}
