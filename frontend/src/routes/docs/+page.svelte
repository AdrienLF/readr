<script>
  import { app } from '$lib/stores/app.svelte.js';
  import { BookOpen, Rss, Keyboard, Filter, Download, Zap, Youtube, Headphones, Globe, Tag } from 'lucide-svelte';

  app.activeView = 'docs';

  const sections = [
    { id: 'getting-started', label: 'Getting Started' },
    { id: 'adding-feeds',    label: 'Adding Feeds' },
    { id: 'bulk-import',     label: 'Bulk Import' },
    { id: 'feed-formats',    label: 'Feed URL Formats' },
    { id: 'keyboard',        label: 'Keyboard Shortcuts' },
    { id: 'organization',    label: 'Topics & Organization' },
    { id: 'filters',         label: 'Mute Filters' },
    { id: 'opml',            label: 'OPML Import / Export' },
    { id: 'ai',              label: 'AI Digest & Summary' },
    { id: 'tags-rules',      label: 'Tags & Rules' },
    { id: 'settings',        label: 'Settings Reference' },
  ];

  let active = $state('getting-started');

  function scrollTo(id) {
    active = id;
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  const shortcuts = [
    { key: 'j',       desc: 'Focus next article' },
    { key: 'k',       desc: 'Focus previous article' },
    { key: 'o / ↵',  desc: 'Open focused article in reader' },
    { key: 'b',       desc: 'Toggle bookmark on focused article' },
    { key: 'u',       desc: 'Toggle read / unread on focused article' },
    { key: 'r',       desc: 'Refresh current article list' },
    { key: '?',       desc: 'Show / hide keyboard shortcuts overlay' },
    { key: 'Esc',     desc: 'Close reader panel or overlay' },
  ];
</script>

<svelte:head>
  <title>Docs · Readr</title>
</svelte:head>

<div class="flex h-full overflow-hidden">
  <!-- Sidebar TOC -->
  <nav class="hidden lg:flex flex-col w-52 shrink-0 border-r border-zinc-800/60 py-6 px-3 overflow-y-auto">
    <p class="text-[11px] font-semibold uppercase tracking-widest text-zinc-500 px-3 mb-3">Contents</p>
    {#each sections as s}
      <button
        onclick={() => scrollTo(s.id)}
        class="text-left text-sm px-3 py-1.5 rounded-lg transition-colors
               {active === s.id ? 'bg-violet-500/10 text-violet-300' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40'}"
      >
        {s.label}
      </button>
    {/each}
  </nav>

  <!-- Content -->
  <div class="flex-1 overflow-y-auto px-6 py-8">
    <div class="max-w-2xl mx-auto space-y-12">

      <div class="flex items-center gap-3">
        <BookOpen size={24} class="text-violet-400 shrink-0" />
        <div>
          <h1 class="text-2xl font-bold text-zinc-100">Readr Documentation</h1>
          <p class="text-sm text-zinc-500 mt-0.5">Self-hosted RSS reader with AI digest and full-text extraction.</p>
        </div>
      </div>

      <!-- Getting Started -->
      <section id="getting-started">
        <h2 class="text-base font-semibold text-zinc-200 mb-4 flex items-center gap-2">
          <Rss size={16} class="text-violet-400" /> Getting Started
        </h2>
        <div class="space-y-3 text-sm text-zinc-400 leading-relaxed">
          <p>Readr is a self-hosted RSS reader. Once running, open it in your browser at <code class="text-violet-300 bg-zinc-800/60 px-1 rounded">http://localhost</code> (or your Tailscale address).</p>
          <ol class="list-decimal list-inside space-y-2 ml-1">
            <li>Click <strong class="text-zinc-300">Add Feed</strong> in the sidebar to subscribe to your first feed.</li>
            <li>Optionally create <strong class="text-zinc-300">Topics</strong> to group your feeds by theme.</li>
            <li>Articles are fetched automatically every hour (configurable in Settings).</li>
            <li>Click any article to open the full-text reader. Use <kbd class="kbd">j/k</kbd> to navigate.</li>
          </ol>
        </div>
      </section>

      <!-- Adding Feeds -->
      <section id="adding-feeds">
        <h2 class="text-base font-semibold text-zinc-200 mb-4 flex items-center gap-2">
          <Globe size={16} class="text-violet-400" /> Adding Feeds
        </h2>
        <div class="space-y-3 text-sm text-zinc-400 leading-relaxed">
          <p>Paste any URL into the <strong class="text-zinc-300">Add Feed</strong> dialog. Readr will auto-detect whether it's a direct RSS/Atom feed or a regular website (in which case it scans the page for a feed link).</p>
          <p>You can assign one or more Topics at the time of adding a feed, or create a new topic inline by typing a name and pressing Enter.</p>
          <div class="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 space-y-1.5">
            <p class="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">What's supported</p>
            <div class="grid grid-cols-2 gap-1 text-xs">
              <span class="text-zinc-300">✓ RSS 2.0 / Atom</span>
              <span class="text-zinc-300">✓ Reddit subreddits</span>
              <span class="text-zinc-300">✓ YouTube channels</span>
              <span class="text-zinc-300">✓ Bluesky accounts</span>
              <span class="text-zinc-300">✓ Podcasts</span>
              <span class="text-zinc-300">✓ Any site with a feed link</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Bulk Import -->
      <section id="bulk-import">
        <h2 class="text-base font-semibold text-zinc-200 mb-4 flex items-center gap-2">
          <Zap size={16} class="text-violet-400" /> Bulk Import
        </h2>
        <div class="space-y-3 text-sm text-zinc-400 leading-relaxed">
          <p>Click the <strong class="text-zinc-300">upload icon</strong> next to the Add Feed button in the sidebar to open the Bulk Import modal.</p>
          <ol class="list-decimal list-inside space-y-2 ml-1">
            <li>Paste a list of feed URLs — or any text containing URLs (e.g. a ChatGPT recommendation). URLs are extracted automatically.</li>
            <li>Click <strong class="text-zinc-300">Classify with AI</strong>. The local LLM discovers each feed's metadata and assigns it to a topic, preferring existing topics and creating new ones when needed.</li>
            <li>Review the proposed classification. You can reassign feeds to different topics using the dropdown, or remove feeds you don't want.</li>
            <li>Click <strong class="text-zinc-300">Import</strong> to create all feeds and topics at once. Articles are fetched in the background.</li>
          </ol>
          <p>Feeds that already exist in your library are shown as <em class="text-zinc-500">(exists)</em> and skipped during import.</p>
        </div>
      </section>

      <!-- Feed URL Formats -->
      <section id="feed-formats">
        <h2 class="text-base font-semibold text-zinc-200 mb-4 flex items-center gap-2">
          <Youtube size={16} class="text-violet-400" /> Feed URL Formats
        </h2>
        <div class="space-y-4 text-sm text-zinc-400">

          <div>
            <p class="text-zinc-300 font-medium mb-1.5">Reddit subreddits</p>
            <code class="block bg-zinc-900/70 border border-zinc-800 rounded px-3 py-2 text-xs text-violet-300">https://www.reddit.com/r/programming</code>
            <p class="text-xs mt-1">Paste the subreddit URL directly — Readr appends <code class="text-zinc-400">.rss</code> automatically.</p>
          </div>

          <div>
            <p class="text-zinc-300 font-medium mb-1.5">YouTube channels</p>
            <code class="block bg-zinc-900/70 border border-zinc-800 rounded px-3 py-2 text-xs text-violet-300">https://www.youtube.com/feeds/videos.xml?channel_id=UC_CHANNEL_ID</code>
            <p class="text-xs mt-1">Find your channel ID in YouTube Studio → Settings → Channel → Advanced Settings.</p>
          </div>

          <div>
            <p class="text-zinc-300 font-medium mb-1.5">Bluesky accounts (via RSSHub)</p>
            <code class="block bg-zinc-900/70 border border-zinc-800 rounded px-3 py-2 text-xs text-violet-300">http://rsshub:1200/bluesky/profile/handle.bsky.social</code>
            <p class="text-xs mt-1">RSSHub is bundled with Readr and accessible internally. Replace <code class="text-zinc-400">handle</code> with the account handle.</p>
          </div>

          <div>
            <p class="text-zinc-300 font-medium mb-1.5">Podcasts</p>
            <p class="text-xs">Paste any podcast RSS feed URL. Readr detects audio enclosures and shows a <span class="text-violet-400 font-semibold">PODCAST</span> badge on episodes. A mini audio player appears in the article reader.</p>
          </div>
        </div>
      </section>

      <!-- Keyboard Shortcuts -->
      <section id="keyboard">
        <h2 class="text-base font-semibold text-zinc-200 mb-4 flex items-center gap-2">
          <Keyboard size={16} class="text-violet-400" /> Keyboard Shortcuts
        </h2>
        <p class="text-sm text-zinc-500 mb-4">Press <kbd class="kbd">?</kbd> anywhere to show the shortcuts overlay. Shortcuts are disabled when focus is in an input field.</p>
        <div class="border border-zinc-800 rounded-lg overflow-hidden">
          {#each shortcuts as s, i}
            <div class="flex items-center justify-between px-4 py-2.5 {i % 2 === 0 ? 'bg-zinc-900/30' : ''}">
              <span class="text-sm text-zinc-300">{s.desc}</span>
              <kbd class="px-2.5 py-1 text-xs font-mono bg-zinc-800 border border-zinc-700 rounded text-zinc-300">{s.key}</kbd>
            </div>
          {/each}
        </div>
      </section>

      <!-- Organization -->
      <section id="organization">
        <h2 class="text-base font-semibold text-zinc-200 mb-4">Topics &amp; Organization</h2>
        <div class="space-y-3 text-sm text-zinc-400 leading-relaxed">
          <p>Topics are colored groups that feeds can belong to. A feed can belong to multiple topics (many-to-many).</p>
          <ul class="list-disc list-inside space-y-1.5 ml-1">
            <li>Create topics from the <strong class="text-zinc-300">+</strong> button in the sidebar, or inline when adding a feed.</li>
            <li>Assign topics when adding a feed, or update them later in Settings → Feeds. The Bulk Import feature can also auto-create topics via AI classification.</li>
            <li>Click a topic in the sidebar to see all articles from its feeds.</li>
            <li>Click the chevron <strong class="text-zinc-300">›</strong> next to a topic to expand it and browse individual feeds.</li>
          </ul>
          <p>Feeds not assigned to any topic appear in the <strong class="text-zinc-300">Feeds</strong> section at the bottom of the sidebar.</p>
        </div>
      </section>

      <!-- Mute Filters -->
      <section id="filters">
        <h2 class="text-base font-semibold text-zinc-200 mb-4 flex items-center gap-2">
          <Filter size={16} class="text-violet-400" /> Mute Filters
        </h2>
        <div class="space-y-3 text-sm text-zinc-400 leading-relaxed">
          <p>Mute filters silently drop articles whose title or excerpt matches a pattern <em>at fetch time</em>. Muted articles never enter your database.</p>
          <div class="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 space-y-2 text-xs">
            <p class="font-medium text-zinc-300">Examples</p>
            <div class="space-y-1.5 font-mono">
              <div><code class="text-violet-300">sponsored</code> <span class="text-zinc-500">— drops any article containing "sponsored"</span></div>
              <div><code class="text-violet-300">^Breaking News</code> <span class="text-zinc-500">— regex: drops articles starting with "Breaking News"</span></div>
              <div><code class="text-violet-300">\bNFT\b</code> <span class="text-zinc-500">— regex: whole-word match for "NFT"</span></div>
            </div>
          </div>
          <p>Filters can be <strong class="text-zinc-300">global</strong> (apply to all feeds) or scoped to a <strong class="text-zinc-300">specific feed</strong>. Manage them in Settings → Mute Filters.</p>
        </div>
      </section>

      <!-- OPML -->
      <section id="opml">
        <h2 class="text-base font-semibold text-zinc-200 mb-4 flex items-center gap-2">
          <Download size={16} class="text-violet-400" /> OPML Import / Export
        </h2>
        <div class="space-y-3 text-sm text-zinc-400 leading-relaxed">
          <p>OPML is the standard format for sharing feed lists. Readr supports both import and export from <strong class="text-zinc-300">Settings → Import / Export</strong>.</p>
          <ul class="list-disc list-inside space-y-1.5 ml-1">
            <li><strong class="text-zinc-300">Export</strong> — downloads <code class="text-zinc-400">readr-feeds.opml</code> with feeds grouped by their topics as OPML folders.</li>
            <li><strong class="text-zinc-300">Import</strong> — accepts any OPML file. OPML folders become Topics automatically. Duplicate feed URLs are skipped.</li>
          </ul>
          <p>Newly imported feeds are queued for an immediate article fetch in the background.</p>
        </div>
      </section>

      <!-- AI Digest & Summary -->
      <section id="ai">
        <h2 class="text-base font-semibold text-zinc-200 mb-4 flex items-center gap-2">
          <Zap size={16} class="text-violet-400" /> AI Digest &amp; Summary
        </h2>
        <div class="space-y-3 text-sm text-zinc-400 leading-relaxed">
          <p>Readr uses a local <a href="https://ollama.com" target="_blank" rel="noopener" class="text-violet-400 hover:underline">Ollama</a> instance for AI features. No data leaves your machine.</p>
          <p class="font-medium text-zinc-300">Daily Digest</p>
          <ul class="list-disc list-inside space-y-1.5 ml-1">
            <li>Generated daily at <strong class="text-zinc-300">07:00</strong> (configurable in Settings).</li>
            <li>Navigate to <strong class="text-zinc-300">Digest</strong> in the sidebar to read today's summary or trigger one on demand.</li>
            <li>Digests can be scoped to a specific Topic or cover all feeds.</li>
          </ul>
          <p class="font-medium text-zinc-300">Per-article Summary</p>
          <ul class="list-disc list-inside space-y-1.5 ml-1">
            <li>Open any article and click the <strong class="text-zinc-300">⚡ lightning</strong> button in the toolbar.</li>
            <li>The summary is generated once and cached — subsequent opens show it instantly.</li>
          </ul>
          <div class="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 text-xs space-y-2">
            <p class="font-medium text-zinc-300">Pulling a model manually</p>
            <code class="block text-violet-300">docker exec rss-reader-ollama-1 ollama pull qwen3:8b</code>
            <p class="text-zinc-500">The model must be pulled before Readr can generate digests or summaries.</p>
          </div>
        </div>
      </section>

      <!-- Tags & Rules -->
      <section id="tags-rules">
        <h2 class="text-base font-semibold text-zinc-200 mb-4 flex items-center gap-2">
          <Tag size={16} class="text-violet-400" /> Tags &amp; Rules
        </h2>
        <div class="space-y-4 text-sm text-zinc-400 leading-relaxed">
          <div>
            <p class="text-zinc-300 font-medium mb-1.5">Tags</p>
            <p>Tags are colored labels you can apply to articles for personal organization. Create them in <strong class="text-zinc-300">Settings → Tags</strong>, then apply them in the article reader toolbar.</p>
          </div>
          <div>
            <p class="text-zinc-300 font-medium mb-1.5">Notes</p>
            <p>Each article has a private note field. Click the <strong class="text-zinc-300">sticky-note</strong> icon in the reader toolbar to open the note editor. Notes are saved on your server and never leave.</p>
          </div>
          <div>
            <p class="text-zinc-300 font-medium mb-1.5">Read Later</p>
            <p>Click the <strong class="text-zinc-300">bookmark+</strong> icon to mark an article for reading later. These articles appear in the <strong class="text-zinc-300">Read Later</strong> sidebar section, separate from Bookmarks.</p>
          </div>
          <div>
            <p class="text-zinc-300 font-medium mb-1.5">Automation Rules</p>
            <p>Rules are evaluated at fetch time. When a new article matches the condition, the action is applied automatically. Create rules in <strong class="text-zinc-300">Settings → Automation Rules</strong>.</p>
            <div class="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 mt-2 space-y-2 text-xs">
              <p class="font-medium text-zinc-300">Examples</p>
              <div class="space-y-1.5 font-mono">
                <div><code class="text-violet-300">title contains "AI"</code> → <span class="text-zinc-400">Save for later</span></div>
                <div><code class="text-violet-300">author equals "John Doe"</code> → <span class="text-zinc-400">Bookmark</span></div>
                <div><code class="text-violet-300">title matches "\\bsponsored\\b"</code> → <span class="text-zinc-400">Mute (discard)</span></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Settings Reference -->
      <section id="settings">
        <h2 class="text-base font-semibold text-zinc-200 mb-4">Settings Reference</h2>
        <div class="border border-zinc-800 rounded-lg overflow-hidden text-sm">
          {#each [
            { key: 'Digest time',       val: 'Daily time (HH:MM) the AI digest is generated (default: 07:00).' },
            { key: 'Feed refresh interval', val: 'Seconds between automatic feed fetches (default: 3600 = 1 hour, min 300).' },
            { key: 'Ollama model',      val: 'Model name used for digest generation. Must be pulled in Ollama first.' },
          ] as row, i}
            <div class="flex gap-4 px-4 py-3 {i % 2 === 0 ? 'bg-zinc-900/30' : ''}">
              <span class="text-zinc-300 font-medium w-44 shrink-0">{row.key}</span>
              <span class="text-zinc-500">{row.val}</span>
            </div>
          {/each}
        </div>
      </section>

    </div>
  </div>
</div>

<style>
  .kbd {
    @apply px-1.5 py-0.5 text-xs font-mono bg-zinc-800 border border-zinc-700 rounded text-zinc-300;
  }
</style>
