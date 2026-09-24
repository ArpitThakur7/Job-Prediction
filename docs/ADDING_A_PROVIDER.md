# 🔌 Guide: Adding a New Discovery Provider

Salvo auto-discovers every provider file placed in `engine/providers/`.
To add a new discovery source, create a file `engine/providers/<name>.mjs` (avoid names starting with `_`).

---

## The Provider Contract

Every provider must export a default object conforming to:

```typescript
interface Provider {
  id: string; // Unique identifier (e.g., 'greenhouse', 'workday')
  detect(entry: BoardEntry): { url: string } | null;
  fetch(entry: BoardEntry, options?: FetchOptions): Promise<JobRecord[]>;
}
```

---

## Template Implementation

```javascript
// engine/providers/my-custom-board.mjs
import { fetchJsonWithRetry, toEpochMs } from './_http.mjs';

const ALLOWED_HOSTS = new Set(['api.example.com']);

function assertUrl(url) {
  const parsed = new URL(url);
  if (parsed.protocol !== 'https:') throw new Error('Must use HTTPS');
  if (!ALLOWED_HOSTS.has(parsed.hostname)) throw new Error('Untrusted host');
  return url;
}

export default {
  id: 'my-board',

  /**
   * Return non-null if this provider can handle the board entry.
   */
  detect(entry) {
    if (entry.provider === 'my-board') return { url: entry.api };
    if (entry.careers_url && entry.careers_url.includes('example.com/careers')) {
      return { url: entry.careers_url };
    }
    return null;
  },

  /**
   * Fetch and normalize job records.
   * Return an array of normalized Job objects.
   */
  async fetch(entry, options = {}) {
    const apiUrl = `https://api.example.com/v1/jobs/${encodeURIComponent(entry.slug)}`;
    assertUrl(apiUrl);

    const json = await fetchJsonWithRetry(apiUrl, { redirect: 'error' });
    const rawJobs = Array.isArray(json?.data) ? json.data : [];

    return rawJobs.map((j) => ({
      title: String(j.title),
      url: String(j.application_url || j.url),
      company: entry.name,
      location: j.location_name || 'Remote',
      description: j.description_text || '',
      postedAt: toEpochMs(j.created_at),
      source: 'my-board',
      ats: 'my-board',
    }));
  },
};
```

---

## Rules for Providers
1. **Public Zero-Auth Endpoints Only**: Never scrape login-gated or bot-protected sites (no LinkedIn/Indeed/Naukri scraping). Honor robots.txt.
2. **Use `_http.mjs`**: Always use `fetchJsonWithRetry` or `fetchTextWithRetry` to ensure uniform user-agent, timeouts, and jittered backoff.
3. **Validate URLs**: Always assert HTTPS and trusted hostnames.
4. **Register in `boards.yaml`**: Add test company entries to `engine/config/boards.yaml` and verify with `node engine/verify-boards.mjs`.
