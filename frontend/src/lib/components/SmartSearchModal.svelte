<script>
  import { X, Plus } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import { savedSearches as savedSearchesApi } from '$lib/api.js';

  let name = $state('');
  let query = $state('');
  let loading = $state(false);
  let error = $state('');

  async function submit() {
    if (!name.trim() || !query.trim()) return;
    loading = true;
    error = '';
    try {
      const created = await savedSearchesApi.create({ name: name.trim(), query: query.trim() });
      await app.loadSavedSearches();
      app.selectSmartSearch(created.id);
      close();
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  function close() {
    app.addSmartSearchOpen = false;
    name = '';
    query = '';
    error = '';
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && app.addSmartSearchOpen && close()} />

{#if app.addSmartSearchOpen}
  <div
    class="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 animate-fade-in"
    onclick={(e) => e.target === e.currentTarget && close()}
    role="dialog"
    tabindex="-1"
    aria-modal="true"
    aria-label="Add smart search"
  >
    <div class="card w-full max-w-md p-6 animate-slide-in-up">
      <div class="flex items-center justify-between mb-5">
        <h2 class="text-base font-semibold">New Smart Search</h2>
        <button onclick={close} class="btn-ghost p-1"><X size={16} /></button>
      </div>

      <div class="space-y-4">
        <div>
          <label class="block text-xs text-zinc-400 mb-1.5" for="ss-name">Name</label>
          <input
            id="ss-name"
            class="input"
            type="text"
            placeholder="e.g. Woodworking, AI Research…"
            bind:value={name}
          />
        </div>

        <div>
          <label class="block text-xs text-zinc-400 mb-1.5" for="ss-query">
            What are you interested in?
          </label>
          <textarea
            id="ss-query"
            class="input min-h-[80px] resize-none"
            placeholder="Describe the topic in plain language — Ollama will expand it into search terms automatically."
            bind:value={query}
          ></textarea>
          <p class="text-xs text-zinc-500 mt-1">
            Ollama will generate related keywords. New articles are matched automatically.
          </p>
        </div>

        {#if error}
          <p class="text-sm text-red-400">{error}</p>
        {/if}

        <div class="flex justify-end gap-2 pt-1">
          <button onclick={close} class="btn-ghost">Cancel</button>
          <button
            onclick={submit}
            class="btn-primary"
            disabled={loading || !name.trim() || !query.trim()}
          >
            <Plus size={14} />
            {loading ? 'Creating…' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}
