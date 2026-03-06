<script>
  import { app } from '$lib/stores/app.svelte.js';
  import ArticleList from '$lib/components/ArticleList.svelte';

  let topicId = $derived(app.selectedTopicId);
  let feedId  = $derived(app.selectedFeedId);
  let smartSearchId = $derived(app.activeView === 'smart-search' ? app.selectedSmartSearchId : null);
</script>

<svelte:head>
  <title>Readr</title>
</svelte:head>

<ArticleList {topicId} {feedId} {smartSearchId} />
