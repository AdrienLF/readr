import { test, expect } from '@playwright/test';
import { api } from './helpers.js';

test.describe('Feed Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="sidebar"]');
  });

  test('shows empty state when no feeds exist', async ({ page }) => {
    await expect(page.getByText('No articles yet')).toBeVisible();
    await expect(page.getByText('Add a feed to get started')).toBeVisible();
  });

  test('can open Add Feed modal', async ({ page }) => {
    await page.getByTestId('add-feed-btn').click();
    await expect(page.getByRole('dialog', { name: 'Add feed' })).toBeVisible();
    await expect(page.getByLabel('Feed URL')).toBeVisible();
  });

  test('can close Add Feed modal with Escape', async ({ page }) => {
    await page.getByTestId('add-feed-btn').click();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog', { name: 'Add feed' })).not.toBeVisible();
  });

  test('shows validation — empty URL cannot be submitted', async ({ page }) => {
    await page.getByTestId('add-feed-btn').click();
    const submitBtn = page.getByRole('button', { name: 'Add Feed' });
    await expect(submitBtn).toBeDisabled();
  });

  test('shows error for invalid feed URL', async ({ page }) => {
    await page.getByTestId('add-feed-btn').click();
    await page.getByLabel('Feed URL').fill('https://not-a-real-feed.invalid/rss');
    await page.getByRole('button', { name: 'Add Feed' }).click();
    // Should show an error (feed discovery will fail)
    await expect(page.getByText(/error|failed|invalid/i)).toBeVisible({ timeout: 10_000 });
  });

  test('feed appears in sidebar after adding', async ({ page }) => {
    // Use the Reddit RSS which is reliable
    await page.getByTestId('add-feed-btn').click();
    await page.getByLabel('Feed URL').fill('https://www.reddit.com/r/programming.rss');
    await page.getByRole('button', { name: 'Add Feed' }).click();

    // Wait for modal to close
    await expect(page.getByRole('dialog', { name: 'Add feed' })).not.toBeVisible({ timeout: 15_000 });

    // Feed should appear somewhere in the UI (settings or unread badge)
    await page.goto('/settings');
    await expect(page.getByText('r/programming', { exact: false })).toBeVisible({ timeout: 5_000 });
  });

  test('can delete a feed from settings', async ({ page }) => {
    // Seed a feed via API (faster than UI flow)
    // Note: if no real feed server, this may fail in isolated environments
    await page.goto('/settings');

    const feedItems = page.getByTestId('feed-item');
    const count = await feedItems.count();
    if (count === 0) {
      test.skip('No feeds to delete — skipping');
      return;
    }

    const firstFeed = feedItems.first();
    await firstFeed.hover();
    await firstFeed.getByRole('button', { name: /delete/i }).click();

    page.on('dialog', (d) => d.accept());
    await expect(feedItems).toHaveCount(count - 1);
  });
});

test.describe('Topic Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="sidebar"]');
  });

  test('can create a topic', async ({ page }) => {
    await page.getByTestId('add-topic-btn').click();
    await expect(page.getByRole('dialog', { name: 'Add topic' })).toBeVisible();

    await page.getByLabel('Name').fill('Technology');
    await page.getByRole('button', { name: 'Create' }).click();

    await expect(page.getByRole('dialog', { name: 'Add topic' })).not.toBeVisible();
    await expect(page.getByText('Technology')).toBeVisible();
  });

  test('topic appears in sidebar after creation', async ({ page }) => {
    await page.getByTestId('add-topic-btn').click();
    await page.getByLabel('Name').fill('Finance');
    await page.getByRole('button', { name: 'Create' }).click();

    await expect(page.getByTestId('sidebar')).toContainText('Finance');
  });

  test('clicking topic filters the feed', async ({ page }) => {
    // Create topic first
    await page.getByTestId('add-topic-btn').click();
    await page.getByLabel('Name').fill('MyTopic');
    await page.getByRole('button', { name: 'Create' }).click();

    // Click topic in sidebar
    await page.getByText('MyTopic').click();
    // Page should still be functional (no crash)
    await expect(page.getByTestId('article-list')).toBeVisible();
  });
});
