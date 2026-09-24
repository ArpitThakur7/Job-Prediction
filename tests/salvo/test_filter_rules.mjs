import test from 'node:test';
import assert from 'node:assert/strict';
import {
  requiresExperience,
  titleMatches,
  locationMatches,
  scoreJob,
  applyFilters,
} from '../../engine/lib/filter.mjs';

const mockProfile = {
  freshness_days: 21,
  target: {
    titles: ['software engineer', 'backend engineer', 'frontend engineer', 'full stack engineer'],
    exclude_titles: ['senior', 'lead', 'staff', 'principal', 'manager', 'director'],
    internship_titles: ['intern', 'internship', 'new grad'],
    tech_domain_markers: ['software', 'engineering', 'backend', 'frontend', 'developer', 'ai', 'data'],
  },
  location: {
    remote_only: true,
    allow: ['remote', 'worldwide', 'anywhere', 'global', 'india', 'emea', 'apac'],
    deny: ['us citizen', 'security clearance', 'w2 only'],
  },
  skills: {
    primary: ['react', 'node', 'typescript', 'python'],
    secondary: ['docker', 'mongodb', 'postgresql', 'tailwind'],
  },
  preference: {
    boost_keywords: ['distributed', 'async', 'remote-first'],
    penalty_keywords: ['contract to hire', 'c2c'],
  },
  compensation: {
    deny: ['unpaid', 'for credit only', '0/hr', 'equity only'],
  },
  scoring: {
    apply_min: 2.0,
    daily_apply_target: 25,
    max_per_company: 3,
  },
};

test('requiresExperience correctly gates out 2+ years while permitting 0-1 and 0-2 years', () => {
  assert.equal(requiresExperience('requires 3+ years of experience'), true);
  assert.equal(requiresExperience('minimum 5 years software development'), true);
  assert.equal(requiresExperience('2-4 years in backend development'), true);

  // Beginner allowed
  assert.equal(requiresExperience('0-2 years of experience'), false);
  assert.equal(requiresExperience('0-1 years or new graduate'), false);
  assert.equal(requiresExperience('no prior experience required'), false);
});

test('titleMatches matches target and rejects exclusions', () => {
  assert.equal(titleMatches({ title: 'Software Engineer' }, mockProfile.target), true);
  assert.equal(titleMatches({ title: 'Senior Software Engineer' }, mockProfile.target), false);
  assert.equal(titleMatches({ title: 'Engineering Manager' }, mockProfile.target), false);

  // Internship requires tech domain marker
  assert.equal(titleMatches({ title: 'Software Engineering Intern' }, mockProfile.target), true);
  assert.equal(titleMatches({ title: 'Finance Analytics Intern' }, mockProfile.target), false);
});

test('locationMatches enforces remote gates and denies restricted phrases', () => {
  assert.equal(locationMatches({ location: 'Remote', title: 'SWE', description: 'Work anywhere' }, mockProfile.location), true);
  assert.equal(locationMatches({ location: 'United States Only (Remote)', title: 'SWE', description: 'Remote' }, mockProfile.location), false);
  assert.equal(locationMatches({ location: 'Austin, TX (Hybrid)', title: 'SWE', description: '3 days office' }, mockProfile.location), false);
  assert.equal(locationMatches({ location: 'Remote', title: 'SWE', description: 'Requires US Citizen clearance' }, mockProfile.location), false);
});

test('scoreJob returns deterministic score and explainable reasons', () => {
  const job = {
    title: 'Software Engineer',
    description: 'Looking for a developer with React, Node, and TypeScript experience. Remote-first team.',
    location: 'Worldwide Remote',
  };

  const scored = scoreJob(job, mockProfile);
  assert.ok(scored.score > 2.0, `Expected score > 2.0, got ${scored.score}`);
  assert.equal(scored.blocked, false);
  assert.ok(scored.reasons.some((r) => r.includes('title match')));
  assert.ok(scored.reasons.some((r) => r.includes('stack')));
  assert.ok(scored.reasons.some((r) => r.includes('open globally')));
});

test('applyFilters filters, scores and sorts jobs descending', () => {
  const jobs = [
    { title: 'Software Engineer', description: 'React Node full time', location: 'Global Remote', postedAt: Date.now() },
    { title: 'Senior Architect', description: 'Lead systems', location: 'Global Remote', postedAt: Date.now() }, // off-title
    { title: 'Software Engineer', description: '5+ years experience required', location: 'Global Remote', postedAt: Date.now() }, // requires-exp
    { title: 'Backend Engineer', description: 'Node Python developer', location: 'Remote', postedAt: Date.now() },
  ];

  const { jobs: kept, stats } = applyFilters(jobs, mockProfile);
  assert.equal(kept.length, 2);
  assert.equal(stats.title, 1);
  assert.equal(stats.experience, 1);
  assert.ok(kept[0].score >= kept[1].score);
});
