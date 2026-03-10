<script>
  import { X, Trash2, Sparkles, Loader2 } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import { savedSearches as savedSearchesApi } from '$lib/api.js';

  let { search = $bindable(null) } = $props();

  let terms = $state([]);
  let busy = $state(false);
  let dirty = $state(false);

  // Sync terms when search changes
  $effect(() => {
    if (search?.expanded_terms) {
      terms = [...search.expanded_terms];
      dirty = false;
    }
  });

  function removeTerm(index) {
    terms = terms.filter((_, i) => i !== index);
    dirty = true;
  }

  function removeAll() {
    terms = [];
    dirty = true;
  }

  async function save() {
    if (!dirty || busy) return;
    busy = true;
    try {
      await savedSearchesApi.update(search.id, { expanded_terms: terms });
      await app.loadSavedSearches();
      dirty = false;
    } finally {
      busy = false;
    }
  }

  async function deleteSearch() {
    if (busy) return;
    if (!confirm('Delete this smart search and all its matches?')) return;
    busy = true;
    try {
      await savedSearchesApi.delete(search.id);
      await app.loadSavedSearches();
      if (app.selectedSmartSearchId === search.id) app.selectAll();
      close();
    } finally {
      busy = false;
    }
  }

  function close() {
    search = null;
    dirty = false;
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && search && close()} />

{#if search}
  <div
    class="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 animate-fade-in"
    onclick={(e) => e.target === e.currentTarget && close()}
    role="dialog"
    tabindex="-1"
    aria-modal="true"
    aria-label="Smart search details"
  >
    <div class="card w-full max-w-md p-6 animate-slide-in-up max-h-[80vh] flex flex-col">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-2 min-w-0">
          <Sparkles size={14} class="text-violet-400 shrink-0" />
          <h2 class="text-base font-semibold truncate">{search.name}</h2>
        </div>
        <button onclick={close} class="btn-ghost p-1 shrink-0"><X size={16} /></button>
      </div>

      <p class="text-xs text-zinc-500 mb-1">Query</p>
      <p class="text-sm text-zinc-300 mb-4">{search.query}</p>

      <div class="flex items-center justify-between mb-2">
        <p class="text-xs text-zinc-500">
          {search.is_strict ? 'Keywords' : 'AI-expanded terms'} ({terms.length})
        </p>
        {#if terms.length > 0}
          <button onclick={removeAll} class="text-[11px] text-zinc-600 hover:text-red-400 transition-colors">
            Remove all
          </button>
        {/if}
      </div>

      <div class="flex-1 overflow-y-auto min-h-0 mb-4">
        {#if !search.expanded_terms && !search.is_strict}
          <div class="flex items-center gap-2 py-4 justify-center text-zinc-500 text-sm">
            <Loader2 size={14} class="animate-spin" />
            <span>Generating terms…</span>
          </div>
        {:else if terms.length === 0}
          <p class="text-sm text-zinc-600 italic py-2">No terms. This search won't match any articles.</p>
        {:else}
          <div class="flex flex-wrap gap-1.5">
            {#each terms as term, i (term + i)}
              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-800 border border-zinc-700 text-[12px] text-zinc-300 group/tag">
                {term}
                <button
                  onclick={() => removeTerm(i)}
                  class="opacity-0 group-hover/tag:opacity-100 hover:text-red-400 transition-all -mr-0.5"
                  aria-label="Remove term"
                >
                  <X size={10} />
                </button>
              </span>
            {/each}
          </div>
        {/if}
      </div>

      <div class="flex items-center justify-between pt-3 border-t border-zinc-800">
        <button
          onclick={deleteSearch}
          disabled={busy}
          class="flex items-center gap-1.5 text-[13px] text-zinc-500 hover:text-red-400 transition-colors
                 {busy ? 'opacity-50 cursor-wait' : ''}"
        >
          <Trash2 size={13} />
          Delete search
        </button>

        <div class="flex gap-2">
          <button onclick={close} class="btn-ghost text-[13px]">
            {dirty ? 'Cancel' : 'Close'}
          </button>
          {#if dirty}
            <button onclick={save} class="btn-primary text-[13px]" disabled={busy}>
              {busy ? 'Saving…' : 'Save changes'}
            </button>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}
