// Captures the README screenshots from a running local stack.
//   1. Start backend, engine and frontend (run.bat, or the three dev servers).
//   2. node engine/capture_screenshots.mjs
// Images are written to docs/screenshots/.

import { chromium } from 'playwright';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const outputDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../docs/screenshots');
const BASE = process.env.SCREENSHOT_BASE_URL || 'http://localhost:3000';
fs.mkdirSync(outputDir, { recursive: true });

const desktop = { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 };
const phone = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true };

const shots = [
  { name: '01_home.png', path: '/', wait: 6000 },
  { name: '02_job_feed.png', path: '/jobs', wait: 4000 },
  {
    name: '03_filters.png',
    path: '/jobs',
    wait: 4000,
    async act(page) {
      await page.getByLabel('Search jobs').fill('python');
      await page.getByLabel('Minimum fit score').fill('50');
      await page.getByRole('switch', { name: 'Remote only' }).check({ force: true });
      await page.waitForTimeout(800);
    },
  },
  {
    name: '04_job_preview.png',
    path: '/jobs',
    wait: 4000,
    async act(page) {
      await page.locator('article').first().click();
      await page.waitForTimeout(1200);
    },
  },
  { name: '05_dark_theme.png', path: '/jobs', wait: 4000, theme: 'aurora' },
  // Tracker, Resume studio and Resume check join the gallery once they get the new design.
  { name: '06_mobile_home.png', path: '/', wait: 6000, device: phone },
  {
    name: '07_mobile_filters.png',
    path: '/jobs',
    wait: 4000,
    device: phone,
    async act(page) {
      await page.getByRole('button', { name: /^Filters/ }).click();
      await page.waitForTimeout(800);
    },
  },
];

const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
let failed = 0;
for (const shot of shots) {
  const context = await browser.newContext({ ...(shot.device || desktop), colorScheme: 'light' });
  await context.addInitScript((theme) => {
    try {
      localStorage.setItem('theme', theme);
    } catch {}
  }, shot.theme || 'luminary');
  const page = await context.newPage();
  try {
    await page.goto(BASE + shot.path, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(shot.wait);
    if (shot.act) await shot.act(page);
    // Hide the Next.js dev indicator so it doesn't appear in published images.
    await page.addStyleTag({ content: 'nextjs-portal { display: none !important; }' });
    await page.screenshot({ path: path.join(outputDir, shot.name) });
    console.log('saved', shot.name);
  } catch (err) {
    failed++;
    console.error('failed', shot.name, err.message.split('\n')[0]);
  }
  await context.close();
}
await browser.close();
process.exit(failed ? 1 : 0);
