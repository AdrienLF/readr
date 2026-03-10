<script>
  import { onMount } from 'svelte';
  import { format } from 'date-fns';
  import { marked } from 'marked';
  import { sanitize } from '$lib/sanitize.js';
  import {
    X, ExternalLink, Bookmark, BookmarkCheck, BookmarkPlus, MessageSquare,
    Zap, Tag, StickyNote, Globe, ThumbsUp, ThumbsDown, Highlighter, Cpu,
    ChevronLeft, ChevronRight, ArrowUp,
  } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import { articles as articlesApi, tags as tagsApi } from '$lib/api.js';
  import CommentThread from './CommentThread.svelte';

  let article = $state(null);
  let comments = $state([]);
  let commentsLoading = $state(false);
  let commentsOpen = $state(false);
  let loading = $state(false);

  // Notes
  let noteValue = $state('');
  let noteEditing = $state(false);
  let noteSaving = $state(false);

  // Summary
  let summarizing = $state(false);

  // Tags
  let allTags = $state([]);
  let tagsOpen = $state(false);

  // Panels
  let noteOpen = $state(false);

  // Iframe mode
  let iframeMode = $state(false);

  // Highlights
  let highlights = $state([]);
  let highlightsOpen = $state(false);
  let selectionText = $state('');
  let pickerVisible = $state(false);
  let pickerX = $state(0);
  let pickerY = $state(0);

  // Signals (thumbs)
  let userSignal = $state(null);

  // Entities
  let entities = $state([]);
  let entitiesOpen = $state(false);
  let extractingEntities = $state(false);

  onMount(async () => {
    allTags = await tagsApi.list();
  });

  $effect(() => {
    if (app.selectedArticleId) {
      loadArticle(app.selectedArticleId);
    }
  });

  async function loadArticle(id) {
    loading = true;
    comments = [];
    commentsOpen = false;
    noteEditing = false;
    noteOpen = false;
    tagsOpen = false;
    iframeMode = false;
    pickerVisible = false;
    highlightsOpen = false;
    entitiesOpen = false;
    try {
      article = await articlesApi.get(id);
      noteValue = article.note || '';
      highlights = article.highlights || [];
      entities = article.entities || [];
      userSignal = article.user_signal ?? null;
    } finally {
      loading = false;
    }
  }

  async function loadComments() {
    if (commentsLoading || !article) return;
    commentsLoading = true;
    try {
      const data = await articlesApi.getComments(article.id);
      comments = data.comments;
      // Update score/comment_count from fresh Reddit data
      if (data.score != null || data.comment_count != null) {
        article = { ...article, score: data.score ?? article.score, comment_count: data.comment_count ?? article.comment_count };
      }
      commentsOpen = true;
    } finally {
      commentsLoading = false;
    }
  }

  async function toggleBookmark() {
    if (!article) return;
    const updated = await articlesApi.toggleBookmark(article.id);
    article = { ...article, is_bookmarked: updated.is_bookmarked };
  }

  async function toggleSaved() {
    if (!article) return;
    const updated = await articlesApi.toggleSaved(article.id);
    article = { ...article, is_saved: updated.is_saved };
  }

  async function saveNote() {
    if (!article) return;
    noteSaving = true;
    try {
      await articlesApi.updateNote(article.id, noteValue || null);
      article = { ...article, note: noteValue || null };
      noteEditing = false;
    } finally {
      noteSaving = false;
    }
  }

  async function generateSummary() {
    if (!article || summarizing) return;
    summarizing = true;
    try {
      const res = await articlesApi.summarize(article.id);
      article = { ...article, summary: res.summary };
    } finally {
      summarizing = false;
    }
  }

  async function addTag(tag) {
    if (!article) return;
    const res = await articlesApi.addTag(article.id, tag.id);
    article = { ...article, tags: res.tags };
  }

  async function removeTag(tagId) {
    if (!article) return;
    const res = await articlesApi.removeTag(article.id, tagId);
    article = { ...article, tags: res.tags };
  }

  // --- Signal ---
  async function toggleSignal(signal) {
    if (!article) return;
    const next = userSignal === signal ? 0 : signal;
    await articlesApi.signal(article.id, next);
    userSignal = next === 0 ? null : next;
  }

  // --- Highlights ---
  function handleTextSelect(e) {
    if (iframeMode) return;
    const sel = window.getSelection();
    const text = sel?.toString().trim();
    if (!text || text.length < 3) {
      pickerVisible = false;
      return;
    }
    selectionText = text;
    const range = sel.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    pickerX = rect.left + rect.width / 2;
    pickerY = rect.top - 8;
    pickerVisible = true;
  }

  const HIGHLIGHT_COLORS = [
    { id: 'yellow', bg: '#fef08a', border: '#ca8a04' },
    { id: 'green',  bg: '#bbf7d0', border: '#16a34a' },
    { id: 'blue',   bg: '#bae6fd', border: '#0284c7' },
    { id: 'pink',   bg: '#fbcfe8', border: '#db2777' },
  ];

  async function saveHighlight(color) {
    if (!article || !selectionText) return;
    pickerVisible = false;
    const h = await articlesApi.addHighlight(article.id, { text: selectionText, color });
    highlights = [...highlights, h];
    window.getSelection()?.removeAllRanges();
    highlightsOpen = true;
  }

  async function deleteHighlight(id) {
    if (!article) return;
    await articlesApi.deleteHighlight(article.id, id);
    highlights = highlights.filter((h) => h.id !== id);
  }

  // --- Entity extraction ---
  async function extractEntities() {
    if (!article || extractingEntities) return;
    extractingEntities = true;
    try {
      const result = await articlesApi.extractEntities(article.id);
      entities = result;
      entitiesOpen = true;
    } finally {
      extractingEntities = false;
    }
  }

  function formatDate(d) {
    if (!d) return '';
    try {
      return format(new Date(d), 'MMM d, yyyy · h:mm a');
    } catch {
      return '';
    }
  }

  let isReddit = $derived(article?.feed_source_type === 'reddit');

  // Auto-load comments for Reddit posts
  $effect(() => {
    if (article && isReddit && !commentsOpen && comments.length === 0 && !commentsLoading) {
      loadComments();
    }
  });

  function fmtNum(n) {
    if (n == null) return '';
    if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k';
    return String(n);
  }

  let articleTagIds = $derived(new Set((article?.tags || []).map((t) => t.id)));
  let unattachedTags = $derived(allTags.filter((t) => !articleTagIds.has(t.id)));

  const ENTITY_TYPE_COLORS = {
    PERSON:  { bg: 'bg-violet-950/40', text: 'text-violet-300', border: 'border-violet-800/40' },
    ORG:     { bg: 'bg-blue-950/40',   text: 'text-blue-300',   border: 'border-blue-800/40' },
    PLACE:   { bg: 'bg-emerald-950/40',text: 'text-emerald-300',border: 'border-emerald-800/40' },
    TOPIC:   { bg: 'bg-amber-950/40',  text: 'text-amber-300',  border: 'border-amber-800/40' },
    PRODUCT: { bg: 'bg-cyan-950/40',   text: 'text-cyan-300',   border: 'border-cyan-800/40' },
    EVENT:   { bg: 'bg-rose-950/40',   text: 'text-rose-300',   border: 'border-rose-800/40' },
  };

  function entityColors(type) {
    return ENTITY_TYPE_COLORS[type] ?? ENTITY_TYPE_COLORS.TOPIC;
  }

  let currentIndex = $derived(app.articleIds.indexOf(app.selectedArticleId));
  let hasPrev = $derived(currentIndex > 0);
  let hasNext = $derived(currentIndex !== -1 && currentIndex < app.articleIds.length - 1);

  // Close on Escape, navigate with arrow keys
  function handleKeydown(e) {
    if (!app.readerOpen) return;
    const tag = e.target?.tagName;
    if (tag === 'TEXTAREA' || e.target?.isContentEditable) return;
    if (e.key === 'Escape') {
      if (pickerVisible) { pickerVisible = false; return; }
      if (noteEditing) { noteEditing = false; return; }
      if (tagsOpen) { tagsOpen = false; return; }
      app.closeReader();
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      if (hasPrev) { e.preventDefault(); app.openPrevArticle(); }
    } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      if (hasNext) { e.preventDefault(); app.openNextArticle(); }
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- Highlight color picker (fixed, floats above selection) -->
{#if pickerVisible}
  <div
    class="fixed z-[100] flex items-center gap-1 p-1.5 rounded-lg bg-zinc-800 border border-zinc-700 shadow-xl"
    style="left: {pickerX}px; top: {pickerY}px; transform: translate(-50%, -100%);"
    onmouseleave={() => { if (!window.getSelection()?.toString().trim()) pickerVisible = false; }}
  >
    {#each HIGHLIGHT_COLORS as c}
      <button
        onclick={() => saveHighlight(c.id)}
        class="w-5 h-5 rounded-full border-2 transition-transform hover:scale-125"
        style="background: {c.bg}; border-color: {c.border}"
        title="Highlight {c.id}"
      ></button>
    {/each}
    <span class="text-[10px] text-zinc-500 ml-1 mr-0.5">Highlight</span>
  </div>
{/if}

<!-- Backdrop (mobile) -->
{#if app.readerOpen}
  <div
    class="fixed inset-0 bg-black/60 z-30 md:hidden animate-fade-in"
    onclick={() => app.closeReader()}
    role="presentation"
  ></div>
{/if}

<!-- Panel -->
<div
  data-testid="article-reader"
  class="fixed top-0 right-0 h-full w-full md:w-[600px] xl:w-[720px] bg-zinc-900 border-l border-zinc-800
         z-40 flex flex-col shadow-2xl transition-transform duration-250
         {app.readerOpen ? 'translate-x-0' : 'translate-x-full'}"
>
  <!-- Toolbar -->
  <div class="flex items-center justify-between px-4 py-3 border-b border-zinc-800 shrink-0">
    <div class="flex items-center gap-1">
      <button onclick={() => app.closeReader()} class="btn-ghost p-2" aria-label="Close">
        <X size={18} />
      </button>
      <button
        onclick={() => app.openPrevArticle()}
        disabled={!hasPrev}
        class="btn-ghost p-2 disabled:opacity-30 disabled:cursor-not-allowed"
        aria-label="Previous article"
        title="Previous article (←)"
      >
        <ChevronLeft size={18} />
      </button>
      <button
        onclick={() => app.openNextArticle()}
        disabled={!hasNext}
        class="btn-ghost p-2 disabled:opacity-30 disabled:cursor-not-allowed"
        aria-label="Next article"
        title="Next article (→)"
      >
        <ChevronRight size={18} />
      </button>
    </div>

    <div class="flex items-center gap-1 flex-wrap">
      {#if article}
        <!-- Thumbs up/down -->
        <button
          onclick={() => toggleSignal(1)}
          class="btn-ghost p-2 {userSignal === 1 ? 'text-emerald-400' : ''}"
          title="Like — boosts feed priority"
          aria-label="Like"
        >
          <ThumbsUp size={16} />
        </button>
        <button
          onclick={() => toggleSignal(-1)}
          class="btn-ghost p-2 {userSignal === -1 ? 'text-red-400' : ''}"
          title="Dislike — lowers feed priority"
          aria-label="Dislike"
        >
          <ThumbsDown size={16} />
        </button>

        <span class="w-px h-4 bg-zinc-700 mx-0.5"></span>

        <!-- Save for later -->
        <button
          onclick={toggleSaved}
          class="btn-ghost p-2 {article.is_saved ? 'text-violet-400' : ''}"
          aria-label={article.is_saved ? 'Remove from read later' : 'Read later'}
          title={article.is_saved ? 'Remove from read later' : 'Read later'}
        >
          <BookmarkPlus size={18} class={article.is_saved ? 'text-violet-400' : ''} />
        </button>

        <!-- Bookmark -->
        <button onclick={toggleBookmark} class="btn-ghost p-2" aria-label="Bookmark">
          {#if article.is_bookmarked}
            <BookmarkCheck size={18} class="text-amber-400" />
          {:else}
            <Bookmark size={18} />
          {/if}
        </button>

        <!-- AI Summary -->
        <button
          onclick={generateSummary}
          class="btn-ghost p-2 {article.summary ? 'text-violet-400' : ''}"
          disabled={summarizing}
          aria-label="AI Summary"
          title="Generate AI summary"
        >
          <Zap size={18} class={summarizing ? 'animate-pulse text-violet-400' : ''} />
        </button>

        <!-- Extract entities -->
        <button
          onclick={extractEntities}
          class="btn-ghost p-2 {entities.length > 0 ? 'text-cyan-400' : ''}"
          disabled={extractingEntities}
          aria-label="Extract entities"
          title="Detect people, orgs, places"
        >
          <Cpu size={18} class={extractingEntities ? 'animate-pulse text-cyan-400' : ''} />
        </button>

        <!-- Highlights panel toggle -->
        <button
          onclick={() => (highlightsOpen = !highlightsOpen)}
          class="btn-ghost p-2 {highlights.length > 0 ? 'text-amber-400' : ''}"
          aria-label="Highlights"
          title="Highlights ({highlights.length})"
        >
          <Highlighter size={18} />
        </button>

        <!-- Note -->
        <button
          onclick={() => (noteOpen = !noteOpen)}
          class="btn-ghost p-2 {article.note ? 'text-amber-400' : ''}"
          aria-label="Notes"
          title="Notes"
        >
          <StickyNote size={18} class={article.note ? 'text-amber-400' : ''} />
        </button>

        <!-- Tags -->
        <div class="relative">
          <button
            onclick={() => (tagsOpen = !tagsOpen)}
            class="btn-ghost p-2 {article.tags?.length ? 'text-violet-400' : ''}"
            aria-label="Tags"
            title="Tags"
          >
            <Tag size={18} />
          </button>
          {#if tagsOpen}
            <div class="absolute right-0 top-full mt-1 w-56 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl z-50 p-2">
              {#if article.tags?.length > 0}
                <p class="text-[10px] text-zinc-500 uppercase tracking-wider px-2 mb-1.5">Applied</p>
                <div class="flex flex-wrap gap-1 px-2 mb-2">
                  {#each article.tags as tag (tag.id)}
                    <button
                      onclick={() => removeTag(tag.id)}
                      class="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border transition-colors hover:opacity-70"
                      style="color: {tag.color}; border-color: {tag.color}40; background: {tag.color}15"
                    >
                      {tag.name} <X size={10} />
                    </button>
                  {/each}
                </div>
              {/if}
              {#if unattachedTags.length > 0}
                <p class="text-[10px] text-zinc-500 uppercase tracking-wider px-2 mb-1.5">Add tag</p>
                {#each unattachedTags as tag (tag.id)}
                  <button
                    onclick={() => addTag(tag)}
                    class="w-full flex items-center gap-2 px-2 py-1.5 rounded hover:bg-zinc-700 transition-colors text-left"
                  >
                    <span class="w-2 h-2 rounded-full shrink-0" style="background-color: {tag.color}"></span>
                    <span class="text-sm text-zinc-200">{tag.name}</span>
                  </button>
                {/each}
              {/if}
              {#if allTags.length === 0}
                <p class="text-xs text-zinc-500 px-2 py-1">No tags yet — create them in Settings.</p>
              {/if}
            </div>
          {/if}
        </div>

        {#if isReddit}
          <button
            onclick={loadComments}
            class="btn-ghost p-2 gap-1 text-xs {commentsOpen ? 'text-orange-400' : ''}"
            disabled={commentsLoading}
            aria-label="Load comments"
          >
            <MessageSquare size={18} />
            {commentsLoading ? '…' : article.comment_count != null ? fmtNum(article.comment_count) : 'Comments'}
          </button>
        {/if}

        <!-- Iframe mode toggle -->
        <button
          onclick={() => (iframeMode = !iframeMode)}
          class="btn-ghost p-2 {iframeMode ? 'text-violet-400' : ''}"
          aria-label="Original site"
          title={iframeMode ? 'Back to reader' : 'View original site'}
        >
          <Globe size={18} />
        </button>

        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          class="btn-ghost p-2"
          aria-label="Open original"
        >
          <ExternalLink size={18} />
        </a>
      {/if}
    </div>
  </div>

  <!-- Tags strip (applied tags shown inline) -->
  {#if article?.tags?.length > 0}
    <div class="flex items-center gap-1.5 px-5 py-2 border-b border-zinc-800/50 shrink-0">
      {#each article.tags as tag (tag.id)}
        <span
          class="text-xs px-2 py-0.5 rounded-full border"
          style="color: {tag.color}; border-color: {tag.color}40; background: {tag.color}15"
        >
          {tag.name}
        </span>
      {/each}
    </div>
  {/if}

  <!-- Iframe mode -->
  {#if iframeMode && article}
    <iframe
      src={article.url}
      title={article.title}
      class="flex-1 w-full border-0"
      sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox"
    ></iframe>
  {:else}
    <!-- Content -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="flex-1 overflow-y-auto" onmouseup={handleTextSelect}>
      {#if loading}
        <div class="flex items-center justify-center h-40 text-zinc-500">
          Loading…
        </div>
      {:else if article}
        <article class="px-6 py-8 max-w-2xl mx-auto">
          <!-- Meta -->
          <div class="flex flex-wrap items-center gap-2 text-xs text-zinc-500 mb-4">
            {#if isReddit}
              <span class="text-orange-400 font-semibold uppercase tracking-wide">Reddit</span>
              <span class="text-zinc-700">·</span>
            {/if}
            <span>{article.feed_title || 'Unknown source'}</span>
            {#if article.author}
              <span class="text-zinc-700">·</span>
              <span>{article.author}</span>
            {/if}
            {#if article.published_at}
              <span class="text-zinc-700">·</span>
              <span>{formatDate(article.published_at)}</span>
            {/if}
            {#if isReddit && article.score != null}
              <span class="text-zinc-700">·</span>
              <span class="flex items-center gap-0.5 text-orange-400/80">
                <ArrowUp size={12} />{fmtNum(article.score)}
              </span>
            {/if}
            {#if isReddit && article.comment_count != null}
              <span class="flex items-center gap-0.5 text-zinc-400">
                <MessageSquare size={11} />{fmtNum(article.comment_count)}
              </span>
            {/if}
          </div>

          <!-- Title -->
          <h1 data-testid="reader-title" class="text-2xl font-bold text-zinc-50 leading-tight mb-6">
            {article.title}
          </h1>

          <!-- AI Summary (if generated) -->
          {#if article.summary}
            <div class="mb-6 p-4 rounded-lg bg-violet-950/30 border border-violet-800/40">
              <div class="flex items-center gap-2 mb-2">
                <Zap size={13} class="text-violet-400" />
                <span class="text-xs font-semibold text-violet-400 uppercase tracking-wider">AI Summary</span>
              </div>
              <div class="prose prose-invert prose-sm max-w-none
                          prose-p:text-zinc-300 prose-p:leading-relaxed prose-p:my-1
                          prose-headings:text-zinc-200 prose-headings:font-semibold
                          prose-strong:text-zinc-200 prose-li:text-zinc-300
                          prose-ul:my-1 prose-ol:my-1">
                {@html sanitize(marked(article.summary))}
              </div>
            </div>
          {:else if summarizing}
            <div class="mb-6 p-4 rounded-lg bg-violet-950/20 border border-violet-800/30 animate-pulse">
              <div class="flex items-center gap-2">
                <Zap size={13} class="text-violet-400" />
                <span class="text-xs text-violet-400">Generating summary…</span>
              </div>
            </div>
          {/if}

          <!-- Entities panel -->
          {#if entitiesOpen && entities.length > 0}
            <div class="mb-6 p-4 rounded-lg bg-zinc-800/40 border border-zinc-700/40">
              <div class="flex items-center gap-2 mb-3">
                <Cpu size={13} class="text-cyan-400" />
                <span class="text-xs font-semibold text-cyan-400 uppercase tracking-wider">Detected Entities</span>
              </div>
              <div class="flex flex-wrap gap-1.5">
                {#each entities as entity (entity.id)}
                  {@const c = entityColors(entity.entity_type)}
                  <span class="text-xs px-2 py-0.5 rounded-full border {c.bg} {c.text} {c.border}">
                    <span class="opacity-60 mr-1">{entity.entity_type}</span>{entity.name}
                  </span>
                {/each}
              </div>
            </div>
          {:else if extractingEntities}
            <div class="mb-6 p-4 rounded-lg bg-zinc-800/30 border border-zinc-700/30 animate-pulse">
              <div class="flex items-center gap-2">
                <Cpu size={13} class="text-cyan-400" />
                <span class="text-xs text-cyan-400">Detecting entities…</span>
              </div>
            </div>
          {/if}

          <!-- Note panel -->
          {#if noteOpen}
            <div class="mb-6 p-4 rounded-lg bg-amber-950/20 border border-amber-800/30">
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <StickyNote size={13} class="text-amber-400" />
                  <span class="text-xs font-semibold text-amber-400 uppercase tracking-wider">Note</span>
                </div>
              </div>
              {#if noteEditing}
                <textarea
                  class="w-full bg-zinc-800/60 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-200
                         placeholder-zinc-600 resize-none focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                  rows="4"
                  placeholder="Write a note…"
                  bind:value={noteValue}
                  onkeydown={(e) => { if (e.key === 'Enter' && e.ctrlKey) saveNote(); }}
                ></textarea>
                <div class="flex gap-2 mt-2">
                  <button onclick={saveNote} disabled={noteSaving} class="btn-primary text-xs py-1">
                    {noteSaving ? 'Saving…' : 'Save'}
                  </button>
                  <button onclick={() => { noteEditing = false; noteValue = article.note || ''; }} class="btn-ghost text-xs py-1">
                    Cancel
                  </button>
                </div>
              {:else}
                <button
                  class="w-full text-left text-sm leading-relaxed whitespace-pre-wrap cursor-pointer transition-colors min-h-[2rem]
                         {article.note ? 'text-zinc-300 hover:text-zinc-100' : 'text-zinc-600 italic hover:text-zinc-500'}"
                  onclick={() => (noteEditing = true)}
                >
                  {article.note || 'Click to add a note…'}
                </button>
              {/if}
            </div>
          {/if}

          <!-- Podcast player -->
          {#if article.audio_url}
            <div class="mb-6">
              <audio controls class="w-full rounded-lg" src={article.audio_url}>
                Your browser does not support audio.
              </audio>
            </div>
          {/if}

          <!-- Body -->
          {#if article.full_content}
            <div class="article-content select-text">
              {@html sanitize(article.full_content)}
            </div>
          {:else if article.excerpt}
            <p class="text-zinc-400 leading-relaxed italic">{article.excerpt}</p>
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-2 mt-4 text-violet-400 hover:text-violet-300 text-sm"
            >
              Read full article <ExternalLink size={14} />
            </a>
          {/if}

          <!-- Highlights panel -->
          {#if highlightsOpen}
            <div class="mt-8 pt-6 border-t border-zinc-800">
              <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-2">
                  <Highlighter size={13} class="text-amber-400" />
                  <span class="text-xs font-semibold text-amber-400 uppercase tracking-wider">
                    Highlights ({highlights.length})
                  </span>
                </div>
                {#if highlights.length === 0}
                  <span class="text-xs text-zinc-600">Select text in the article to highlight</span>
                {/if}
              </div>
              <div class="space-y-2">
                {#each highlights as h (h.id)}
                  {@const colorMap = { yellow: '#fef08a', green: '#bbf7d0', blue: '#bae6fd', pink: '#fbcfe8' }}
                  <div
                    class="p-3 rounded-lg border-l-4 bg-zinc-800/40"
                    style="border-color: {colorMap[h.color] ?? '#fef08a'}"
                  >
                    <p class="text-sm text-zinc-200 leading-relaxed">"{h.text}"</p>
                    {#if h.note}
                      <p class="text-xs text-zinc-400 mt-1 italic">{h.note}</p>
                    {/if}
                    <button
                      onclick={() => deleteHighlight(h.id)}
                      class="text-[10px] text-zinc-600 hover:text-red-400 transition-colors mt-1"
                    >
                      Delete
                    </button>
                  </div>
                {/each}
              </div>
            </div>
          {/if}

          <!-- Comments -->
          {#if commentsOpen && comments.length > 0}
            <div class="mt-10 pt-8 border-t border-zinc-800">
              <div class="flex items-center gap-3 mb-4">
                <h2 class="text-sm font-semibold text-zinc-400 uppercase tracking-wide">
                  Comments ({comments.length})
                </h2>
                {#if isReddit && article.score != null}
                  <span class="flex items-center gap-1 text-xs text-orange-400/80">
                    <ArrowUp size={12} />{fmtNum(article.score)} points
                  </span>
                {/if}
              </div>
              <CommentThread {comments} />
            </div>
          {:else if commentsOpen && commentsLoading}
            <div class="mt-10 pt-8 border-t border-zinc-800">
              <p class="text-sm text-zinc-500 animate-pulse">Loading comments…</p>
            </div>
          {/if}
        </article>
      {/if}
    </div>
  {/if}
</div>
