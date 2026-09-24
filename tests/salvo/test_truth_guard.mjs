import test from 'node:test';
import assert from 'node:assert/strict';
import { verifyAndSanitizeResume, generateResumeDiff } from '../../engine/lib/truth-guard.mjs';

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
  // Hallucinated bullet stripped
  assert.equal(result.resume.experience[0].bullets.length, 0);
});
