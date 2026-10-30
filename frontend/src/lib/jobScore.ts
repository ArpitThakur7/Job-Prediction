import { SalvoJob } from "@/lib/salvoClient";

/** Fit score 0–100 for a job: the blended score when present, else the rule score (0–5) scaled. */
export function jobScore(job: SalvoJob): number {
  if (typeof job.combinedScore === "number") return job.combinedScore;
  if (typeof job.score === "number") return Math.round((job.score / 5) * 100);
  return 0;
}

export function fitColor(score: number): string {
  if (score >= 75) return "#0FB97C";
  if (score >= 55) return "#E9A23B";
  return "#9C8FCB";
}

export function fitLabel(score: number): string {
  if (score >= 75) return "Strong fit";
  if (score >= 55) return "Possible fit";
  return "Long shot";
}

export function isRemote(job: SalvoJob) {
  return /remote|anywhere|worldwide|wfh/i.test(job.location || "");
}

export function isEarlyCareer(job: SalvoJob) {
  return !!job.isInternship || /intern|junior|entry|graduate|trainee|apprentice/i.test(job.title || "");
}

export function isSenior(job: SalvoJob) {
  return /senior|lead|principal|staff|architect|head of/i.test(job.title || "");
}

export function jobSource(job: SalvoJob) {
  return (job.source || job.ats || "web").toLowerCase();
}
