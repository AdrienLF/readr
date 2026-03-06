/**
 * Layout integrity tests.
 *
 * Guard against layout regressions like:
 * - Horizontal overflow (content wider than viewport)
 * - Zero-height scroll containers (overflow:hidden eating flex children)
 * - Reader panel pushing main content off-screen
 * - Missing flex/min-h-0 causing child scroll to not work
 */
import { test, expect } from '@playwright/test';

// ── No horizontal overflow ────────────────────────────────────────────────────

test.describe('No horizontal overflow', () => {
  const pages = ['/', '/settings', '/search', '/bookmarks', '/digest'];

  for (const path of pages) {
    test(`${path} has no horizontal overflow`, async ({ page }) => {
      await page.goto(path);
      await page.waitForSelector('[data-testid="sidebar"]');

      const hasHorizontalOverflow = await page.evaluate(() => {
        const docWidth = document.documentElement.scrollWidth;
        const viewWidth = document.documentElement.clientWidth;
        return docWidth > viewWidth;
      });
      expect(hasHorizontalOverflow).toBe(false);
    });
  }
});

// ── Main layout structure ─────────────────────────────────────────────────────

test.describe('Root layout structure', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="sidebar"]');
  });

  test('viewport fills the full screen height', async ({ page }) => {
    const bodyHeight = await page.evaluate(() => document.body.clientHeight);
    const viewportHeight = page.viewportSize().height;
    expect(bodyHeight).toBe(viewportHeight);
  });

  test('sidebar is exactly 240px wide on desktop', async ({ page }) => {
    const sidebar = page.getByTestId('sidebar');
    const box = await sidebar.boundingBox();
    expect(box.width).toBe(240);
  });

  test('main content area fills remaining width', async ({ page }) => {
    const sidebar = page.getByTestId('sidebar');
    const sidebarBox = await sidebar.boundingBox();
    const viewportWidth = page.viewportSize().width;

    const articleList = page.getByTestId('article-list');
    const listBox = await articleList.boundingBox();

    // Main area should start right after the sidebar
    expect(listBox.x).toBeCloseTo(sidebarBox.width, -1);
    // And take up the rest of the width
    expect(listBox.width + listBox.x).toBeCloseTo(viewportWidth, -1);
  });

  test('article list scroll container fills its parent', async ({ page }) => {
    const scroll = page.getByTestId('article-list-scroll');
    const box = await scroll.boundingBox();
    // Must have a real height (not collapsed to 0)
    expect(box.height).toBeGreaterThan(200);
  });
});

// ── Settings layout ───────────────────────────────────────────────────────────

test.describe('Settings layout', () => {
  test('settings scroll container fills full height', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForSelector('h1:has-text("Settings")');

    const scroll = page.getByTestId('settings-scroll');
    const box = await scroll.boundingBox();
    // Must fill the viewport height minus any top chrome (mobile bar, etc.)
    expect(box.height).toBeGreaterThan(400);
  });

  test('settings scroll container is not overflow:hidden', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForSelector('h1:has-text("Settings")');

    const scroll = page.getByTestId('settings-scroll');
    const overflow = await scroll.evaluate((el) => getComputedStyle(el).overflowY);
    // Should be 'auto' or 'scroll' — NOT 'hidden'
    expect(overflow).not.toBe('hidden');
    expect(['auto', 'scroll']).toContain(overflow);
  });
});

// ── Article reader layout ─────────────────────────────────────────────────────

test.describe('Article reader layout', () => {
  test('reader panel does not cause horizontal overflow', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="article-list"]');

    const cards = page.getByTestId('article-card');
    if (await cards.count() === 0) {
      test.skip('No articles available');
      return;
    }

    await cards.first().click();
    await expect(page.getByTestId('article-reader')).toBeVisible();

    const hasHorizontalOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasHorizontalOverflow).toBe(false);
  });

  test('reader panel overlays content — does not push sidebar off screen', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="article-list"]');

    const cards = page.getByTestId('article-card');
    if (await cards.count() === 0) {
      test.skip('No articles available');
      return;
    }

    await cards.first().click();
    await expect(page.getByTestId('article-reader')).toBeVisible();

    // Sidebar must still be in its original position (not pushed off)
    const sidebar = page.getByTestId('sidebar');
    const box = await sidebar.boundingBox();
    expect(box.x).toBeGreaterThanOrEqual(0);
  });
});

// ── Flex/min-h-0 guard ────────────────────────────────────────────────────────

test.describe('Flex container min-h-0 guard', () => {
  /**
   * A common Tailwind gotcha: flex children with overflow-y:auto collapse to 0
   * height unless the parent chain has min-h-0. These tests detect that case.
   */

  test('article list outer wrapper has nonzero min-height', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="article-list"]');

    const list = page.getByTestId('article-list');
    const box = await list.boundingBox();
    expect(box.height).toBeGreaterThan(0);
  });

  test('settings page outer wrapper has nonzero height', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForSelector('h1:has-text("Settings")');

    const scroll = page.getByTestId('settings-scroll');
    const box = await scroll.boundingBox();
    expect(box.height).toBeGreaterThan(0);
  });
});
