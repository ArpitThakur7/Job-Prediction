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
function unverifiedNumber(text, factBank) {
  return extractNumbers(text).find((num) => !factBank.trustedNumbers.has(num) && !['0', '1', '2'].includes(num));
}

function splitSentences(text) {
  return String(text || '').match(/[^.!?\n]+[.!?]*\s*|\n+/g) || [];
}

/** Drop sentences that contain a number the fact bank can't back up. */
function stripUnverifiedSentences(text, factBank, where, violations) {
  return splitSentences(text)
    .filter((sentence) => {
      const num = unverifiedNumber(sentence, factBank);
      if (num) violations.push(`Unverified metric "${num}" in ${where}: "${sentence.trim()}"`);
      return !num;
    })
    .join('')
    .trim();
}

export function verifyAndSanitizeResume(tailoredResume, factBank) {
  const violations = [];
  const sanitized = JSON.parse(JSON.stringify(tailoredResume));
  const trustedTokens = ` ${factBank.normalizedTrusted} `;

  // 1. Experience: an employer that isn't in the master resume is dropped with all its bullets.
  if (Array.isArray(sanitized.experience)) {
    sanitized.experience = sanitized.experience.filter((exp) => {
      const companyNorm = normalizeStr(exp.company || exp.employer);
      if (companyNorm && !factBank.normalizedTrusted.includes(companyNorm)) {
        violations.push(`Unverified employer "${exp.company || exp.employer}" removed.`);
        return false;
      }
      if (Array.isArray(exp.bullets)) {
        exp.bullets = exp.bullets.filter((bullet) => {
          const num = unverifiedNumber(bullet, factBank);
          if (num) violations.push(`Unverified metric "${num}" in experience: "${bullet}"`);
          return !num;
        });
      }
      return true;
    });
  }

  // 2. Summary: keep only sentences whose numbers are grounded.
  if (sanitized.summary) {
    sanitized.summary = stripUnverifiedSentences(sanitized.summary, factBank, 'summary', violations);
  }

  // 3. Skills: a skill must appear as a whole word somewhere in the fact bank.
  if (sanitized.skills && typeof sanitized.skills === 'object') {
    for (const [category, items] of Object.entries(sanitized.skills)) {
      if (!Array.isArray(items)) continue;
      sanitized.skills[category] = items.filter((skill) => {
        const norm = normalizeStr(skill);
        const known = !norm || trustedTokens.includes(` ${norm} `);
        if (!known) violations.push(`Unverified skill "${skill}" removed.`);
        return known;
      });
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
          const num = unverifiedNumber(b, factBank);
          if (num) violations.push(`Unverified metric "${num}" in project bullet: "${b}"`);
          return !num;
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
 * Same rule for the cover letter: sentences with numbers the fact bank can't
 * back up are removed. (The target company's name is expected, so names aren't checked.)
 * Numbers quoted from the job description itself are about the employer, so they're allowed.
 */
export function verifyAndSanitizeCoverLetter(text, factBank, { jobText = '' } = {}) {
  const violations = [];
  factBank = { ...factBank, trustedNumbers: new Set([...factBank.trustedNumbers, ...extractNumbers(jobText)]) };
  const sanitized = String(text || '')
    .split(/\n{2,}/)
    .map((para) => stripUnverifiedSentences(para, factBank, 'cover letter', violations))
    .filter(Boolean)
    .join('\n\n');
  return { verified: violations.length === 0, violations, text: sanitized };
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
