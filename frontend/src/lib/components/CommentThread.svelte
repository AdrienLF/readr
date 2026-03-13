<script>
  import { formatDistanceToNow } from 'date-fns';

  let { comments = [] } = $props();

  const MAX_DEPTH = 3;

  function timeAgo(utc) {
    try {
      return formatDistanceToNow(new Date(utc * 1000), { addSuffix: true });
    } catch {
      return '';
    }
  }

  // Flatten the recursive comment tree into a single array with depth info.
  // This avoids recursive Svelte components which are expensive to mount/destroy.
  function flatten(nodes, depth = 0) {
    const result = [];
    for (const c of nodes) {
      result.push({ ...c, _depth: depth });
      if (c.replies?.length && depth < MAX_DEPTH) {
        result.push(...flatten(c.replies, depth + 1));
      } else if (c.replies?.length && depth >= MAX_DEPTH) {
        result.push({ _collapsed: true, _depth: depth + 1, _count: c.replies.length, id: c.id + '_more' });
      }
    }
    return result;
  }

  let flat = $derived(flatten(comments));
</script>

{#each flat as item (item.id)}
  {#if item._collapsed}
    <div style="padding-left: {item._depth * 1.25}rem" class="py-1">
      <span class="text-xs text-violet-400">
        {item._count} more {item._count === 1 ? 'reply' : 'replies'}
      </span>
    </div>
  {:else}
    <div
      style="padding-left: {item._depth * 1.25}rem"
      class={item._depth > 0 ? 'border-l border-zinc-800' : ''}
    >
      <div class="py-2 pl-3">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-semibold text-violet-400">{item.author}</span>
          <span class="text-xs text-zinc-600">{timeAgo(item.created_utc)}</span>
          <span class="text-xs text-zinc-500 ml-auto">{item.score} pts</span>
        </div>
        <p class="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">{item.body}</p>
      </div>
    </div>
  {/if}
{/each}
