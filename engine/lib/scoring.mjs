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

const ML_API_URL = process.env.ML_API_URL || 'http://127.0.0.1:8000';

/**
 * Scores a job with the trained model via the prediction API, which computes
 * real features from this job's text and the master resume. Falls back to a
 * keyword heuristic when the API is down, and says so in `source`.
 * @returns {Promise<{ score: number, source: 'model' | 'heuristic' }>}
 */
export async function fetchMlPrediction(job, candidateProfile = null, apiBaseUrl = ML_API_URL) {
  try {
    const res = await fetch(`${apiBaseUrl}/match/score-job`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: job.title || '',
        description: String(job.description || '').slice(0, 100_000),
        company: job.company || '',
        location: job.location || '',
      }),
      // First call loads the model and embeddings; later calls are fast.
      signal: AbortSignal.timeout(8000),
    });
    if (res.ok) {
      const { data } = await res.json();
      const prob = data?.model_probability ?? data?.match_probability;
      if (typeof prob === 'number') return { score: Math.round(prob * 100), source: 'model' };
    }
  } catch {
    // Prediction API offline: fall through to the local estimate.
  }

  const skills = candidateProfile?.skills?.primary || ['react', 'node', 'typescript', 'python'];
  return { score: heuristicMlScore(job, skills), source: 'heuristic' };
}

/** Backward-compatible number-only form. */
export async function fetchMlPredictionScore(job, candidateProfile = null, apiBaseUrl = ML_API_URL) {
  return (await fetchMlPrediction(job, candidateProfile, apiBaseUrl)).score;
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
  const { score: predictionScore, source: predictionSource } = await fetchMlPrediction(job, profile);

  const wRel = cfg.weights?.relevance ?? 0.6;
  const wPred = cfg.weights?.prediction ?? 0.4;

  const combinedScore = Math.round((wRel * det.relevanceScore) + (wPred * predictionScore));

  return {
    combinedScore: det.blocked ? 0 : combinedScore,
    relevanceScore: det.relevanceScore,
    predictionScore,
    predictionSource,
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
