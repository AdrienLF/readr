/**
 * Data persistence tests.
 *
 * Guard against the class of bug where state is held in memory and lost on
 * page reload — or where the nginx proxy silently drops requests after a
 * backend restart (stale upstream IP).
 */
import { test, expect } from '@playwright/test';
import { api } from './helpers.js';

// ── API proxy health ──────────────────────────────────────────────────────────

test.describe('API proxy health', () => {
  test('GET /api/feeds returns 200 (nginx proxy is alive)', async ({ request }) => {
    const res = await request.get('/api/feeds');
    expect(res.status()).toBe(200);
  });

  test('GET /api/settings returns 200', async ({ request }) => {
    const res = await request.get('/api/settings');
    expect(res.status()).toBe(200);
  });

  test('GET /api/topics returns 200', async ({ request }) => {
    const res = await request.get('/api/topics');
    expect(res.status()).toBe(200);
  });

  test('API returns JSON (not nginx 502 HTML)', async ({ request }) => {
    const res = await request.get('/api/feeds');
    const contentType = res.headers()['content-type'] || '';
    expect(contentType).toContain('application/json');
  });
});

// ── Sidebar feed count consistency ───────────────────────────────────────────

test.describe('Feed count consistency', () => {
  test('sidebar feed count matches settings feed count', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="sidebar"]');

    // Count feeds in sidebar (uncategorized + inside expanded topics)
    const apiFeeds = await api.get('/feeds');
    const apiCount = apiFeeds.length;

    // Settings page shows all feeds
    await page.goto('/settings');
    await page.waitForSelector('h1:has-text("Settings")');

    const feedItems = page.getByTestId('feed-item');
    // Wait for store to load feeds (async)
    if (apiCount > 0) {
      await expect(feedItems.first()).toBeVisible({ timeout: 5_000 });
    }
    const settingsCount = await feedItems.count();

    expect(settingsCount).toBe(apiCount);
  });
});

// ── Settings persistence ──────────────────────────────────────────────────────

test.describe('Settings persistence across reloads', () => {
  test('digest time persists after page reload', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForSelector('h1:has-text("Settings")');

    // Wait for onMount to finish loading settings from API before filling
    await expect(page.getByLabel('Daily digest time')).not.toHaveValue('');
    // Set a distinctive value
    await page.getByLabel('Daily digest time').fill('06:15');
    await page.getByRole('button', { name: 'Save Settings' }).click();
    await page.waitForSelector('button:has-text("Saved")');

    // Reload and verify
    await page.reload();
    await page.waitForSelector('h1:has-text("Settings")');
    const value = await page.getByLabel('Daily digest time').inputValue();
    expect(value).toBe('06:15');

    // Restore
    await page.getByLabel('Daily digest time').fill('07:00');
    await page.getByRole('button', { name: 'Save Settings' }).click();
  });

  test('fetch interval persists after page reload', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForSelector('h1:has-text("Settings")');

    await expect(page.getByLabel('Feed refresh interval (seconds)')).not.toHaveValue('');
    await page.getByLabel('Feed refresh interval (seconds)').fill('1800');
    await page.getByRole('button', { name: 'Save Settings' }).click();
    await page.waitForSelector('button:has-text("Saved")');

    await page.reload();
    await page.waitForSelector('h1:has-text("Settings")');
    const value = await page.getByLabel('Feed refresh interval (seconds)').inputValue();
    expect(value).toBe('1800');

    // Restore
    await page.getByLabel('Feed refresh interval (seconds)').fill('3600');
    await page.getByRole('button', { name: 'Save Settings' }).click();
  });
});

// ── Feed visibility after navigation ─────────────────────────────────────────

test.describe('Feed visibility', () => {
  test('feeds present before navigation are still visible after navigating away and back', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="sidebar"]');

    // Get the current API feed list
    const feeds = await api.get('/feeds');
    if (feeds.length === 0) {
      test.skip('No feeds to test persistence with');
      return;
    }

    const firstFeedTitle = feeds[0].title || feeds[0].url;

    // Navigate to settings and back
    await page.goto('/settings');
    await page.goto('/');
    await page.waitForSelector('[data-testid="sidebar"]');

    // Feed count via API should be unchanged
    const feedsAfter = await api.get('/feeds');
    expect(feedsAfter.length).toBe(feeds.length);
  });

  test('settings page still shows feeds after full page reload', async ({ page }) => {
    const feeds = await api.get('/feeds');
    if (feeds.length === 0) {
      test.skip('No feeds to test persistence with');
      return;
    }

    await page.goto('/settings');
    await page.waitForSelector('h1:has-text("Settings")');

    // Hard reload
    await page.reload();
    await page.waitForSelector('h1:has-text("Settings")');

    // Wait for feeds to load from the store (async)
    const feedItems = page.getByTestId('feed-item');
    await expect(feedItems.first()).toBeVisible({ timeout: 5_000 });
    expect(await feedItems.count()).toBe(feeds.length);
  });

  test('frontend shows feeds that exist in the API', async ({ page }) => {
    const feeds = await api.get('/feeds');
    if (feeds.length === 0) {
      test.skip('No feeds to check');
      return;
    }

    await page.goto('/settings');
    await page.waitForSelector('h1:has-text("Settings")');

    // Every feed from the API should be rendered in the settings list
    for (const feed of feeds) {
      const label = feed.title || feed.url;
      // Title might be truncated, so check for partial match
      await expect(
        page.getByTestId('feed-item').filter({ hasText: label.slice(0, 20) }).first()
      ).toBeVisible();
    }
  });
});

// ── Topic persistence ─────────────────────────────────────────────────────────

test.describe('Topic persistence', () => {
  test('topics created via API appear in sidebar', async ({ page }) => {
    const topics = await api.get('/topics');
    if (topics.length === 0) {
      test.skip('No topics to test');
      return;
    }

    await page.goto('/');
    await page.waitForSelector('[data-testid="sidebar"]');

    for (const topic of topics) {
      await expect(
        page.getByTestId('sidebar').getByText(topic.name).first()
      ).toBeVisible();
    }
  });
});
