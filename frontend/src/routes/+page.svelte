<script>
  import { app } from '$lib/stores/app.svelte.js';
  import ArticleList from '$lib/components/ArticleList.svelte';

  let topicId = $derived(app.selectedTopicId);
</script>

<svelte:head>
  <title>Readr</title>
</svelte:head>

<ArticleList {topicId} />
