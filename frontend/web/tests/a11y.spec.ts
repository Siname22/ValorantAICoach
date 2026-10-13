import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Valorant AI Coach - WCAG 2.2 AA Accessibility Audits', () => {
  const routes = ['/resumen', '/partidas', '/informes', '/marcador', '/cuenta'];

  for (const route of routes) {
    test(`Route ${route} should pass axe-core WCAG 2.2 AA rules`, async ({ page }) => {
      await page.goto(route);

      // Verify skip link is present and targets #main-content
      const skipLink = page.locator('a.skip-link');
      await expect(skipLink).toBeAttached();
      await expect(skipLink).toHaveAttribute('href', '#main-content');

      // Verify landmarks
      await expect(page.locator('nav[aria-label]')).toBeAttached();
      await expect(page.locator('main#main-content')).toBeAttached();

      // Run axe analysis for wcag2a, wcag2aa, wcag21aa, wcag22aa
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
        .analyze();

      expect(accessibilityScanResults.violations).toEqual([]);
    });
  }

  test('Skip to content link becomes visible on keyboard focus and moves focus to #main-content', async ({ page }) => {
    await page.goto('/resumen');
    await page.keyboard.press('Tab');

    const skipLink = page.locator('a.skip-link');
    await expect(skipLink).toBeFocused();

    await page.keyboard.press('Enter');
    const mainContent = page.locator('main#main-content');
    await expect(mainContent).toBeFocused();
  });

  test('Target sizes are at least 44x44px for primary controls', async ({ page }) => {
    await page.goto('/resumen');

    const primaryButtons = page.locator('button.btn-primary');
    const count = await primaryButtons.count();

    for (let i = 0; i < count; i++) {
      const btn = primaryButtons.nth(i);
      const box = await btn.boundingBox();
      if (box) {
        expect(box.height).toBeGreaterThanOrEqual(44);
        expect(box.width).toBeGreaterThanOrEqual(44);
      }
    }
  });
});
