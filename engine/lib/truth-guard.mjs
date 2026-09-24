import { readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import yaml from 'js-yaml';
import { ROOT } from './config.mjs';

function extractNumbers(text) {
  if (!text) return [];
  // Extracts numbers, percentages, multipliers like "40%", "10x", "$50k", "150ms", "500"
  const matches = String(text).match(/\b\d+(?:\.\d+)?(?:%|x|ms|s|k|m|b)?\b/gi) || [];
  return matches.map((m) => m.toLowerCase());
}

function normalizeStr(s) {
  return String(s || '').toLowerCase().replace(/[^a-z0-9]/g, ' ').replace(/\s+/g, ' ').trim();
}

/**
 * Extracts all verified facts from master resume.md and portfolio.yaml
 */
export async function loadTrustedFactBank() {
  const masterPath = join(ROOT, 'data/resume/resume.md');
  const portfolioPath = join(ROOT, 'config/portfolio.yaml');

  let masterText = '';
  if (existsSync(masterPath)) {
    masterText = await readFile(masterPath, 'utf8');
  }

  let portfolio = { projects: [] };
  if (existsSync(portfolioPath)) {
    const raw = await readFile(portfolioPath, 'utf8');
    portfolio = yaml.load(raw) || { projects: [] };
  }

  const trustedText = `${masterText}\n${JSON.stringify(portfolio)}`;
  const normalizedTrusted = normalizeStr(trustedText);
  const trustedNumbers = new Set(extractNumbers(trustedText));

  // Extract known project names
  const trustedProjects = (portfolio.projects || []).map((p) => normalizeStr(p.name || p.title));

  return {
    masterText,
    portfolio,
    normalizedTrusted,
    trustedNumbers,
    trustedProjects,
  };
}

/**
 * Validates a tailored resume against the trusted fact bank.
 * Fails closed or sanitizes any ungrounded assertions.
 */
export function verifyAndSanitizeResume(tailoredResume, factBank) {
  const violations = [];
  const sanitized = JSON.parse(JSON.stringify(tailoredResume));

  // 1. Verify Experience
  if (Array.isArray(sanitized.experience)) {
    for (const exp of sanitized.experience) {
      const companyNorm = normalizeStr(exp.company || exp.employer);
      if (companyNorm && !factBank.normalizedTrusted.includes(companyNorm)) {
        violations.push(`Unverified employer "${exp.company}" detected.`);
      }
      if (Array.isArray(exp.bullets)) {
        exp.bullets = exp.bullets.filter((bullet) => {
          const numbers = extractNumbers(bullet);
          for (const num of numbers) {
            if (!factBank.trustedNumbers.has(num) && !['0', '1', '2'].includes(num)) {
              violations.push(`Unverified metric "${num}" in experience: "${bullet}"`);
              return false; // strip hallucinated bullet
            }
          }
          return true;
        });
      }
    }
  }

  // 2. Verify Projects
  if (Array.isArray(sanitized.projects)) {
    sanitized.projects = sanitized.projects.filter((proj) => {
      const projNorm = normalizeStr(proj.name || proj.title);
      const isKnown = factBank.trustedProjects.some((tp) => tp.includes(projNorm) || projNorm.includes(tp)) ||
                      factBank.normalizedTrusted.includes(projNorm);
      if (!isKnown) {
        violations.push(`Unverified project "${proj.name}" stripped.`);
        return false;
      }

      if (Array.isArray(proj.bullets)) {
        proj.bullets = proj.bullets.filter((b) => {
          const numbers = extractNumbers(b);
          for (const num of numbers) {
            if (!factBank.trustedNumbers.has(num) && !['0', '1', '2'].includes(num)) {
              violations.push(`Unverified metric "${num}" in project bullet: "${b}"`);
              return false;
            }
          }
          return true;
        });
      }
      return true;
    });
  }

  return {
    verified: violations.length === 0,
    violations,
    resume: sanitized,
  };
}

/**
 * Computes a diff summary between master resume and tailored resume
 */
export function generateResumeDiff(masterText, tailored) {
  const changes = [];
  if (tailored.summary) {
    changes.push({ type: 'summary', description: `Targeted summary aligned to role.` });
  }

  const projNames = (tailored.projects || []).map((p) => p.name || p.title).filter(Boolean);
  if (projNames.length) {
    changes.push({ type: 'projects', description: `Selected top portfolio projects: ${projNames.join(', ')}` });
  }

  return changes;
}
