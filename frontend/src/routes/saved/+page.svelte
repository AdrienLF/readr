<script>
  import ArticleList from '$lib/components/ArticleList.svelte';
  import { app } from '$lib/stores/app.svelte.js';
  app.activeView = 'saved';
</script>

<svelte:head>
  <title>Saved · Readr</title>
</svelte:head>

<ArticleList savedOnly={true} />
