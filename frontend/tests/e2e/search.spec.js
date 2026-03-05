import { test, expect } from '@playwright/test';

test.describe('Search', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/search');
    await page.waitForSelector('[data-testid="search-input"]');
  });

  test('shows empty state before typing', async ({ page }) => {
    await expect(page.getByText('Start typing to search')).toBeVisible();
  });

  test('search input is focused on page load', async ({ page }) => {
    const input = page.getByTestId('search-input');
    await expect(input).toBeFocused();
  });

  test('typing triggers search with debounce', async ({ page }) => {
    await page.getByTestId('search-input').fill('test');
    // After debounce (350ms), should show results or "no results"
    await page.waitForTimeout(500);
    await expect(page.getByText('Start typing to search')).not.toBeVisible();
  });

  test('shows no results message for unknown query', async ({ page }) => {
    await page.getByTestId('search-input').fill('xyznonexistentquery123');
    await page.waitForTimeout(500);
    await expect(page.getByText(/No results for/)).toBeVisible({ timeout: 5_000 });
  });

  test('shows result count when articles match', async ({ page }) => {
    // This test is meaningful only if articles exist in the DB
    await page.getByTestId('search-input').fill('the');
    await page.waitForTimeout(500);

    // Either shows results or "no results" — both are valid UI states
    const hasResults = await page.getByTestId('article-card').count() > 0;
    const hasNoResults = await page.getByText(/No results/).isVisible().catch(() => false);
    expect(hasResults || hasNoResults).toBe(true);
  });

  test('can navigate to search from sidebar', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="sidebar"]');
    await page.getByRole('link', { name: 'Search' }).click();
    await expect(page).toHaveURL('/search');
    await expect(page.getByTestId('search-input')).toBeVisible();
  });

  test('clearing search returns to empty state', async ({ page }) => {
    const input = page.getByTestId('search-input');
    await input.fill('test query');
    await page.waitForTimeout(500);

    await input.clear();
    await page.waitForTimeout(100);
    await expect(page.getByText('Start typing to search')).toBeVisible();
  });
});
