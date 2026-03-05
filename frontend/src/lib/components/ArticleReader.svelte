<script>
  import { onMount } from 'svelte';
  import { format } from 'date-fns';
  import { X, ExternalLink, Bookmark, BookmarkCheck, BookmarkPlus, MessageSquare, Zap, Tag, StickyNote } from 'lucide-svelte';
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
    try {
      article = await articlesApi.get(id);
      noteValue = article.note || '';
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

  function formatDate(d) {
    if (!d) return '';
    try {
      return format(new Date(d), 'MMM d, yyyy · h:mm a');
    } catch {
      return '';
    }
  }

  let articleTagIds = $derived(new Set((article?.tags || []).map((t) => t.id)));
  let unattachedTags = $derived(allTags.filter((t) => !articleTagIds.has(t.id)));

  // Close on Escape
  function handleKeydown(e) {
    if (e.key === 'Escape') {
      if (noteEditing) { noteEditing = false; return; }
      if (tagsOpen) { tagsOpen = false; return; }
      app.closeReader();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

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
    <button onclick={() => app.closeReader()} class="btn-ghost p-2" aria-label="Close">
      <X size={18} />
    </button>

    <div class="flex items-center gap-1">
      {#if article}
        <!-- Save for later -->
        <button
          onclick={toggleSaved}
          class="btn-ghost p-2 {article.is_saved ? 'text-violet-400' : ''}"
          aria-label={article.is_saved ? 'Remove from saved' : 'Save for later'}
          title={article.is_saved ? 'Remove from saved' : 'Save for later'}
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
            <!-- Tags dropdown -->
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

        {#if article.feed_source_type === 'reddit'}
          <button
            onclick={loadComments}
            class="btn-ghost p-2 gap-1 text-xs {commentsOpen ? 'text-orange-400' : ''}"
            disabled={commentsLoading}
            aria-label="Load comments"
          >
            <MessageSquare size={18} />
            {commentsLoading ? '…' : 'Comments'}
          </button>
        {/if}

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

  <!-- Content -->
  <div class="flex-1 overflow-y-auto">
    {#if loading}
      <div class="flex items-center justify-center h-40 text-zinc-500">
        Loading…
      </div>
    {:else if article}
      <article class="px-6 py-8 max-w-2xl mx-auto">
        <!-- Meta -->
        <div class="flex flex-wrap items-center gap-2 text-xs text-zinc-500 mb-4">
          {#if article.feed_source_type === 'reddit'}
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
            <p class="text-sm text-zinc-300 leading-relaxed">{article.summary}</p>
          </div>
        {:else if summarizing}
          <div class="mb-6 p-4 rounded-lg bg-violet-950/20 border border-violet-800/30 animate-pulse">
            <div class="flex items-center gap-2">
              <Zap size={13} class="text-violet-400" />
              <span class="text-xs text-violet-400">Generating summary…</span>
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
          <div class="article-content">
            {@html article.full_content}
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

        <!-- Comments -->
        {#if commentsOpen && comments.length > 0}
          <div class="mt-10 pt-8 border-t border-zinc-800">
            <h2 class="text-sm font-semibold text-zinc-400 mb-4 uppercase tracking-wide">
              Comments ({comments.length})
            </h2>
            <CommentThread {comments} />
          </div>
        {/if}
      </article>
    {/if}
  </div>
</div>
