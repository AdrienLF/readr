<script>
  import '../app.css';
  import { onMount } from 'svelte';
  import { Menu, X } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';
  import Sidebar from '$lib/components/Sidebar.svelte';
  import ArticleReader from '$lib/components/ArticleReader.svelte';
  import AddFeedModal from '$lib/components/AddFeedModal.svelte';
  import TopicModal from '$lib/components/TopicModal.svelte';
  import MobileNav from '$lib/components/MobileNav.svelte';
  import KeyboardHelp from '$lib/components/KeyboardHelp.svelte';

  function handleGlobalKey(e) {
    const tag = e.target?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target?.isContentEditable) return;
    if (e.key === '?') { e.preventDefault(); app.shortcutsVisible = !app.shortcutsVisible; }
    if (e.key === 'Escape') {
      if (app.shortcutsVisible) app.shortcutsVisible = false;
      else if (app.readerOpen) app.closeReader();
    }
  }

  let { children } = $props();

  onMount(() => {
    app.init();
    // Close sidebar by default on mobile
    if (window.innerWidth < 768) {
      app.sidebarOpen = false;
    }
  });
</script>

<svelte:window onkeydown={handleGlobalKey} />

<div class="flex h-screen overflow-hidden bg-zinc-950">
  <!-- Mobile sidebar backdrop -->
  {#if app.sidebarOpen}
    <div
      class="fixed inset-0 bg-black/50 z-10 md:hidden"
      onclick={() => (app.sidebarOpen = false)}
      role="presentation"
    ></div>
  {/if}

  <Sidebar />

  <!-- Main area -->
  <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
    <!-- Mobile topbar -->
    <div class="md:hidden flex items-center gap-3 px-4 py-3 border-b border-zinc-800 shrink-0">
      <button
        onclick={() => (app.sidebarOpen = !app.sidebarOpen)}
        class="btn-ghost p-2"
        aria-label="Toggle sidebar"
      >
        {#if app.sidebarOpen}
          <X size={18} />
        {:else}
          <Menu size={18} />
        {/if}
      </button>
      <span class="font-semibold text-sm">
        {#if app.selectedTopicId !== null}
          {app.topics.find((t) => t.id === app.selectedTopicId)?.name || 'Topic'}
        {:else if app.activeView === 'bookmarks'}
          Bookmarks
        {:else if app.activeView === 'search'}
          Search
        {:else if app.activeView === 'digest'}
          Digest
        {:else if app.activeView === 'settings'}
          Settings
        {:else}
          All Articles
        {/if}
      </span>
    </div>

    <!-- Page content -->
    <div class="flex-1 overflow-hidden pb-16 md:pb-0">
      {@render children()}
    </div>
  </div>

  <!-- Article reader panel -->
  <ArticleReader />

  <!-- Modals -->
  <AddFeedModal />
  <TopicModal />

  <!-- Mobile bottom nav -->
  <MobileNav />

  <!-- Keyboard help overlay -->
  <KeyboardHelp />
</div>
