<script>
  import { onMount } from 'svelte';
  import { formatDistanceToNow, format } from 'date-fns';
  import { X, ExternalLink, Bookmark, BookmarkCheck, MessageSquare, ChevronDown } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import { articles as articlesApi } from '$lib/api.js';
  import CommentThread from './CommentThread.svelte';

  let article = $state(null);
  let comments = $state([]);
  let commentsLoading = $state(false);
  let commentsOpen = $state(false);
  let loading = $state(false);

  $effect(() => {
    if (app.selectedArticleId) {
      loadArticle(app.selectedArticleId);
    }
  });

  async function loadArticle(id) {
    loading = true;
    comments = [];
    commentsOpen = false;
    try {
      article = await articlesApi.get(id);
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

  function formatDate(d) {
    if (!d) return '';
    try {
      return format(new Date(d), 'MMM d, yyyy · h:mm a');
    } catch {
      return '';
    }
  }

  // Close on Escape
  function handleKeydown(e) {
    if (e.key === 'Escape') app.closeReader();
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

    <div class="flex items-center gap-2">
      {#if article}
        <button onclick={toggleBookmark} class="btn-ghost p-2" aria-label="Bookmark">
          {#if article.is_bookmarked}
            <BookmarkCheck size={18} class="text-amber-400" />
          {:else}
            <Bookmark size={18} />
          {/if}
        </button>

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
