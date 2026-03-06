<script>
  import { onMount } from 'svelte';
  import { Settings, Trash2, RefreshCw, Plus, Edit2, Check, Upload, Download, X, Tag, Zap, ToggleLeft, ToggleRight, AlertCircle, CheckCircle2 } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import { settings as settingsApi, feeds as feedsApi, topics as topicsApi, filters as filtersApi, tags as tagsApi, rules as rulesApi } from '$lib/api.js';

  app.activeView = 'settings';

  let cfg = $state({ digest_time: '07:00', ollama_model: 'qwen3.5:9b', fetch_interval: 3600 });
  let saving = $state(false);
  let saved = $state(false);
  let editingFeed = $state(null);

  // Ollama model picker
  let ollamaModels = $state([]);
  let ollamaStatus = $state(''); // '' | 'ok' | 'unreachable'
  let ollamaError = $state('');

  // OPML
  let importStatus = $state('');
  let fileInput = $state(null);

  // Mute filters
  let muteFilters = $state([]);
  let newPattern = $state('');
  let newIsRegex = $state(false);
  let newFeedId = $state(null);

  // Tags
  let allTags = $state([]);
  let newTagName = $state('');
  let newTagColor = $state('#6366f1');

  // Rules
  let allRules = $state([]);
  let newRuleName = $state('');
  let newRuleField = $state('title');
  let newRuleOp = $state('contains');
  let newRuleValue = $state('');
  let newRuleAction = $state('mark_read');
  let newRuleTagId = $state('');

  onMount(async () => {
    cfg = await settingsApi.get();
    muteFilters = await filtersApi.list();
    allTags = await tagsApi.list();
    allRules = await rulesApi.list();
    loadOllamaModels();
  });

  async function loadOllamaModels() {
    try {
      const res = await settingsApi.ollamaModels();
      ollamaModels = res.models;
      ollamaStatus = res.status;
      ollamaError = res.error || '';
    } catch {
      ollamaStatus = 'unreachable';
    }
  }

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

  async function addTag() {
    if (!newTagName.trim()) return;
    const t = await tagsApi.create({ name: newTagName.trim(), color: newTagColor });
    allTags = [...allTags, t];
    newTagName = '';
    newTagColor = '#6366f1';
  }

  async function removeTag(id) {
    await tagsApi.delete(id);
    allTags = allTags.filter((t) => t.id !== id);
  }

  function getRuleActionLabel(action) {
    if (action === 'mark_read') return 'Mark as read';
    if (action === 'save') return 'Save for later';
    if (action === 'bookmark') return 'Bookmark';
    if (action === 'mute') return 'Mute (discard)';
    if (action.startsWith('tag:')) {
      const tagId = parseInt(action.split(':')[1]);
      return `Tag: ${allTags.find((t) => t.id === tagId)?.name ?? tagId}`;
    }
    return action;
  }

  async function addRule() {
    if (!newRuleName.trim() || !newRuleValue.trim()) return;
    const action = newRuleAction === 'tag' ? `tag:${newRuleTagId}` : newRuleAction;
    const rule = await rulesApi.create({
      name: newRuleName.trim(),
      condition: { field: newRuleField, op: newRuleOp, value: newRuleValue.trim() },
      action,
    });
    allRules = [...allRules, rule];
    newRuleName = '';
    newRuleValue = '';
  }

  async function toggleRule(rule) {
    const updated = await rulesApi.update(rule.id, { is_active: !rule.is_active });
    allRules = allRules.map((r) => (r.id === updated.id ? updated : r));
  }

  async function removeRule(id) {
    await rulesApi.delete(id);
    allRules = allRules.filter((r) => r.id !== id);
  }
</script>

<svelte:head>
  <title>Settings · Readr</title>
</svelte:head>

<div data-testid="settings-scroll" class="flex-1 overflow-y-auto px-4 py-6">
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
        <div class="flex items-center justify-between mb-1.5">
          <label class="text-xs text-zinc-400" for="ollama-model">Ollama model</label>
          <div class="flex items-center gap-1.5 text-xs">
            {#if ollamaStatus === 'ok'}
              <CheckCircle2 size={12} class="text-emerald-400" />
              <span class="text-emerald-400">Connected</span>
            {:else if ollamaStatus === 'unreachable'}
              <AlertCircle size={12} class="text-red-400" />
              <span class="text-red-400">Ollama unreachable</span>
            {/if}
            <button onclick={loadOllamaModels} class="text-zinc-600 hover:text-zinc-300 transition-colors ml-1" title="Refresh model list">
              <RefreshCw size={11} />
            </button>
          </div>
        </div>

        {#if ollamaModels.length > 0}
          <select id="ollama-model" class="input" bind:value={cfg.ollama_model}>
            {#each ollamaModels as m}
              <option value={m}>{m}</option>
            {/each}
            <!-- Keep current value if not in list -->
            {#if !ollamaModels.includes(cfg.ollama_model)}
              <option value={cfg.ollama_model}>{cfg.ollama_model} (not installed)</option>
            {/if}
          </select>
        {:else}
          <input
            id="ollama-model"
            class="input"
            type="text"
            placeholder="qwen3.5:9b"
            bind:value={cfg.ollama_model}
          />
        {/if}

        {#if ollamaStatus === 'unreachable'}
          <p class="text-xs text-red-400/80 mt-1">{ollamaError || 'Cannot reach Ollama. Is the container running?'}</p>
        {:else}
          <p class="text-xs text-zinc-600 mt-1">
            Pull a model: <code class="text-zinc-500">docker exec rss-reader-ollama-1 ollama pull qwen3.5:9b</code>
          </p>
        {/if}
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
          {@const healthBadge = {
            ok:    { cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-800/40', label: 'ok' },
            stale: { cls: 'bg-amber-500/15 text-amber-400 border-amber-800/40',       label: 'stale' },
            error: { cls: 'bg-red-500/15 text-red-400 border-red-800/40',             label: 'error' },
            never: { cls: 'bg-zinc-700/30 text-zinc-500 border-zinc-700',             label: 'never fetched' },
          }[feed.health] ?? { cls: '', label: '' }}
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
              {#if feed.health && feed.health !== 'ok'}
                <span
                  class="text-[10px] px-1.5 py-0.5 rounded border shrink-0 {healthBadge.cls}"
                  title={feed.last_error || healthBadge.label}
                >{healthBadge.label}</span>
              {:else}
                <span class="text-xs text-zinc-600 shrink-0">{feed.unread_count} unread</span>
              {/if}
              <div class="hidden group-hover:flex items-center gap-1">
                <button onclick={() => (editingFeed = feed.id)} class="btn-ghost p-1" aria-label="Edit title">
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

    <!-- Tags -->
    <section class="card p-5 space-y-4">
      <h2 class="text-sm font-semibold text-zinc-300 flex items-center gap-2">
        <Tag size={14} class="text-violet-400" /> Tags
      </h2>
      <p class="text-xs text-zinc-500">
        Tags can be applied manually in the reader, or automatically via Rules.
      </p>

      <!-- Add tag -->
      <div class="flex gap-2 items-end flex-wrap">
        <div class="flex-1 min-w-[140px]">
          <label class="block text-xs text-zinc-400 mb-1" for="tag-name">Tag name</label>
          <input id="tag-name" class="input text-sm" type="text" placeholder="e.g. To Read" bind:value={newTagName}
            onkeydown={(e) => e.key === 'Enter' && addTag()} />
        </div>
        <div>
          <label class="block text-xs text-zinc-400 mb-1" for="tag-color">Color</label>
          <input id="tag-color" type="color" class="h-9 w-14 rounded border border-zinc-700 bg-zinc-900 cursor-pointer"
            bind:value={newTagColor} />
        </div>
        <button onclick={addTag} class="btn-primary text-xs py-1.5" disabled={!newTagName.trim()}>
          <Plus size={13} /> Add
        </button>
      </div>

      {#if allTags.length > 0}
        <div class="flex flex-wrap gap-2">
          {#each allTags as tag (tag.id)}
            <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs"
              style="color: {tag.color}; border-color: {tag.color}40; background: {tag.color}15">
              <span>{tag.name}</span>
              <button onclick={() => removeTag(tag.id)} class="hover:opacity-70 transition-opacity ml-0.5">
                <X size={11} />
              </button>
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-xs text-zinc-600 italic">No tags yet</p>
      {/if}
    </section>

    <!-- Rules -->
    <section class="card p-5 space-y-4">
      <h2 class="text-sm font-semibold text-zinc-300 flex items-center gap-2">
        <Zap size={14} class="text-violet-400" /> Automation Rules
      </h2>
      <p class="text-xs text-zinc-500">
        Rules are evaluated at fetch time. Matching articles are automatically acted upon.
      </p>

      <!-- Add rule -->
      <div class="space-y-3 p-3 bg-zinc-800/40 rounded-lg border border-zinc-800">
        <p class="text-xs font-semibold text-zinc-400">New rule</p>
        <div>
          <label class="block text-xs text-zinc-400 mb-1" for="rule-name">Rule name</label>
          <input id="rule-name" class="input text-sm" type="text" placeholder="e.g. Auto-save AI articles"
            bind:value={newRuleName} />
        </div>
        <div class="grid grid-cols-3 gap-2">
          <div>
            <label class="block text-xs text-zinc-400 mb-1">Field</label>
            <select class="input text-sm" bind:value={newRuleField}>
              <option value="title">Title</option>
              <option value="author">Author</option>
              <option value="excerpt">Excerpt</option>
              <option value="feed_id">Feed ID</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-zinc-400 mb-1">Condition</label>
            <select class="input text-sm" bind:value={newRuleOp}>
              <option value="contains">contains</option>
              <option value="not_contains">doesn't contain</option>
              <option value="equals">equals</option>
              <option value="matches">regex matches</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-zinc-400 mb-1">Value</label>
            <input class="input text-sm" type="text" placeholder="e.g. AI, GPT" bind:value={newRuleValue} />
          </div>
        </div>
        <div class="flex gap-2 items-end">
          <div class="flex-1">
            <label class="block text-xs text-zinc-400 mb-1">Action</label>
            <select class="input text-sm" bind:value={newRuleAction}>
              <option value="mark_read">Mark as read</option>
              <option value="save">Save for later</option>
              <option value="bookmark">Bookmark</option>
              <option value="mute">Mute (discard)</option>
              <option value="tag">Apply tag…</option>
            </select>
          </div>
          {#if newRuleAction === 'tag'}
            <div class="flex-1">
              <label class="block text-xs text-zinc-400 mb-1">Tag</label>
              <select class="input text-sm" bind:value={newRuleTagId}>
                {#each allTags as t (t.id)}
                  <option value={t.id}>{t.name}</option>
                {/each}
              </select>
            </div>
          {/if}
          <button onclick={addRule} class="btn-primary text-xs py-1.5 shrink-0"
            disabled={!newRuleName.trim() || !newRuleValue.trim() || (newRuleAction === 'tag' && !newRuleTagId)}>
            <Plus size={13} /> Add Rule
          </button>
        </div>
      </div>

      <!-- Rule list -->
      {#if allRules.length > 0}
        <div class="space-y-2">
          {#each allRules as rule (rule.id)}
            <div class="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-zinc-800/50 {rule.is_active ? '' : 'opacity-50'}">
              <button onclick={() => toggleRule(rule)} class="shrink-0 text-zinc-500 hover:text-violet-400 transition-colors"
                title={rule.is_active ? 'Disable rule' : 'Enable rule'}>
                {#if rule.is_active}
                  <ToggleRight size={18} class="text-violet-400" />
                {:else}
                  <ToggleLeft size={18} />
                {/if}
              </button>
              <div class="flex-1 min-w-0">
                <p class="text-sm text-zinc-200 truncate">{rule.name}</p>
                <p class="text-xs text-zinc-500 truncate">
                  {rule.condition.field} {rule.condition.op} "<span class="text-zinc-400">{rule.condition.value}</span>"
                  → <span class="text-violet-400">{getRuleActionLabel(rule.action)}</span>
                </p>
              </div>
              <button onclick={() => removeRule(rule.id)} class="text-zinc-600 hover:text-red-400 transition-colors p-1 rounded shrink-0">
                <Trash2 size={13} />
              </button>
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-xs text-zinc-600 italic">No rules yet</p>
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
