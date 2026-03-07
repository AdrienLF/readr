<script>
  import { X, Upload, Sparkles, Trash2, ChevronDown, Loader2 } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import { feeds as feedsApi } from '$lib/api.js';

  let step = $state('input'); // input | classifying | review
  let urlText = $state('');
  let classifiedFeeds = $state([]);
  let error = $state('');
  let loading = $state(false);
  let importResult = $state(null);

  // Gather unique topic names from classification results
  let topicNames = $derived.by(() => {
    const seen = new Set();
    const topics = [];
    for (const f of classifiedFeeds) {
      if (!seen.has(f.topic_name)) {
        seen.add(f.topic_name);
        topics.push({ name: f.topic_name, color: f.topic_color, is_new: f.is_new_topic });
      }
    }
    return topics;
  });

  function parseUrls() {
    const matches = urlText.match(/https?:\/\/[^\s,;)"'<>]+/g) || [];
    // Deduplicate and strip trailing punctuation like periods or parentheses
    const seen = new Set();
    return matches
      .map((u) => u.replace(/[.)]+$/, ''))
      .filter((u) => {
        if (seen.has(u)) return false;
        seen.add(u);
        return true;
      });
  }

  async function classify() {
    const urls = parseUrls();
    if (urls.length === 0) {
      error = 'Enter at least one valid URL (starting with http:// or https://)';
      return;
    }
    error = '';
    loading = true;
    step = 'classifying';
    try {
      const result = await feedsApi.bulkClassify(urls);
      classifiedFeeds = result.feeds;
      step = 'review';
    } catch (e) {
      error = e.message || 'Classification failed. Is Ollama running?';
      step = 'input';
    } finally {
      loading = false;
    }
  }

  function removeFeed(index) {
    classifiedFeeds = classifiedFeeds.filter((_, i) => i !== index);
  }

  function setFeedTopic(index, topicName, topicColor, isNew) {
    classifiedFeeds = classifiedFeeds.map((f, i) =>
      i === index ? { ...f, topic_name: topicName, topic_color: topicColor, is_new_topic: isNew } : f
    );
  }

  async function doImport() {
    const toImport = classifiedFeeds.filter((f) => !f.already_exists);
    if (toImport.length === 0) {
      error = 'No new feeds to import (all already exist)';
      return;
    }
    loading = true;
    error = '';
    try {
      importResult = await feedsApi.bulkImport({
        feeds: toImport.map((f) => ({
          url: f.url,
          topic_name: f.topic_name,
          topic_color: f.topic_color,
        })),
      });
      await Promise.all([app.loadFeeds(), app.loadTopics()]);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  function close() {
    app.bulkAddOpen = false;
    step = 'input';
    urlText = '';
    classifiedFeeds = [];
    error = '';
    loading = false;
    importResult = null;
  }
</script>

{#if app.bulkAddOpen}
  <div
    class="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 animate-fade-in"
    onclick={(e) => e.target === e.currentTarget && close()}
    onkeydown={(e) => e.key === 'Escape' && close()}
    role="dialog"
    tabindex="-1"
    aria-modal="true"
    aria-label="Bulk add feeds"
  >
    <div class="card w-full max-w-2xl p-6 animate-slide-in-up max-h-[80vh] flex flex-col">
      <div class="flex items-center justify-between mb-5 shrink-0">
        <div class="flex items-center gap-2">
          <Upload size={18} class="text-violet-400" />
          <h2 class="text-base font-semibold">Bulk Add Feeds</h2>
        </div>
        <button onclick={close} class="btn-ghost p-1"><X size={16} /></button>
      </div>

      {#if importResult}
        <!-- Success state -->
        <div class="space-y-4">
          <div class="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4 text-sm">
            <p class="text-emerald-400 font-medium mb-1">Import complete</p>
            <p class="text-zinc-300">
              {importResult.added} feed{importResult.added !== 1 ? 's' : ''} added
              {#if importResult.skipped > 0}
                , {importResult.skipped} skipped (already existed)
              {/if}
              {#if importResult.topics_created > 0}
                , {importResult.topics_created} new topic{importResult.topics_created !== 1 ? 's' : ''} created
              {/if}
            </p>
          </div>
          <div class="flex justify-end">
            <button onclick={close} class="btn-primary">Done</button>
          </div>
        </div>

      {:else if step === 'input' || step === 'classifying'}
        <!-- Step 1: URL input -->
        <div class="space-y-4">
          <div>
            <label class="block text-xs text-zinc-400 mb-1.5" for="bulk-urls">
              Paste feed URLs or text containing URLs
            </label>
            <textarea
              id="bulk-urls"
              class="input min-h-[200px] font-mono text-xs resize-y"
              placeholder="Paste a list of URLs, or any text containing feed URLs — they'll be extracted automatically."
              bind:value={urlText}
              disabled={step === 'classifying'}
            ></textarea>
            <p class="text-xs text-zinc-600 mt-1">
              {parseUrls().length} valid URL{parseUrls().length !== 1 ? 's' : ''} detected
            </p>
          </div>

          {#if error}
            <p class="text-sm text-red-400">{error}</p>
          {/if}

          <div class="flex justify-end gap-2 pt-1">
            <button onclick={close} class="btn-ghost">Cancel</button>
            <button
              onclick={classify}
              class="btn-primary"
              disabled={loading || parseUrls().length === 0}
            >
              {#if loading}
                <Loader2 size={14} class="animate-spin" />
                Classifying...
              {:else}
                <Sparkles size={14} />
                Classify with AI
              {/if}
            </button>
          </div>
        </div>

      {:else if step === 'review'}
        <!-- Step 2: Review classifications -->
        <div class="space-y-4 min-h-0 flex flex-col">
          <!-- Topic legend -->
          <div class="flex flex-wrap gap-1.5 shrink-0">
            {#each topicNames as topic (topic.name)}
              <span
                class="px-2 py-0.5 rounded-full text-[11px] font-medium text-white"
                style="background-color: {topic.color}"
              >
                {topic.name}
                {#if topic.is_new}
                  <span class="opacity-70">new</span>
                {/if}
              </span>
            {/each}
          </div>

          <!-- Feed list -->
          <div class="overflow-y-auto min-h-0 flex-1 space-y-1 -mx-1 px-1">
            {#each classifiedFeeds as feed, i (feed.url)}
              <div
                class="flex items-center gap-2 py-2 px-2 rounded-lg group
                       {feed.already_exists ? 'opacity-50' : 'hover:bg-zinc-800/50'}"
              >
                <div class="flex-1 min-w-0">
                  <p class="text-sm truncate" title={feed.title || feed.url}>
                    {feed.title || feed.url}
                    {#if feed.already_exists}
                      <span class="text-xs text-zinc-500 ml-1">(exists)</span>
                    {/if}
                  </p>
                  <p class="text-xs text-zinc-500 truncate">{feed.url}</p>
                </div>

                <!-- Topic selector -->
                <div class="relative shrink-0">
                  <select
                    class="appearance-none pl-2 pr-6 py-1 rounded-full text-xs font-medium text-white border-0 cursor-pointer focus:ring-1 focus:ring-violet-500"
                    style="background-color: {feed.topic_color}"
                    value={feed.topic_name}
                    onchange={(e) => {
                      const selected = topicNames.find((t) => t.name === e.target.value);
                      if (selected) setFeedTopic(i, selected.name, selected.color, selected.is_new);
                    }}
                    disabled={feed.already_exists}
                  >
                    {#each topicNames as topic (topic.name)}
                      <option value={topic.name}>{topic.name}</option>
                    {/each}
                  </select>
                  <ChevronDown size={10} class="absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                </div>

                {#if !feed.already_exists}
                  <button
                    onclick={() => removeFeed(i)}
                    class="btn-ghost p-1 opacity-0 group-hover:opacity-100 shrink-0"
                    aria-label="Remove"
                  >
                    <Trash2 size={13} class="text-zinc-500" />
                  </button>
                {/if}
              </div>
            {/each}
          </div>

          {#if error}
            <p class="text-sm text-red-400 shrink-0">{error}</p>
          {/if}

          <div class="flex items-center justify-between pt-2 border-t border-zinc-800 shrink-0">
            <button onclick={() => { step = 'input'; error = ''; }} class="btn-ghost text-xs">
              Back
            </button>
            <div class="flex gap-2">
              <button onclick={close} class="btn-ghost">Cancel</button>
              <button
                onclick={doImport}
                class="btn-primary"
                disabled={loading || classifiedFeeds.filter((f) => !f.already_exists).length === 0}
              >
                {#if loading}
                  <Loader2 size={14} class="animate-spin" />
                  Importing...
                {:else}
                  <Upload size={14} />
                  Import {classifiedFeeds.filter((f) => !f.already_exists).length} Feed{classifiedFeeds.filter((f) => !f.already_exists).length !== 1 ? 's' : ''}
                {/if}
              </button>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}
