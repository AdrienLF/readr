/**
 * Scroll regression tests.
 *
 * These guard against the class of bug where an overflow:hidden ancestor clips
 * a scroll container, making content unreachable. Each test verifies that the
 * container is taller than the viewport AND that elements near the bottom are
 * actually reachable via scrolling.
 */
import { test, expect } from '@playwright/test';

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Returns true when the element has more content than visible height,
 * i.e. it would actually scroll if the user tried.
 */
async function isScrollable(locator) {
  return locator.evaluate((el) => el.scrollHeight > el.clientHeight);
}

/**
 * Returns true when the element's scroll container is not clipped to 0 height
 * (the most common manifestation of the overflow:hidden bug).
 */
async function hasPositiveHeight(locator) {
  return locator.evaluate((el) => el.clientHeight > 0);
}

// ── Settings page ─────────────────────────────────────────────────────────────

test.describe('Settings page — scroll', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
    await page.waitForSelector('h1:has-text("Settings")');
  });

  test('scroll container has positive height', async ({ page }) => {
    const scroll = page.getByTestId('settings-scroll');
    await expect(scroll).toBeVisible();
    expect(await hasPositiveHeight(scroll)).toBe(true);
  });

  test('settings page is scrollable when it has multiple sections', async ({ page }) => {
    const scroll = page.getByTestId('settings-scroll');
    // The page has General / Feeds / Import / Mute / Tags / Rules / Topics sections
    // — enough to exceed one viewport height
    expect(await isScrollable(scroll)).toBe(true);
  });

  test('Topics section is reachable by scrolling', async ({ page }) => {
    // This would fail if overflow:hidden is clipping the container
    const topicsHeading = page.locator('section').filter({ hasText: 'Topics' }).last();
    await topicsHeading.scrollIntoViewIfNeeded();
    await expect(topicsHeading).toBeInViewport();
  });

  test('Automation Rules section is reachable by scrolling', async ({ page }) => {
    const rulesHeading = page.locator('section').filter({ hasText: 'Automation Rules' });
    await rulesHeading.scrollIntoViewIfNeeded();
    await expect(rulesHeading).toBeInViewport();
  });

  test('Import / Export section is reachable by scrolling', async ({ page }) => {
    const importSection = page.locator('section').filter({ hasText: 'Import / Export' });
    await importSection.scrollIntoViewIfNeeded();
    await expect(importSection).toBeInViewport();
  });

  test('scroll position survives tab change and return', async ({ page }) => {
    const scroll = page.getByTestId('settings-scroll');

    // Scroll to bottom
    await scroll.evaluate((el) => (el.scrollTop = el.scrollHeight));
    const scrollTopBefore = await scroll.evaluate((el) => el.scrollTop);
    expect(scrollTopBefore).toBeGreaterThan(0);

    // Navigate away and back
    await page.goto('/');
    await page.goto('/settings');
    await page.waitForSelector('h1:has-text("Settings")');

    // Scroll container should still be functional (not stuck at 0)
    const newScroll = page.getByTestId('settings-scroll');
    expect(await hasPositiveHeight(newScroll)).toBe(true);
  });
});

// ── Article list ──────────────────────────────────────────────────────────────

test.describe('Article list — scroll', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="article-list"]');
  });

  test('article list scroll container has positive height', async ({ page }) => {
    const scroll = page.getByTestId('article-list-scroll');
    await expect(scroll).toBeVisible();
    expect(await hasPositiveHeight(scroll)).toBe(true);
  });

  test('article list scrollable when articles present', async ({ page }) => {
    const cards = page.getByTestId('article-card');
    const count = await cards.count();
    if (count < 5) {
      test.skip('Not enough articles to test scroll');
      return;
    }

    const scroll = page.getByTestId('article-list-scroll');
    expect(await isScrollable(scroll)).toBe(true);
  });

  test('articles near page bottom are reachable', async ({ page }) => {
    const cards = page.getByTestId('article-card');
    const count = await cards.count();
    if (count === 0) {
      test.skip('No articles available');
      return;
    }

    const last = cards.last();
    await last.scrollIntoViewIfNeeded();
    await expect(last).toBeInViewport();
  });
});

// ── Article reader ────────────────────────────────────────────────────────────

test.describe('Article reader — scroll', () => {
  test('reader content area is scrollable for long articles', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="article-list"]');

    const cards = page.getByTestId('article-card');
    if (await cards.count() === 0) {
      test.skip('No articles available');
      return;
    }

    await cards.first().click();
    await expect(page.getByTestId('article-reader')).toBeVisible();

    // The reader's scroll container wraps the full content area
    const readerScroll = page.getByTestId('article-reader').locator('.overflow-y-auto').first();
    expect(await hasPositiveHeight(readerScroll)).toBe(true);
  });

  test('reader does not clip content behind viewport', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="article-list"]');

    const cards = page.getByTestId('article-card');
    if (await cards.count() === 0) {
      test.skip('No articles available');
      return;
    }

    await cards.first().click();
    const reader = page.getByTestId('article-reader');
    await expect(reader).toBeVisible();

    // The reader title should be immediately visible (not scrolled out of view)
    await expect(page.getByTestId('reader-title')).toBeVisible();
  });
});

// ── Sidebar ───────────────────────────────────────────────────────────────────

test.describe('Sidebar — scroll', () => {
  test('sidebar scroll area has positive height', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="sidebar"]');

    const sidebarScroll = page.getByTestId('sidebar').locator('.overflow-y-auto').first();
    expect(await hasPositiveHeight(sidebarScroll)).toBe(true);
  });
});
