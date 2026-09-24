import { scoreJob } from './filter.mjs';
import { loadYaml } from './config.mjs';

/**
 * Normalizes Salvo deterministic 0-5 score to 0-100
 */
export function scoreDeterministic(job, profile) {
  const result = scoreJob(job, profile);
  // Scale raw 0-5 to 0-100
  const relevanceScore = Math.max(0, Math.min(100, Math.round((result.score / 5.0) * 100)));
  return {
    relevanceScore,
    rawScore: result.score,
    reasons: result.reasons,
    blocked: result.blocked,
  };
}

/**
 * Heuristic fallback for XGBoost ML score when Python backend is unreachable.
 * Mirrors ml/predict.py feature computation.
 */
function heuristicMlScore(job, candidateSkills = ['react', 'node', 'typescript', 'python', 'nextjs']) {
  const desc = String(job.description || '').toLowerCase();
  const title = String(job.title || '').toLowerCase();

  const matchedSkills = candidateSkills.filter((s) => desc.includes(s) || title.includes(s));
  const overlapRatio = candidateSkills.length > 0 ? matchedSkills.length / candidateSkills.length : 0.5;
  const isRemote = /remote|worldwide|anywhere/.test(job.location?.toLowerCase() || '');
  const locMatch = isRemote ? 1.0 : 0.5;

  let baseProb = (overlapRatio * 0.6) + (locMatch * 0.4);
  return Math.max(0, Math.min(100, Math.round(baseProb * 100)));
}

/**
 * Calls Project 1's XGBoost ML matcher service or falls back to feature matching.
 */
export async function fetchMlPredictionScore(job, candidateProfile = null, apiBaseUrl = 'http://127.0.0.1:8000') {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);

    const res = await fetch(`${apiBaseUrl}/match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resume_id: candidateProfile?.id || 'default_candidate',
        job_id: job.id || job.url,
        features: {
          skill_overlap_ratio: 0.8,
          experience_gap: 0.0,
          education_score: 3,
          location_match: 1,
          category_match: 1,
          title_relevance: 1,
        },
      }),
      signal: controller.signal,
    });
    clearTimeout(timeout);

    if (res.ok) {
      const data = await res.json();
      const prob = data.data?.match_probability ?? data.match_probability ?? 0.85;
      return Math.round(prob * 100);
    }
  } catch {
    // Graceful fallback to local feature approximation
  }

  const skills = candidateProfile?.skills?.primary || ['react', 'node', 'typescript', 'python'];
  return heuristicMlScore(job, skills);
}

/**
 * Combines Salvo deterministic score with ML match prediction score
 */
export async function scoreJobCombined(job, profile, scoringConfig = null) {
  const cfg = scoringConfig || (await loadYaml('config/scoring.yaml').catch(() => null)) || {
    weights: { relevance: 0.6, prediction: 0.4 },
    thresholds: { apply_min: 65, high_confidence: 80 },
  };

  const det = scoreDeterministic(job, profile);
  const predictionScore = await fetchMlPredictionScore(job, profile);

  const wRel = cfg.weights?.relevance ?? 0.6;
  const wPred = cfg.weights?.prediction ?? 0.4;

  const combinedScore = Math.round((wRel * det.relevanceScore) + (wPred * predictionScore));

  return {
    combinedScore: det.blocked ? 0 : combinedScore,
    relevanceScore: det.relevanceScore,
    predictionScore,
    reasons: det.reasons,
    blocked: det.blocked,
    weights: { relevance: wRel, prediction: wPred },
    verdict: combinedScore >= (cfg.thresholds?.high_confidence || 80)
      ? 'Strong Match'
      : combinedScore >= (cfg.thresholds?.apply_min || 65)
      ? 'Match'
      : 'Moderate Match',
  };
}
