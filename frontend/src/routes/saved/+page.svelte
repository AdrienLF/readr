<script>
  import ArticleList from '$lib/components/ArticleList.svelte';
  import { app } from '$lib/stores/app.svelte.js';
  app.activeView = 'saved';
</script>

<svelte:head>
  <title>Read Later · Readr</title>
</svelte:head>

<ArticleList savedOnly={true} />
