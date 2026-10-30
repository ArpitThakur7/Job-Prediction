// Request guard for the local engine API.
//
// The engine listens on 127.0.0.1 and holds personal data (resume, profile,
// applications) plus endpoints that spend LLM quota. Binding to loopback is not
// enough on its own: any website open in the user's browser can send requests to
// 127.0.0.1. Two checks close that:
//
// 1. Host must be a loopback name. Defeats DNS rebinding, where an attacker's
//    domain is re-pointed at 127.0.0.1 so its pages become "same-origin".
// 2. Origin, when the browser sends one, must be on the allowlist (the frontend).
//    Browsers always send Origin on cross-origin requests and on all non-GET
//    requests, so other sites' writes and reads are refused. Requests without an
//    Origin (curl, scripts, the Next.js server-side proxy) are allowed.

import { resolve, sep } from 'node:path';

const LOOPBACK_HOSTS = new Set(['127.0.0.1', 'localhost', '[::1]', '::1']);

export const DEFAULT_ALLOWED_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000'];

export function allowedOrigins(env = process.env) {
  const raw = env.SALVO_ALLOWED_ORIGINS;
  if (!raw) return new Set(DEFAULT_ALLOWED_ORIGINS);
  return new Set(raw.split(',').map((s) => s.trim().replace(/\/$/, '')).filter(Boolean));
}

function hostnameOf(hostHeader = '') {
  if (hostHeader.startsWith('[')) return hostHeader.slice(0, hostHeader.indexOf(']') + 1);
  return hostHeader.split(':')[0].toLowerCase();
}

/**
 * Decide whether a request may proceed.
 * @returns {{ ok: true, origin: string | null } | { ok: false, status: number, reason: string }}
 */
export function checkRequest(headers, origins = allowedOrigins()) {
  const host = hostnameOf(headers.host);
  if (!LOOPBACK_HOSTS.has(host)) {
    return { ok: false, status: 421, reason: 'Host is not a loopback address' };
  }
  const origin = headers.origin;
  if (origin === undefined) return { ok: true, origin: null };
  if (origins.has(origin)) return { ok: true, origin };
  return { ok: false, status: 403, reason: 'Origin not allowed' };
}

/** CORS headers for an allowed origin; nothing for requests that sent no Origin. */
export function corsHeaders(origin) {
  if (!origin) return {};
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '600',
    Vary: 'Origin',
  };
}

/** True when `target` resolves to a path inside `dir` (not merely sharing its prefix). */
export function isInside(dir, target) {
  const base = resolve(dir);
  const full = resolve(target);
  return full === base || full.startsWith(base + sep);
}

export const MAX_BODY_BYTES = 2 * 1024 * 1024;
