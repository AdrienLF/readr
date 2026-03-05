<script>
  import { formatDistanceToNow } from 'date-fns';
  import { Bookmark, BookmarkCheck } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import { articles as articlesApi } from '$lib/api.js';

  let { article, onUpdate, density = 'card' } = $props();

  function timeAgo(date) {
    if (!date) return '';
    try {
      return formatDistanceToNow(new Date(date), { addSuffix: true });
    } catch {
      return '';
    }
  }

  async function toggleBookmark(e) {
    e.stopPropagation();
    const updated = await articlesApi.toggleBookmark(article.id);
    onUpdate?.({ ...article, is_bookmarked: updated.is_bookmarked });
  }

  function open() {
    app.openArticle(article.id);
    if (!article.is_read) {
      articlesApi.markRead(article.id);
      onUpdate?.({ ...article, is_read: true });
    }
  }
</script>

{#if density === 'list'}
  <!-- Compact list row -->
  <div
    role="button"
    tabindex="0"
    data-testid="article-card"
    onclick={open}
    onkeydown={(e) => e.key === 'Enter' && open()}
    class="group flex items-center gap-3 px-4 py-2.5 border-b border-zinc-800/40
           hover:bg-zinc-900/60 cursor-pointer transition-colors
           {article.is_read ? 'opacity-50' : ''}"
  >
    <div class="w-1.5 h-1.5 rounded-full shrink-0 {article.is_read ? 'bg-transparent' : 'bg-violet-500'}"></div>
    <span class="text-xs text-zinc-500 w-32 shrink-0 truncate">{article.feed_title || '—'}</span>
    <span class="flex-1 text-sm text-zinc-200 truncate group-hover:text-violet-300 transition-colors font-medium">
      {article.title}
    </span>
    {#if article.author}
      <span class="text-xs text-zinc-600 w-24 shrink-0 truncate hidden lg:block">{article.author}</span>
    {/if}
    <span class="text-xs text-zinc-600 w-20 shrink-0 text-right hidden sm:block">{timeAgo(article.published_at)}</span>
    <button
      onclick={toggleBookmark}
      class="text-zinc-700 hover:text-amber-400 transition-colors p-1 rounded shrink-0"
      aria-label="Toggle bookmark"
    >
      {#if article.is_bookmarked}
        <BookmarkCheck size={13} class="text-amber-400" />
      {:else}
        <Bookmark size={13} />
      {/if}
    </button>
  </div>

{:else if density === 'grid'}
  <!-- Grid card — no image, compact -->
  <div
    role="button"
    tabindex="0"
    data-testid="article-card"
    onclick={open}
    onkeydown={(e) => e.key === 'Enter' && open()}
    class="group relative w-full text-left card hover:border-zinc-700 transition-all duration-200
           cursor-pointer p-3 {article.is_read ? 'opacity-60' : ''}"
  >
    {#if !article.is_read}
      <div class="absolute top-3 right-3 w-1.5 h-1.5 rounded-full bg-violet-500 pointer-events-none"></div>
    {/if}
    <div class="flex items-center gap-1.5 mb-1.5">
      {#if article.feed_source_type === 'reddit'}
        <span class="text-orange-400 text-xs font-semibold">r/</span>
      {/if}
      <span class="text-zinc-500 text-xs truncate">{article.feed_title || 'Unknown'}</span>
      <span class="text-zinc-700 text-xs ml-auto shrink-0">{timeAgo(article.published_at)}</span>
    </div>
    <h3 class="text-sm font-semibold text-zinc-100 leading-snug line-clamp-3 group-hover:text-violet-300 transition-colors mb-2">
      {article.title}
    </h3>
    {#if article.excerpt}
      <p class="text-xs text-zinc-500 line-clamp-1 leading-relaxed">{article.excerpt}</p>
    {/if}
    <div class="flex items-center justify-between mt-2">
      <span class="text-xs text-zinc-600 truncate">{article.author || ''}</span>
      <button
        onclick={toggleBookmark}
        class="text-zinc-600 hover:text-amber-400 transition-colors p-1 rounded shrink-0"
        aria-label="Toggle bookmark"
      >
        {#if article.is_bookmarked}
          <BookmarkCheck size={13} class="text-amber-400" />
        {:else}
          <Bookmark size={13} />
        {/if}
      </button>
    </div>
  </div>

{:else}
  <!-- Full card with image (default: 'card') -->
  <div
    role="button"
    tabindex="0"
    data-testid="article-card"
    onclick={open}
    onkeydown={(e) => e.key === 'Enter' && open()}
    class="group relative w-full text-left card hover:border-zinc-700 transition-all duration-200
           overflow-hidden cursor-pointer {article.is_read ? 'opacity-60' : ''}"
  >
    {#if article.image_url}
      <div class="aspect-video w-full overflow-hidden bg-zinc-800">
        <img
          src={article.image_url}
          alt=""
          class="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-300"
          loading="lazy"
          onerror={(e) => e.currentTarget.parentElement.remove()}
        />
      </div>
    {/if}

    <div class="p-4">
      <div class="flex items-center gap-2 mb-2">
        {#if article.feed_source_type === 'reddit'}
          <span class="text-orange-400 text-xs font-semibold uppercase tracking-wide">Reddit</span>
        {/if}
        <span class="text-zinc-500 text-xs truncate">{article.feed_title || 'Unknown'}</span>
        <span class="text-zinc-700 text-xs ml-auto shrink-0">{timeAgo(article.published_at)}</span>
      </div>

      <h3 class="text-sm font-semibold text-zinc-100 leading-snug line-clamp-2 mb-2 group-hover:text-violet-300 transition-colors">
        {article.title}
      </h3>

      {#if article.excerpt}
        <p class="text-xs text-zinc-500 line-clamp-2 leading-relaxed">{article.excerpt}</p>
      {/if}

      <div class="flex items-center justify-between mt-3">
        <span class="text-xs text-zinc-600">{article.author || ''}</span>
        <button
          onclick={toggleBookmark}
          class="text-zinc-600 hover:text-amber-400 transition-colors p-1 rounded"
          aria-label="Toggle bookmark"
        >
          {#if article.is_bookmarked}
            <BookmarkCheck size={14} class="text-amber-400" />
          {:else}
            <Bookmark size={14} />
          {/if}
        </button>
      </div>
    </div>

    {#if !article.is_read}
      <div class="absolute top-3 left-3 w-2 h-2 rounded-full bg-violet-500 pointer-events-none"></div>
    {/if}
  </div>
{/if}
