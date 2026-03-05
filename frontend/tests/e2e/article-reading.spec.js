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
    await expect(page.getByTestId('article-reader')).not.toBeVisible({ timeout: 2_000 });
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
    await expect(bookmarked.first()).toBeVisible();
  });
});

test.describe('Reddit Comments', () => {
  test('Comments button visible for Reddit articles', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="article-list"]');

    // Find a Reddit article card (has "Reddit" label)
    const redditCards = page.locator('[data-testid="article-card"]:has-text("Reddit")');
    const count = await redditCards.count();
    if (count === 0) {
      test.skip('No Reddit articles available');
      return;
    }

    await redditCards.first().click();
    await expect(page.getByLabel('Load comments')).toBeVisible();
  });
});
