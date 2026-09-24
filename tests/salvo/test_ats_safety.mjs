import test from 'node:test';
import assert from 'node:assert/strict';
import { readdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { ROOT } from '../../engine/lib/config.mjs';

test('Golden Rule Verification: NO ATS filler module contains any submit action', async () => {
  const atsDir = join(ROOT, 'lib/ats');
  const files = (await readdir(atsDir)).filter((f) => f.endsWith('.mjs'));

  assert.ok(files.length >= 4, 'Expected at least 4 ATS filler modules');

  // Forbidden patterns that could submit an application
  const forbiddenPatterns = [
    /submit/i,
    /click\s*\(\s*['"`].*submit/i,
    /getByRole\s*\(\s*['"`]button['"`]\s*,\s*\{\s*name:\s*\/submit/i,
    /\.submit\s*\(/i,
    /type\s*=\s*['"`]submit['"`]/i,
  ];

  for (const file of files) {
    const content = await readFile(join(atsDir, file), 'utf8');
    const lines = content.split('\n');

    lines.forEach((line, index) => {
      // Allow comment explanations that explicitly state submit is not clicked
      const trimmed = line.trim();
      if (trimmed.startsWith('//') || trimmed.startsWith('*') || trimmed.startsWith('/*')) {
        return;
      }

      // Check code lines for any invocation or selector that targets submit
      if (
        /click/i.test(line) &&
        /submit/i.test(line)
      ) {
        assert.fail(`[GOLDEN RULE VIOLATION] Submit action detected in ${file}:${index + 1}: "${line}"`);
      }

      if (/getByRole\s*\(\s*['"]button['"]\s*,\s*\{\s*name:\s*\/submit/i.test(line)) {
        assert.fail(`[GOLDEN RULE VIOLATION] Submit button selector detected in ${file}:${index + 1}: "${line}"`);
      }
    });
  }
});
