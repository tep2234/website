# Visitor analytics

The site uses two free services. Neither one uses Supabase or touches the DALIguro databases.

| | Public footer counter | Private analytics |
| --- | --- | --- |
| Service | [Abacus](https://v2.jasoncameron.dev/abacus) (`abacus.jasoncameron.dev`) | [Cloudflare Web Analytics](https://developers.cloudflare.com/web-analytics/) |
| Shows | Total **page views**, in the footer | Visits, page views, top pages, referrers, countries, devices, Core Web Vitals, in your Cloudflare dashboard only |
| Account needed | No | Yes, a free Cloudflare account and a site token |
| Status | **Working, with one blocker before merge:** the counter's admin key is treated as exposed and needs a replacement counter (see below). The current counter `tep2234-website/pageviews` reads 0. | **Waiting for your token.** Nothing is loaded until it is added. |

## Footer counter (Abacus)

### How it works
On each page load the browser makes one GET request to Abacus:

- `/hit/tep2234-website/pageviews` adds 1 and returns the new total, or
- `/get/tep2234-website/pageviews` returns the total without adding anything.

The footer then shows "Site traffic: **N** page views". No key or secret is in the page; the hit and get endpoints are public by design.

### When a view is counted
- Counted: a visible page in a normal browser.
- Not counted, total still shown (uses `/get`): a refresh or return visit from the same browser within 30 minutes; browsers sending Do Not Track or Global Privacy Control; automated browsers (`navigator.webdriver`, headless Chrome, crawlers, link previews, Lighthouse); browsers that block storage.
- A tab opened in the background is counted only when someone switches to it.

### Why it shows page views only
Abacus stores a single number. It can't tell people or devices apart, so the site does not show "unique visitors". Cloudflare's dashboard gives an estimate of visits for your own use.

### When it stays hidden
The footer line appears only after Abacus returns a whole number. A confirmed 0 is shown as "0 page views". It stays hidden if the request fails, times out (6 s), is rate-limited, returns 404, or returns anything else. There is no placeholder number.

### Limitations
- **Not tamper-proof.** The 30-minute rule runs in the visitor's browser. Anyone can call the public `/hit` URL directly and raise the count (Abacus limits each IP address to 30 requests per 10 seconds). Treat the number as an approximate total, not an audited figure.
- **Ad and privacy blockers** may block the request. Those visits aren't counted, and the line stays hidden for those visitors.
- **No SLA.** Abacus is a free community service run by one developer. If it goes down, the line hides itself; the rest of the site is unaffected.
- **Expiry.** Abacus keeps a counter for 6 months after its last access. Any visit resets that clock.

### Admin key: treat as exposed, replacement pending
Creating a counter with `/create` returns an admin key that can set, reset or delete it. The key for `tep2234-website/pageviews` was shown in a chat conversation, so it is treated as exposed. It has never been in this repository, its history, the pull request or the page code.

**Abacus can't rotate or revoke an admin key.** Its documentation lists only `/delete`, `/set`, `/reset` and `/update` for admin keys, with no endpoint to regenerate one. The only fix is a new counter whose key nobody else has seen. Do this before merging:

1. **Create the new counter yourself** in your own browser, so the key never passes through anyone else. Open:
   `https://abacus.jasoncameron.dev/create/tep2234-website/<new-name>`
   The page shows JSON with `admin_key`. Save that value straight into your password manager. Don't paste it into chats, issues, commits or this file.
2. **Point the page at it.** In `index.html`, change `key:"pageviews"` in `var PAGEVIEWS={...}` to the new name, then commit to this PR.
3. **Retire the old counter** (optional; needs the old key): `POST https://abacus.jasoncameron.dev/delete/tep2234-website/pageviews` with header `Authorization: Bearer <old key>`. After that the old key no longer controls anything.
4. **Check it.** `https://abacus.jasoncameron.dev/info/tep2234-website/<new-name>` should show `"exists":true` and `"is_genuine":false`. Abacus documents `is_genuine` as false when a counter was made with `/create`, so an admin key exists.

Only the counter name goes in the page. The name is public by design; the admin key is the secret.

## Cloudflare Web Analytics (private dashboard)

Free, no cookies, no fingerprinting. Cloudflare's docs say it is free and allows up to 10 sites that aren't proxied through Cloudflare. It does **not** offer a public count endpoint, so it isn't used for the footer. DNS, the domain and GitHub Pages hosting stay as they are.

### What you need to do (about 5 minutes)
1. Sign up or log in at <https://dash.cloudflare.com/sign-up> (free plan).
2. Open **Web Analytics** (type "Web Analytics" in the dashboard search if it isn't in the menu) and select **Add a site**.
3. Under **Set up hostname**, enter `tep2234.github.io`, confirm, and select **Done**. Don't add the domain to Cloudflare or change any DNS or nameserver settings; the JS snippet works without them.
4. Open **Manage site** and copy the JS snippet. It looks like this; the token is a 32-character code:
   ```html
   <script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{"token": "YOUR_TOKEN"}'></script>
   ```
5. Send the token to Claude, or paste the snippet yourself in `index.html` in place of the line
   `<!-- Cloudflare Web Analytics: not active. ... -->`, just before `</body>`.
6. After merge, data appears in the dashboard within a few minutes of the first visit.

Ad blockers such as Brave, Adblock Plus and DuckDuckGo can block the Cloudflare beacon, so the dashboard undercounts visitors who use them.

## Verification (28 Oct 2026)

**Against the real Abacus service**, run from `https://tep2234.github.io` in a desktop browser on a test counter (`tep2234-website-qa/live-check-1028`), using the exact code from `index.html`:

| Check | Result |
| --- | --- |
| First visit | `/hit`; footer showed "1 page view" |
| Two refreshes | `/get` only; still "1 page view" |
| Second browser (new storage) | `/hit`; "2 page views" |
| Read back from the service | `{"value":2}` |
| Cross-origin access from github.io | Works (no CORS error) |
| Request time | 296–446 ms per request |

**Simulated service** (`tests/page-views/browser_tests.py`, Chromium via Playwright, Abacus replaced by a local fake with one shared count): 34/34 checks passed, run 3 times. Covered:

- recording, refreshes, 31-minute return, multiple browsers and a shared persisted total;
- Do Not Track, Global Privacy Control, automation and blocked storage;
- background tabs;
- 12 failure cases (500, 429, 404, refused, timeout, bad or invalid values);
- network requests (the counter is the only third-party request);
- performance (the request starts after the HTML has arrived, and a hung API doesn't delay page load);
- 390 px and 1440 px, light and dark themes, reduced motion, axe accessibility scan.

**Rest of the site:** functional suite 58/58; axe 0 violations at 1440 px and 390 px, light and dark; no sideways scrolling.

**Not verified:** iPhone Safari and in-app browsers (Facebook, Messenger) on a real phone; the Cloudflare beacon, which needs your token.

## Removed
The earlier Supabase counter (`supabase/visitor-counter.sql`, `tests/visitor-counter/`, and its frontend code) has been removed. It is in git history at commit `39ee1f4` if ever needed.
