# Visitor counter

**Status: built and tested, switched off.** `index.html` ships with `var COUNTER={url:"",anonKey:""};`, so the page makes no counter request and the footer shows nothing. It switches on only when a database is chosen and approved (see "Switching it on").

## Why it was inactive
1. `COUNTER.url` and `COUNTER.anonKey` are empty, so the script exits before any request. That is deliberate: no database had been approved.
2. There is no free slot to host the database. The Supabase organization is on the **Free plan**, which allows **two active free projects**. Both are DALIguro: `DaliGuro` (production) and `daliguro-staging`. The other three projects (`partsflow-pro`, `daliguro-ppt-studio`, `daliguro-qr-assessment`) are paused. Portfolio analytics must not go into a DALIguro database, and no project was created, paused or restored without the owner's approval.

## Why it needs a database
GitHub Pages only serves files. It cannot run code on the server or save anything, so it cannot count visits by itself.

| Option | Why it doesn't work |
| --- | --- |
| GitHub Actions | Runs on pushes or schedules, not on page visits. A visitor's browser can't trigger it without a GitHub token, and a token in page code would let anyone write to the repo. |
| Writing a JSON file in the repo | Same problem: every write needs a token with write access. |
| Repository "Insights → Traffic" | Counts people viewing the repository on github.com, not the website. |
| `localStorage` | Lives in one visitor's browser. It can't add up visits from different people. |

## How it works
The page calls two database functions through Supabase's REST API. No third-party counter service, no GoatCounter account.

- `record_visit(visitor_id, path)` records one page view if it qualifies, then returns the totals.
- `visit_stats()` returns the totals only.

The footer shows **page views** and **estimated unique visitors** separately, with the month counting started. If the counter isn't configured, the request fails, times out (6 s) or returns anything other than valid totals, the footer line stays hidden. It never shows a placeholder or a made-up number.

### What the numbers mean
- **Page views:** one per browser, per page, per 30 minutes. Refreshing inside 30 minutes does not add views. This is enforced in the database; the browser also skips the write so it doesn't send pointless requests.
- **Estimated unique visitors:** distinct random IDs kept in visitors' browsers. One person on two devices, or someone who clears site data or browses privately, counts more than once.
- **Not recorded (totals still shown):** browsers that send Do Not Track or Global Privacy Control, automated browsers (`navigator.webdriver`, headless Chrome, crawlers, link previews, Lighthouse), and browsers that block storage.
- A tab opened in the background or prerendered is counted only when someone actually looks at it.
- Counting starts on the day it's switched on. There is no history before that.

### Security and abuse controls (`supabase/visitor-counter.sql`)
- Data lives in a private schema, `portfolio_analytics`, which the REST API does not expose. Its tables have row-level security on, no policies, and all privileges revoked from `anon` and `authenticated`.
- The public key can call only the two functions. `EXECUTE` is revoked from `PUBLIC`, `anon` and `authenticated` (Supabase grants it by default), then granted to `anon` only.
- Both functions are `SECURITY DEFINER` with `search_path = ''` and fully qualified names, and a 2-second `statement_timeout`.
- Input validation: the visitor id must be a UUID (PostgreSQL rejects anything else with HTTP 400). Query strings and fragments are stripped from the path; anything not matching `^/[A-Za-z0-9/_.~-]{0,199}$` is stored as `/`. A `CHECK` constraint enforces the same rule on the table.
- Concurrency: each write locks the single totals row (`SELECT … FOR UPDATE`), so the 30-minute check, the caps and the totals update happen as one step. Simultaneous refreshes can't double-count.
- Abuse caps: at most 120 new page views per minute site-wide and at most 30 new browser ids per minute. Above that, requests return totals without recording.
- Totals are kept in a one-row table, so reading the counter doesn't scan the visit log.
- No personal data is stored: no IP address, user agent, name or email. Only a random id, the page path and the time.
- Residual risk: someone scripting requests can still add up to the caps (about 30 fake visitors and 120 fake views per minute). The anon key is public by design, so this can be limited but not prevented without a server or CAPTCHA.

## Switching it on (needs your approval)
Cheapest safe option first:

1. **New free organization (₱0).** Supabase lets you create another Free Plan organization; its two free project slots are separate from the DALIguro organization. Create the organization and one project in it (for example `portfolio-analytics`). DALIguro is not touched.
2. **Reuse a paused project.** Restoring `partsflow-pro`, `daliguro-ppt-studio` or `daliguro-qr-assessment` needs a free slot, which means pausing DALIguro production or staging. Not recommended.
3. **Pro plan.** USD 25/month (includes USD 10 of compute credit, enough for one project); each extra project is roughly USD 10/month.

Free projects pause after a period of inactivity. A paused project makes the counter hide itself until the project is restored; no wrong numbers are shown.

Then:
1. In the new project open **SQL editor**, paste `supabase/visitor-counter.sql`, run it. It's safe to run again.
2. From **Project Settings → API Keys**, copy the **Project URL** and the **publishable** key (`sb_publishable_…`) or the legacy **anon** key. Never use the secret or `service_role` key.
3. In `index.html`, fill `var COUNTER={url:"https://<ref>.supabase.co",anonKey:"<key>"};`.
4. Commit and push. Open the site once, then check in the SQL editor:
   `select * from portfolio_analytics.totals;`

## Tests
Run against PostgreSQL 17.5 with Supabase-style roles and default privileges (scripts in `tests/visitor-counter/`):

- `sql_tests.sh`: 37 checks covering recording, 30-minute window, input validation, permissions, caps and totals drift.
- `concurrency.sh`: 50 simultaneous refreshes from one browser record exactly 1 view; 25 simultaneous new browsers record exactly 25.
- The browser behaviour (real database behind PostgREST, failure modes, privacy signals, hidden tabs) was tested with Playwright and Chromium.
