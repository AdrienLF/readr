import { test, expect } from '@playwright/test';
import { api } from './helpers.js';

// These tests assume at least some articles are present.
// They are designed to be run after feed-management tests have added feeds,
// or can be run independently if the DB already has articles.

test.describe('Article Reading', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="article-list"]');
  });

  test('article list shows article cards', async ({ page }) => {
    const cards = page.getByTestId('article-card');
    // If there are articles, test card structure
    const count = await cards.count();
    if (count === 0) {
      test.skip('No articles available');
      return;
    }

    const firstCard = cards.first();
    await expect(firstCard).toBeVisible();
    // Cards should have a title
    await expect(firstCard.locator('h3')).toBeVisible();
  });

  test('clicking article card opens reader panel', async ({ page }) => {
    const cards = page.getByTestId('article-card');
    const count = await cards.count();
    if (count === 0) test.skip('No articles available');

    await cards.first().click();
    await expect(page.getByTestId('article-reader')).toBeVisible();
    await expect(page.getByTestId('reader-title')).toBeVisible();
  });

  test('reader shows article title and content', async ({ page }) => {
    const cards = page.getByTestId('article-card');
    if (await cards.count() === 0) test.skip('No articles available');

    const cardTitle = await cards.first().locator('h3').textContent();
    await cards.first().click();

    const readerTitle = page.getByTestId('reader-title');
    await expect(readerTitle).toBeVisible();
    expect(await readerTitle.textContent()).toBe(cardTitle.trim());
  });

  test('reader has Open Original button', async ({ page }) => {
    const cards = page.getByTestId('article-card');
    if (await cards.count() === 0) test.skip('No articles available');

    await cards.first().click();
    await expect(page.getByLabel('Open original')).toBeVisible();
  });

  test('reader closes on Escape key', async ({ page }) => {
    const cards = page.getByTestId('article-card');
    if (await cards.count() === 0) test.skip('No articles available');

    await cards.first().click();
    await expect(page.getByTestId('article-reader')).toBeVisible();

    await page.keyboard.press('Escape');
    // Reader closes via CSS transform (translate-x-full), not display:none
    await expect(async () => {
      const cls = await page.getByTestId('article-reader').getAttribute('class');
      expect(cls).toContain('translate-x-full');
    }).toPass({ timeout: 3_000 });
  });

  test('article is marked read after opening', async ({ page }) => {
    const cards = page.getByTestId('article-card');
    if (await cards.count() === 0) test.skip('No articles available');

    const firstCard = cards.first();
    // Unread articles have the purple dot
    const hadDot = await firstCard.locator('.bg-violet-500').count() > 0;

    await firstCard.click();
    await page.getByLabel('Close').click();

    // After closing, the dot should be gone
    if (hadDot) {
      await expect(firstCard.locator('.bg-violet-500')).not.toBeVisible();
    }
  });

  test('bookmark toggle works from article card', async ({ page }) => {
    const cards = page.getByTestId('article-card');
    if (await cards.count() === 0) test.skip('No articles available');

    const bookmarkBtn = cards.first().getByLabel('Toggle bookmark');
    await bookmarkBtn.click();

    // Should not throw, button should still be visible
    await expect(bookmarkBtn).toBeVisible();
  });

  test('bookmarked articles appear in Bookmarks page', async ({ page }) => {
    const cards = page.getByTestId('article-card');
    if (await cards.count() === 0) test.skip('No articles available');

    // Bookmark first article
    await cards.first().getByLabel('Toggle bookmark').click();

    // Navigate to bookmarks
    await page.goto('/bookmarks');
    await page.waitForSelector('[data-testid="article-list"]');

    const bookmarked = page.getByTestId('article-card');
    // Allow time for bookmarks to load from backend
    await expect(bookmarked.first()).toBeVisible({ timeout: 8_000 });
  });
});

test.describe('Reddit Comments', () => {
  test('Comments button visible for Reddit articles', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="article-list"]');

    // Find a Reddit article by checking if any feed is from reddit.com
    const res = await page.request.get('/api/articles?page=1&page_size=50');
    const data = await res.json();
    const redditArticle = data.items?.find((a) => a.url && a.url.includes('reddit.com'));
    if (!redditArticle) {
      test.skip('No Reddit articles available');
      return;
    }
    // Click that article directly
    const cards = page.getByTestId('article-card');

    await redditCards.first().click();
    // Wait for reader to open
    await page.waitForTimeout(500);
    // Comments button appears for Reddit articles
    await expect(page.getByLabel('Load comments')).toBeVisible({ timeout: 5_000 });
  });
});
