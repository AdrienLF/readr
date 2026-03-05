import { test, expect } from '@playwright/test';

test.describe('Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
    await page.waitForSelector('h1:has-text("Settings")');
  });

  test('loads current settings', async ({ page }) => {
    await expect(page.getByLabel('Daily digest time')).toBeVisible();
    await expect(page.getByLabel('Feed refresh interval (seconds)')).toBeVisible();
    await expect(page.getByLabel('Ollama model')).toBeVisible();
  });

  test('shows default digest time 07:00', async ({ page }) => {
    const digestTimeInput = page.getByLabel('Daily digest time');
    const value = await digestTimeInput.inputValue();
    expect(value).toBe('07:00');
  });

  test('shows default ollama model', async ({ page }) => {
    const modelInput = page.getByLabel('Ollama model');
    const value = await modelInput.inputValue();
    expect(value).toBe('qwen3:8b');
  });

  test('can update digest time and save', async ({ page }) => {
    const digestTimeInput = page.getByLabel('Daily digest time');
    await digestTimeInput.fill('08:30');
    await page.getByRole('button', { name: 'Save Settings' }).click();

    // Should show "Saved" confirmation
    await expect(page.getByRole('button', { name: 'Saved' })).toBeVisible({ timeout: 5_000 });
  });

  test('can update ollama model', async ({ page }) => {
    await page.getByLabel('Ollama model').fill('llama3:8b');
    await page.getByRole('button', { name: 'Save Settings' }).click();
    await expect(page.getByRole('button', { name: 'Saved' })).toBeVisible({ timeout: 5_000 });
  });

  test('settings persist after page reload', async ({ page }) => {
    await page.getByLabel('Daily digest time').fill('06:00');
    await page.getByRole('button', { name: 'Save Settings' }).click();
    await page.waitForSelector('button:has-text("Saved")');

    await page.reload();
    await page.waitForSelector('h1:has-text("Settings")');

    const value = await page.getByLabel('Daily digest time').inputValue();
    expect(value).toBe('06:00');

    // Restore default
    await page.getByLabel('Daily digest time').fill('07:00');
    await page.getByRole('button', { name: 'Save Settings' }).click();
  });

  test('feeds section is visible', async ({ page }) => {
    await expect(page.getByText(/Feeds/)).toBeVisible();
  });

  test('topics section is visible', async ({ page }) => {
    await expect(page.getByText(/Topics/)).toBeVisible();
  });

  test('shows pull command for ollama model', async ({ page }) => {
    const hint = page.getByText(/ollama pull/);
    await expect(hint).toBeVisible();
  });

  test('can edit feed title inline', async ({ page }) => {
    const feedItems = page.getByTestId('feed-item');
    const count = await feedItems.count();
    if (count === 0) {
      test.skip('No feeds to edit');
      return;
    }

    await feedItems.first().hover();
    await feedItems.first().getByLabel(/edit/i).click();
    await expect(feedItems.first().getByRole('textbox')).toBeVisible();
  });
});

test.describe('Digest page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/digest');
    await page.waitForSelector('h1:has-text("Daily Digest")');
  });

  test('shows digest page header', async ({ page }) => {
    await expect(page.getByText('Daily Digest')).toBeVisible();
  });

  test('shows date picker', async ({ page }) => {
    await expect(page.getByRole('textbox', { name: '' }).or(page.locator('input[type="date"]'))).toBeVisible();
  });

  test('shows generate button', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Generate/ })).toBeVisible();
  });

  test('shows empty state when no digest for today', async ({ page }) => {
    // This will be true on first run
    const hasEmpty = await page.getByText(/No digest for/).isVisible().catch(() => false);
    const hasDigests = await page.locator('.card').count() > 0;
    expect(hasEmpty || hasDigests).toBe(true);
  });
});
