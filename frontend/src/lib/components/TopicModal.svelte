<script>
  import { X, Plus } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import { topics as topicsApi } from '$lib/api.js';

  let name = $state('');
  let color = $state('#6366f1');
  let loading = $state(false);
  let error = $state('');

  const COLORS = [
    '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e',
    '#f97316', '#eab308', '#22c55e', '#14b8a6',
    '#3b82f6', '#06b6d4',
  ];

  async function submit() {
    if (!name.trim()) return;
    loading = true;
    error = '';
    try {
      await topicsApi.create({ name: name.trim(), color });
      await app.loadTopics();
      close();
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  function close() {
    app.addTopicOpen = false;
    name = '';
    color = '#6366f1';
    error = '';
  }

  function handleKey(e) {
    if (e.key === 'Escape') close();
  }
</script>

<svelte:window onkeydown={handleKey} />

{#if app.addTopicOpen}
  <div
    class="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 animate-fade-in"
    onclick={(e) => e.target === e.currentTarget && close()}
    onkeydown={(e) => e.key === 'Escape' && close()}
    role="dialog"
    tabindex="-1"
    aria-modal="true"
    aria-label="Add topic"
  >
    <div class="card w-full max-w-sm p-6 animate-slide-in-up">
      <div class="flex items-center justify-between mb-5">
        <h2 class="text-base font-semibold">New Topic</h2>
        <button onclick={close} class="btn-ghost p-1"><X size={16} /></button>
      </div>

      <div class="space-y-4">
        <div>
          <label class="block text-xs text-zinc-400 mb-1.5" for="topic-name">Name</label>
          <input
            id="topic-name"
            class="input"
            type="text"
            placeholder="e.g. Tech, Finance, Sports…"
            bind:value={name}
            onkeydown={(e) => e.key === 'Enter' && submit()}
          />
        </div>

        <div>
          <span class="block text-xs text-zinc-400 mb-1.5">Color</span>
          <div class="flex flex-wrap gap-2">
            {#each COLORS as c}
              <button
                type="button"
                onclick={() => (color = c)}
                class="w-7 h-7 rounded-full transition-transform
                       {color === c ? 'ring-2 ring-white ring-offset-2 ring-offset-zinc-900 scale-110' : 'hover:scale-105'}"
                style="background-color: {c}"
                aria-label="Color {c}"
              ></button>
            {/each}
          </div>
        </div>

        {#if error}
          <p class="text-sm text-red-400">{error}</p>
        {/if}

        <div class="flex justify-end gap-2 pt-1">
          <button onclick={close} class="btn-ghost">Cancel</button>
          <button onclick={submit} class="btn-primary" disabled={loading || !name.trim()}>
            <Plus size={14} />
            {loading ? 'Creating…' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}
