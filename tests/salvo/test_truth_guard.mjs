import test from 'node:test';
import assert from 'node:assert/strict';
import { verifyAndSanitizeResume, verifyAndSanitizeCoverLetter, generateResumeDiff } from '../../engine/lib/truth-guard.mjs';

const mockFactBank = {
  masterText: 'Experienced with React, Node.js, and PostgreSQL. Worked at ACME Corp. Scaled system throughput by 50%.',
  portfolio: {
    projects: [
      { name: 'QuantumJobMatcher', description: 'AI platform with 94.2% precision.' },
      { name: 'CloudSync', description: 'Real-time sync engine.' },
    ],
  },
  normalizedTrusted: 'experienced with react node js and postgresql worked at acme corp scaled system throughput by 50 quantumjobmatcher cloudsync',
  trustedNumbers: new Set(['50%', '50', '94.2%', '94.2']),
  trustedProjects: ['quantumjobmatcher', 'cloudsync'],
};

test('truth-guard accepts grounded facts from master resume and portfolio', () => {
  const resume = {
    experience: [
      {
        company: 'ACME Corp',
        bullets: ['Scaled system throughput by 50% using React and Node.js.'],
      },
    ],
    projects: [
      {
        name: 'QuantumJobMatcher',
        bullets: ['Maintained 94.2% precision.'],
      },
    ],
  };

  const result = verifyAndSanitizeResume(resume, mockFactBank);
  assert.equal(result.verified, true);
  assert.equal(result.violations.length, 0);
  assert.equal(result.resume.experience[0].bullets.length, 1);
  assert.equal(result.resume.projects[0].bullets.length, 1);
});

test('truth-guard flags unverified employers and strips hallucinated metrics', () => {
  const hallucinatedResume = {
    experience: [
      {
        company: 'Google Deepmind', // Not in fact bank!
        bullets: ['Boosted revenue by 999% and saved $500M.'], // Fake metrics!
      },
    ],
    projects: [
      {
        name: 'FakeCryptoBot', // Not in fact bank!
        bullets: ['Invented 10x compression.'],
      },
    ],
  };

  const result = verifyAndSanitizeResume(hallucinatedResume, mockFactBank);
  assert.equal(result.verified, false);
  assert.ok(result.violations.length >= 2);
  // Fake project stripped
  assert.equal(result.resume.projects.length, 0);
  // Unverified employer removed entirely, bullets and all
  assert.equal(result.resume.experience.length, 0);
});

test('truth-guard keeps grounded bullets under a real employer while dropping invented metrics', () => {
  const result = verifyAndSanitizeResume(
    {
      experience: [{ company: 'ACME Corp', bullets: ['Scaled throughput by 50%.', 'Cut costs by 73%.'] }],
    },
    mockFactBank
  );
  assert.deepEqual(result.resume.experience[0].bullets, ['Scaled throughput by 50%.']);
  assert.ok(result.violations.some((v) => v.includes('73%')));
});

test('truth-guard checks the summary and skills', () => {
  const result = verifyAndSanitizeResume(
    {
      summary: 'Full-stack engineer working in React and Node.js. Led a team of 40 engineers.',
      skills: { languages: ['React', 'PostgreSQL', 'Kubernetes'] },
    },
    mockFactBank
  );
  assert.equal(result.resume.summary, 'Full-stack engineer working in React and Node.js.');
  assert.deepEqual(result.resume.skills.languages, ['React', 'PostgreSQL']);
  assert.ok(result.violations.some((v) => v.includes('Kubernetes')));
});

test('cover letter: invented numbers removed, numbers quoted from the job post kept', () => {
  const letter = 'I scaled throughput by 50%.\n\nI led 12 launches. Your team of 200 engineers inspires me.';
  const result = verifyAndSanitizeCoverLetter(letter, mockFactBank, { jobText: 'Join our 200-person team.' });
  assert.equal(result.verified, false);
  assert.equal(result.text, 'I scaled throughput by 50%.\n\nYour team of 200 engineers inspires me.');
});
