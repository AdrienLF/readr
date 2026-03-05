<script>
  import { Home, Bookmark, Search, Zap, Settings } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';

  const TABS = [
    { id: 'feed', icon: Home, label: 'Home', path: '/' },
    { id: 'search', icon: Search, label: 'Search', path: '/search' },
    { id: 'digest', icon: Zap, label: 'Digest', path: '/digest' },
    { id: 'bookmarks', icon: Bookmark, label: 'Saved', path: '/bookmarks' },
    { id: 'settings', icon: Settings, label: 'Settings', path: '/settings' },
  ];
</script>

<!-- Only visible on mobile -->
<nav class="fixed bottom-0 left-0 right-0 z-30 md:hidden bg-zinc-900/95 backdrop-blur border-t border-zinc-800 px-2 pb-safe">
  <div class="flex items-center justify-around">
    {#each TABS as tab}
      <a
        href={tab.path}
        onclick={() => (app.activeView = tab.id)}
        class="flex flex-col items-center gap-1 px-3 py-2.5 text-xs transition-colors
               {app.activeView === tab.id ? 'text-violet-400' : 'text-zinc-500'}"
      >
        <svelte:component this={tab.icon} size={20} />
        <span>{tab.label}</span>
      </a>
    {/each}
  </div>
</nav>
