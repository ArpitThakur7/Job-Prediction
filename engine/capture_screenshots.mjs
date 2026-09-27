import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const outputDir = path.resolve(__dirname, '../docs/screenshots');

if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

const pagesToCapture = [
  { name: '01_dashboard.png', url: 'http://localhost:3000/' },
  { name: '02_job_board.png', url: 'http://localhost:3000/job-board' },
  { name: '03_resume_analyzer.png', url: 'http://localhost:3000/analyzer' },
  { name: '04_job_parser.png', url: 'http://localhost:3000/parser' },
  { name: '05_career_coach.png', url: 'http://localhost:3000/coach' },
  { name: '06_account_security.png', url: 'http://localhost:3000/account' },
  { name: '07_platform_settings.png', url: 'http://localhost:3000/settings' },
  { name: '08_applications_tracker.png', url: 'http://localhost:3000/applications' },
  { name: '09_resume_tailor.png', url: 'http://localhost:3000/resume' },
  { name: '10_salvo_engine_settings.png', url: 'http://localhost:3000/settings/salvo' },
];

async function main() {
  console.log('Launching browser...');
  const browser = await chromium.launch({
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 920 },
    deviceScaleFactor: 1.5,
  });

  for (const item of pagesToCapture) {
    try {
      console.log(`Navigating to ${item.url} for ${item.name}...`);
      const page = await context.newPage();
      await page.goto(item.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      // Wait for any animations, charts, or WebGL to initialize
      await page.waitForTimeout(3500);
      const filePath = path.join(outputDir, item.name);
      await page.screenshot({ path: filePath, fullPage: false });
      console.log(`Saved screenshot to ${filePath}`);
      await page.close();
    } catch (err) {
      console.error(`Error capturing ${item.name}:`, err);
    }
  }

  await browser.close();
  console.log('All screenshots captured successfully!');
}

main();
