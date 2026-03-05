<script>
  import { onMount } from 'svelte';
  import { Settings, Trash2, RefreshCw, Plus, Edit2, Check, Upload, Download, X } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import { settings as settingsApi, feeds as feedsApi, topics as topicsApi, filters as filtersApi } from '$lib/api.js';

  app.activeView = 'settings';

  let cfg = $state({ digest_time: '07:00', ollama_model: 'qwen3:8b', fetch_interval: 3600 });
  let saving = $state(false);
  let saved = $state(false);
  let editingFeed = $state(null);

  // OPML
  let importStatus = $state('');
  let fileInput = $state(null);

  // Mute filters
  let muteFilters = $state([]);
  let newPattern = $state('');
  let newIsRegex = $state(false);
  let newFeedId = $state(null);

  onMount(async () => {
    cfg = await settingsApi.get();
    muteFilters = await filtersApi.list();
  });

  async function saveSettings() {
    saving = true;
    try {
      cfg = await settingsApi.update(cfg);
      saved = true;
      setTimeout(() => (saved = false), 2000);
    } finally {
      saving = false;
    }
  }

  async function deleteFeed(id) {
    if (!confirm('Delete this feed and all its articles?')) return;
    await feedsApi.delete(id);
    await app.loadFeeds();
  }

  async function deleteTopic(id) {
    if (!confirm('Delete this topic? Feeds will not be deleted.')) return;
    await topicsApi.delete(id);
    await app.loadTopics();
  }

  async function saveFeedTitle(feed) {
    await feedsApi.update(feed.id, { title: feed.title });
    await app.loadFeeds();
    editingFeed = null;
  }

  async function exportOpml() {
    const blob = await feedsApi.exportOpml();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'readr-feeds.opml';
    a.click();
    URL.revokeObjectURL(url);
  }

  async function importOpml(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    importStatus = 'Importing…';
    try {
      const result = await feedsApi.importOpml(file);
      importStatus = `Imported ${result.imported} feeds, skipped ${result.skipped} duplicates.`;
      await app.loadFeeds();
      await app.loadTopics();
    } catch (err) {
      importStatus = `Error: ${err.message}`;
    }
    e.target.value = '';
  }

  async function addFilter() {
    if (!newPattern.trim()) return;
    const f = await filtersApi.create({ pattern: newPattern.trim(), is_regex: newIsRegex, feed_id: newFeedId });
    muteFilters = [...muteFilters, f];
    newPattern = '';
    newIsRegex = false;
    newFeedId = null;
  }

  async function removeFilter(id) {
    await filtersApi.delete(id);
    muteFilters = muteFilters.filter((f) => f.id !== id);
  }
</script>

<svelte:head>
  <title>Settings · Readr</title>
</svelte:head>

<div class="flex-1 overflow-y-auto px-4 py-6">
  <div class="max-w-2xl mx-auto space-y-8">
    <h1 class="text-lg font-bold flex items-center gap-2">
      <Settings size={18} class="text-violet-400" /> Settings
    </h1>

    <!-- General settings -->
    <section class="card p-5 space-y-5">
      <h2 class="text-sm font-semibold text-zinc-300">General</h2>

      <div class="grid sm:grid-cols-2 gap-4">
        <div>
          <label class="block text-xs text-zinc-400 mb-1.5" for="digest-time">
            Daily digest time
          </label>
          <input
            id="digest-time"
            class="input"
            type="time"
            bind:value={cfg.digest_time}
          />
        </div>

        <div>
          <label class="block text-xs text-zinc-400 mb-1.5" for="fetch-interval">
            Feed refresh interval (seconds)
          </label>
          <input
            id="fetch-interval"
            class="input"
            type="number"
            min="300"
            max="86400"
            step="300"
            bind:value={cfg.fetch_interval}
          />
        </div>
      </div>

      <div>
        <label class="block text-xs text-zinc-400 mb-1.5" for="ollama-model">
          Ollama model
        </label>
        <input
          id="ollama-model"
          class="input"
          type="text"
          placeholder="qwen3:8b"
          bind:value={cfg.ollama_model}
        />
        <p class="text-xs text-zinc-600 mt-1">
          Model must be pulled in Ollama first: <code class="text-zinc-500">docker exec ollama ollama pull {cfg.ollama_model}</code>
        </p>
      </div>

      <div class="flex justify-end">
        <button onclick={saveSettings} class="btn-primary" disabled={saving}>
          {#if saved}
            <Check size={14} /> Saved
          {:else}
            {saving ? 'Saving…' : 'Save Settings'}
          {/if}
        </button>
      </div>
    </section>

    <!-- Feeds -->
    <section class="card p-5">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-sm font-semibold text-zinc-300">Feeds ({app.feeds.length})</h2>
        <button onclick={() => (app.addFeedOpen = true)} class="btn-ghost text-xs">
          <Plus size={13} /> Add
        </button>
      </div>

      <div class="space-y-1">
        {#each app.feeds as feed (feed.id)}
          <div data-testid="feed-item" class="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-zinc-800/50 group">
            {#if feed.favicon_url}
              <img src={feed.favicon_url} alt="" class="w-4 h-4 rounded" onerror={(e) => e.currentTarget.remove()} />
            {/if}

            {#if editingFeed === feed.id}
              <input
                class="input py-1 text-xs flex-1"
                bind:value={feed.title}
                onkeydown={(e) => {
                  if (e.key === 'Enter') saveFeedTitle(feed);
                  if (e.key === 'Escape') editingFeed = null;
                }}
              />
              <button onclick={() => saveFeedTitle(feed)} class="btn-ghost p-1 text-xs">
                <Check size={12} />
              </button>
            {:else}
              <span class="flex-1 text-sm text-zinc-300 truncate">{feed.title || feed.url}</span>
              <span class="text-xs text-zinc-600 shrink-0">{feed.unread_count} unread</span>
              <div class="hidden group-hover:flex items-center gap-1">
                <button onclick={() => (editingFeed = feed.id)} class="btn-ghost p-1">
                  <Edit2 size={12} />
                </button>
                <button onclick={() => deleteFeed(feed.id)} class="btn-danger p-1">
                  <Trash2 size={12} />
                </button>
              </div>
            {/if}
          </div>
        {/each}

        {#if app.feeds.length === 0}
          <p class="text-sm text-zinc-600 px-3 py-2">No feeds added yet</p>
        {/if}
      </div>
    </section>

    <!-- OPML Import / Export -->
    <section class="card p-5 space-y-4">
      <h2 class="text-sm font-semibold text-zinc-300">Import / Export</h2>
      <div class="flex flex-wrap gap-3">
        <button onclick={exportOpml} class="btn-ghost text-xs">
          <Download size={13} /> Export OPML
        </button>
        <label class="btn-ghost text-xs cursor-pointer">
          <Upload size={13} /> Import OPML
          <input bind:this={fileInput} type="file" accept=".opml,.xml" class="hidden" onchange={importOpml} />
        </label>
      </div>
      {#if importStatus}
        <p class="text-xs {importStatus.startsWith('Error') ? 'text-red-400' : 'text-emerald-400'}">{importStatus}</p>
      {/if}
      <p class="text-xs text-zinc-600">
        OPML preserves topic/folder structure on export. On import, folders become topics automatically.
      </p>
    </section>

    <!-- Mute Filters -->
    <section class="card p-5 space-y-4">
      <h2 class="text-sm font-semibold text-zinc-300">Mute Filters</h2>
      <p class="text-xs text-zinc-500">
        Articles whose title or excerpt matches a filter are silently skipped during fetch.
        Supports plain keywords or regular expressions.
      </p>

      <!-- Add filter -->
      <div class="flex gap-2 items-end flex-wrap">
        <div class="flex-1 min-w-[160px]">
          <label class="block text-xs text-zinc-400 mb-1" for="mute-pattern">Pattern</label>
          <input
            id="mute-pattern"
            class="input text-sm"
            type="text"
            placeholder="e.g. sponsored, ^Breaking"
            bind:value={newPattern}
            onkeydown={(e) => e.key === 'Enter' && addFilter()}
          />
        </div>
        <div>
          <label class="block text-xs text-zinc-400 mb-1" for="mute-feed">Feed (optional)</label>
          <select
            id="mute-feed"
            class="input text-sm"
            bind:value={newFeedId}
          >
            <option value={null}>Global</option>
            {#each app.feeds as feed (feed.id)}
              <option value={feed.id}>{feed.title}</option>
            {/each}
          </select>
        </div>
        <label class="flex items-center gap-1.5 text-xs text-zinc-400 pb-2 cursor-pointer">
          <input type="checkbox" bind:checked={newIsRegex} class="rounded" />
          Regex
        </label>
        <button onclick={addFilter} class="btn-primary text-xs py-1.5 pb-2" disabled={!newPattern.trim()}>
          <Plus size={13} /> Add
        </button>
      </div>

      <!-- Filter list -->
      {#if muteFilters.length > 0}
        <div class="space-y-1">
          {#each muteFilters as f (f.id)}
            <div class="flex items-center gap-3 px-3 py-2 rounded-lg bg-zinc-800/50">
              <code class="flex-1 text-xs text-zinc-300 truncate">{f.pattern}</code>
              {#if f.is_regex}
                <span class="text-[10px] font-mono text-violet-400 bg-violet-950/40 px-1.5 py-0.5 rounded">regex</span>
              {/if}
              {#if f.feed_id}
                <span class="text-xs text-zinc-500 truncate max-w-[120px]">
                  {app.feeds.find((fd) => fd.id === f.feed_id)?.title ?? 'feed'}
                </span>
              {:else}
                <span class="text-xs text-zinc-600">global</span>
              {/if}
              <button onclick={() => removeFilter(f.id)} class="text-zinc-600 hover:text-red-400 transition-colors p-1 rounded">
                <X size={12} />
              </button>
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-xs text-zinc-600 italic">No filters yet</p>
      {/if}
    </section>

    <!-- Topics -->
    <section class="card p-5">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-sm font-semibold text-zinc-300">Topics ({app.topics.length})</h2>
        <button onclick={() => (app.addTopicOpen = true)} class="btn-ghost text-xs">
          <Plus size={13} /> Add
        </button>
      </div>

      <div class="space-y-1">
        {#each app.topics as topic (topic.id)}
          <div class="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-zinc-800/50 group">
            <span class="w-3 h-3 rounded-full shrink-0" style="background-color: {topic.color}"></span>
            <span class="flex-1 text-sm text-zinc-300">{topic.name}</span>
            <span class="text-xs text-zinc-600">{topic.feed_count} feeds</span>
            <button
              onclick={() => deleteTopic(topic.id)}
              class="btn-danger p-1 hidden group-hover:flex"
            >
              <Trash2 size={12} />
            </button>
          </div>
        {/each}

        {#if app.topics.length === 0}
          <p class="text-sm text-zinc-600 px-3 py-2">No topics yet</p>
        {/if}
      </div>
    </section>
  </div>
</div>
