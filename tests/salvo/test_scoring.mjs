import test from 'node:test';
import assert from 'node:assert/strict';
import { scoreDeterministic, scoreJobCombined } from '../../engine/lib/scoring.mjs';

const mockProfile = {
  target: {
    titles: ['software engineer', 'backend engineer'],
    exclude_titles: ['senior'],
    internship_titles: ['intern'],
    tech_domain_markers: ['software', 'engineer'],
  },
  location: {
    remote_only: true,
    allow: ['remote', 'worldwide', 'global'],
    deny: ['us citizen'],
  },
  skills: {
    primary: ['react', 'node', 'typescript', 'python'],
    secondary: ['mongodb', 'docker'],
  },
  preference: {
    boost_keywords: ['distributed'],
    penalty_keywords: [],
  },
  compensation: {
    deny: ['unpaid'],
  },
};

test('scoreDeterministic outputs normalized 0-100 score and explainable reasons', () => {
  const job = {
    title: 'Software Engineer',
    description: 'Looking for React and Node experience in a distributed team.',
    location: 'Global Remote',
  };

  const res = scoreDeterministic(job, mockProfile);
  assert.ok(res.relevanceScore >= 50 && res.relevanceScore <= 100);
  assert.equal(res.blocked, false);
  assert.ok(res.reasons.length >= 2);
});

test('scoreJobCombined blends deterministic score with prediction score', async () => {
  const job = {
    title: 'Software Engineer',
    description: 'React, Node, TypeScript developer',
    location: 'Worldwide',
  };

  const config = {
    weights: { relevance: 0.6, prediction: 0.4 },
    thresholds: { apply_min: 65, high_confidence: 80 },
  };

  const combined = await scoreJobCombined(job, mockProfile, config);
  assert.ok(combined.combinedScore >= 0 && combined.combinedScore <= 100);
  assert.ok(combined.relevanceScore >= 0 && combined.relevanceScore <= 100);
  assert.ok(combined.predictionScore >= 0 && combined.predictionScore <= 100);
  assert.ok(typeof combined.verdict === 'string');
});

test('ML prediction reports "heuristic" when the prediction API is unreachable', async () => {
  const { fetchMlPrediction } = await import('../../engine/lib/scoring.mjs');
  const res = await fetchMlPrediction(
    { title: 'Backend Engineer', description: 'Python and React', location: 'Remote' },
    null,
    'http://127.0.0.1:9' // nothing listens here
  );
  assert.equal(res.source, 'heuristic');
  assert.ok(res.score >= 0 && res.score <= 100);
});
