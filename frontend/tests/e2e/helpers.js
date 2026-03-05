/**
 * Shared helpers for E2E tests.
 * All API calls go through the backend directly to seed test data cleanly.
 */

const API = process.env.BASE_URL ? `${process.env.BASE_URL}/api` : 'http://localhost/api';

export async function apiFetch(method, path, body) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (path) => apiFetch('GET', path),
  post: (path, body) => apiFetch('POST', path, body),
  put: (path, body) => apiFetch('PUT', path, body),
  delete: (path) => apiFetch('DELETE', path),
};

/**
 * Wait for the app to be ready before running tests.
 */
export async function waitForApp(page) {
  await page.goto('/');
  await page.waitForSelector('[data-testid="sidebar"]', { timeout: 10_000 });
}
