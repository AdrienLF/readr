<script>
  import { onMount } from 'svelte';
  import { format } from 'date-fns';
  import { marked } from 'marked';
  import { Zap, RefreshCw, ChevronDown, AlertCircle } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import { digests as digestsApi } from '$lib/api.js';

  app.activeView = 'digest';

  const renderer = new marked.Renderer();
  const origLink = renderer.link.bind(renderer);
  renderer.link = function (args) {
    const html = origLink(args);
    return html.replace('<a ', '<a target="_blank" rel="noopener noreferrer" ');
  };
  marked.use({ renderer });

  let digestList = $state([]);
  let loading = $state(false);
  let generating = $state(false);
  let generateError = $state('');
  let selectedDate = $state(new Date().toISOString().split('T')[0]);
  let openId = $state(null);

  async function load() {
    loading = true;
    try {
      digestList = await digestsApi.list(selectedDate);
    } finally {
      loading = false;
    }
  }

  async function generate(topicId = undefined) {
    generating = true;
    generateError = '';
    try {
      const results = await digestsApi.generate(topicId, selectedDate);
      digestList = results ?? [];
    } catch (err) {
      generateError = err.message || 'Generation failed';
    } finally {
      generating = false;
    }
  }

  onMount(() => load());

  $effect(() => {
    selectedDate;
    load();
  });

  function formatDate(d) {
    try {
      return format(new Date(d + 'T00:00:00'), 'EEEE, MMMM d yyyy');
    } catch {
      return d;
    }
  }
</script>

<svelte:head>
  <title>Digest · Readr</title>
</svelte:head>

<div class="flex flex-col h-full overflow-y-auto">
  <!-- Header -->
  <div class="sticky top-0 z-10 bg-zinc-950/90 backdrop-blur border-b border-zinc-800/50 px-4 py-3">
    <div class="flex items-center justify-between max-w-3xl mx-auto">
      <div class="flex items-center gap-3">
        <Zap size={18} class="text-violet-400" />
        <h1 class="font-semibold">Daily Digest</h1>
      </div>
      <div class="flex items-center gap-2">
        <input
          type="date"
          bind:value={selectedDate}
          class="input py-1 text-xs w-36"
        />
        <button
          onclick={() => generate()}
          class="btn-primary text-xs py-1.5"
          disabled={generating}
        >
          <RefreshCw size={13} class={generating ? 'animate-spin' : ''} />
          {generating ? 'Generating…' : 'Generate'}
        </button>
      </div>
    </div>
    {#if generateError}
      <div class="flex items-center gap-2 mt-2 px-3 py-2 bg-red-950/40 border border-red-800/50 rounded-lg max-w-3xl mx-auto text-xs text-red-400">
        <AlertCircle size={13} class="shrink-0" />
        {generateError}
      </div>
    {/if}
  </div>

  <div class="flex-1 px-4 py-6 max-w-3xl mx-auto w-full">
    {#if loading}
      <div class="flex items-center justify-center h-40 text-zinc-500">Loading…</div>
    {:else if digestList.length === 0}
      <div class="flex flex-col items-center justify-center h-64 text-zinc-600 text-center">
        <Zap size={32} class="mb-3 opacity-30" />
        <p class="text-base mb-1">No digest for {formatDate(selectedDate)}</p>
        <p class="text-sm mb-4">Click Generate to create one with AI</p>
        <button onclick={() => generate()} class="btn-primary" disabled={generating}>
          <Zap size={14} />
          {generating ? 'Generating…' : 'Generate Digest'}
        </button>
      </div>
    {:else}
      <p class="text-sm text-zinc-500 mb-6">{formatDate(selectedDate)}</p>
      <div class="space-y-3">
        {#each digestList as digest (digest.id)}
          <div class="card overflow-hidden">
            <button
              onclick={() => (openId = openId === digest.id ? null : digest.id)}
              class="w-full flex items-center justify-between px-5 py-4 hover:bg-zinc-800/50 transition-colors"
            >
              <div class="flex items-center gap-3">
                <span
                  class="w-2 h-2 rounded-full"
                  style="background-color: {app.topics.find((t) => t.id === digest.topic_id)?.color || '#6366f1'}"
                ></span>
                <span class="font-medium text-sm">{digest.topic_name || 'All Topics'}</span>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-xs text-zinc-600">{digest.model_used}</span>
                <ChevronDown
                  size={16}
                  class="text-zinc-500 transition-transform duration-200 {openId === digest.id ? 'rotate-180' : ''}"
                />
              </div>
            </button>

            {#if openId === digest.id}
              <div class="px-5 pb-5 border-t border-zinc-800">
                <div class="mt-4 prose prose-invert prose-sm max-w-none
                            prose-p:text-zinc-300 prose-headings:text-zinc-200 prose-headings:font-semibold
                            prose-strong:text-zinc-200 prose-li:text-zinc-300
                            prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5">
                  {@html marked(digest.content || '')}
                </div>
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>
