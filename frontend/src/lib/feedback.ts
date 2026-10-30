import { SalvoJob } from "@/lib/salvoClient";

export type FeedbackAction = "apply" | "save" | "dismiss" | "interview" | "offer" | "reject";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

/**
 * Tell the prediction API what the user did with a job. These events become
 * real training labels for the next retrain. Fire-and-forget: the UI never waits on it.
 */
export function sendFeedback(job: SalvoJob, action: FeedbackAction) {
  fetch(`${API_BASE}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    keepalive: true,
    body: JSON.stringify({
      job_url: job.url,
      title: job.title,
      company: job.company,
      action,
      description: job.description?.slice(0, 4000),
      relevance_score: job.relevanceScore,
      prediction_score: job.predictionScore,
    }),
  }).catch(() => {
    // Prediction API offline — the action itself still succeeds in the UI.
  });
}
