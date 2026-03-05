<script>
  import { formatDistanceToNow } from 'date-fns';
  import CommentThread from './CommentThread.svelte';

  let { comments = [], depth = 0 } = $props();

  function timeAgo(utc) {
    try {
      return formatDistanceToNow(new Date(utc * 1000), { addSuffix: true });
    } catch {
      return '';
    }
  }

  const MAX_VISIBLE_DEPTH = 3;
</script>

{#each comments as comment (comment.id)}
  <div class="group {depth > 0 ? 'ml-4 border-l border-zinc-800 pl-3' : ''}">
    <div class="py-2">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-xs font-semibold text-violet-400">{comment.author}</span>
        <span class="text-xs text-zinc-600">{timeAgo(comment.created_utc)}</span>
        <span class="text-xs text-zinc-500 ml-auto">{comment.score} pts</span>
      </div>
      <p class="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">{comment.body}</p>
    </div>

    {#if comment.replies?.length && depth < MAX_VISIBLE_DEPTH}
      <CommentThread comments={comment.replies} depth={depth + 1} />
    {:else if comment.replies?.length && depth >= MAX_VISIBLE_DEPTH}
      <button class="text-xs text-violet-400 hover:text-violet-300 ml-4 mt-1">
        {comment.replies.length} more {comment.replies.length === 1 ? 'reply' : 'replies'}
      </button>
    {/if}
  </div>
{/each}
