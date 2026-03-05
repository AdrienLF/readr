<script>
  import { X } from 'lucide-svelte';
  import { app } from '$lib/stores/app.svelte.js';

  const sections = [
    {
      title: 'Navigation',
      shortcuts: [
        { keys: ['j'], desc: 'Next article' },
        { keys: ['k'], desc: 'Previous article' },
        { keys: ['o', '↵'], desc: 'Open focused article' },
        { keys: ['Esc'], desc: 'Close reader / this overlay' },
      ],
    },
    {
      title: 'Actions',
      shortcuts: [
        { keys: ['b'], desc: 'Toggle bookmark' },
        { keys: ['u'], desc: 'Toggle read/unread' },
        { keys: ['r'], desc: 'Refresh articles' },
      ],
    },
    {
      title: 'App',
      shortcuts: [
        { keys: ['?'], desc: 'Show / hide this overlay' },
      ],
    },
  ];
</script>

{#if app.shortcutsVisible}
  <div
    class="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 animate-fade-in"
    onclick={(e) => e.target === e.currentTarget && (app.shortcutsVisible = false)}
    role="dialog"
    aria-modal="true"
    aria-label="Keyboard shortcuts"
    tabindex="-1"
  >
    <div class="card w-full max-w-md p-6 animate-slide-in-up">
      <div class="flex items-center justify-between mb-5">
        <h2 class="text-base font-semibold">Keyboard Shortcuts</h2>
        <button onclick={() => (app.shortcutsVisible = false)} class="btn-ghost p-1">
          <X size={16} />
        </button>
      </div>

      <div class="space-y-5">
        {#each sections as section}
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-widest text-zinc-500 mb-2">
              {section.title}
            </p>
            <div class="space-y-1.5">
              {#each section.shortcuts as s}
                <div class="flex items-center justify-between">
                  <span class="text-sm text-zinc-300">{s.desc}</span>
                  <div class="flex items-center gap-1">
                    {#each s.keys as key, i}
                      {#if i > 0}<span class="text-zinc-600 text-xs">or</span>{/if}
                      <kbd class="px-2 py-0.5 text-xs font-mono bg-zinc-800 border border-zinc-700 rounded text-zinc-300">{key}</kbd>
                    {/each}
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/each}
      </div>

      <p class="text-xs text-zinc-600 mt-5">Shortcuts are disabled when typing in input fields.</p>
    </div>
  </div>
{/if}
