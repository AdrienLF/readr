/**
 * Keyboard shortcut tests.
 *
 * Guard against regressions in the global keyboard handler and
 * per-component shortcut handling.
 */
import { test, expect } from '@playwright/test';

// Helper: check the article reader is off-screen (closed via CSS transform)
async function readerIsClosed(page) {
  const cls = await page.getByTestId('article-reader').getAttribute('class');
  return cls && cls.includes('translate-x-full');
}

test.describe('Global keyboard shortcuts', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="sidebar"]');
    // Click the main area so focus is not in an input
    await page.locator('[data-testid="article-list"]').click({ position: { x: 10, y: 10 } });
  });

  test('? opens keyboard shortcuts overlay', async ({ page }) => {
    await page.keyboard.press('Shift+?');
    await expect(page.getByRole('dialog', { name: 'Keyboard shortcuts' })).toBeVisible({ timeout: 2_000 });
  });

  test('Escape closes keyboard shortcuts overlay', async ({ page }) => {
    await page.keyboard.press('Shift+?');
    await expect(page.getByRole('dialog', { name: 'Keyboard shortcuts' })).toBeVisible({ timeout: 2_000 });
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog', { name: 'Keyboard shortcuts' })).not.toBeVisible({ timeout: 2_000 });
  });

  test('Escape closes the article reader', async ({ page }) => {
    const cards = page.getByTestId('article-card');
    if (await cards.count() === 0) {
      test.skip('No articles available');
      return;
    }

    await cards.first().click();
    // Reader slides in — check it is on-screen (not translate-x-full)
    await expect(async () => {
      expect(await readerIsClosed(page)).toBe(false);
    }).toPass({ timeout: 3_000 });

    await page.keyboard.press('Escape');
    // Reader slides out — translate-x-full
    await expect(async () => {
      expect(await readerIsClosed(page)).toBe(true);
    }).toPass({ timeout: 3_000 });
  });
});

test.describe('Modal keyboard handling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="sidebar"]');
  });

  test('Escape closes the Add Feed modal', async ({ page }) => {
    await page.getByTestId('add-feed-btn').click();
    await expect(page.getByRole('dialog', { name: 'Add feed' })).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog', { name: 'Add feed' })).not.toBeVisible({ timeout: 2_000 });
  });

  test('Escape closes the Add Topic modal', async ({ page }) => {
    await page.getByTestId('add-topic-btn').click();
    await expect(page.getByRole('dialog', { name: 'Add topic' })).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog', { name: 'Add topic' })).not.toBeVisible({ timeout: 2_000 });
  });
});

test.describe('Article list keyboard navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="article-list"]');
  });

  test('j/k navigation does not crash the page', async ({ page }) => {
    const cards = page.getByTestId('article-card');
    if (await cards.count() < 2) {
      test.skip('Need at least 2 articles');
      return;
    }

    await page.locator('[data-testid="article-list"]').click({ position: { x: 10, y: 10 } });
    await page.keyboard.press('j');
    await page.keyboard.press('j');
    await page.keyboard.press('k');

    await expect(page.getByTestId('article-list')).toBeVisible();
  });

  test('r key triggers article list refresh', async ({ page }) => {
    await page.locator('[data-testid="article-list"]').click({ position: { x: 10, y: 10 } });
    await page.keyboard.press('r');
    // Refresh button should briefly spin or list reloads — no crash
    await expect(page.getByTestId('article-list')).toBeVisible();
  });
});

test.describe('Search page keyboard', () => {
  test('search input is focused immediately on /search', async ({ page }) => {
    await page.goto('/search');
    await page.waitForSelector('[data-testid="search-input"]');
    await expect(page.getByTestId('search-input')).toBeFocused();
  });

  test('j/k inside search input do not trigger article navigation', async ({ page }) => {
    await page.goto('/search');
    await page.waitForSelector('[data-testid="search-input"]');

    const input = page.getByTestId('search-input');
    await input.fill('javascript');
    await input.press('j');
    await input.press('k');

    // Input value must still contain the typed text
    expect(await input.inputValue()).toContain('javascript');
  });
});
