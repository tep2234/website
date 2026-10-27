# Visitor counter

## Why it needs a database
GitHub Pages only serves files. It cannot run code on the server or save anything, so it cannot count visits by itself.
None of the GitHub-only options give a real website count:

| Option | Why it doesn't work |
| --- | --- |
| GitHub Actions | Runs on pushes or schedules, not on page visits. A visitor's browser can't trigger it without a GitHub token, and a token in page code would let anyone write to the repo. |
| Writing a JSON file in the repo | Same problem: every write needs a token with write access. |
| Repository "Insights → Traffic" | Counts people viewing the repository on github.com, not the website. |
| `localStorage` | Lives in one visitor's browser. It can't add up visits from different people. |

## What this site does
`index.html` calls two database functions in a Supabase project you already have access to (no new account or third-party counter service):

- `record_visit(visitor_id, path)` stores one page view and returns the totals.
- `visit_stats()` returns totals only (used for bots and browsers that block storage).

The footer then shows **page views** and **unique visitors** separately, with the start date. Until the counter is configured, or if the database can't be reached, the footer shows nothing; it never shows a placeholder or made-up number.

### What the numbers mean
- **Page views:** visits recorded, ignoring refreshes of the same page by the same browser within 30 minutes.
- **Unique visitors:** distinct random IDs stored in visitors' browsers. One person on two devices, or someone who clears site data or browses privately, counts more than once. Treat it as an estimate.
- Automated browsers that identify themselves (search crawlers, link previews, Lighthouse) are not recorded.
- Counting starts on the day you switch it on; there is no history before that.

### Security
- The table has row-level security on and no policies, so the public key can't read or change rows directly.
- The public (anon) key in the page is designed to be public. It only allows the two functions above.
- No personal data is stored: no IP addresses, names or emails.
- Someone determined could still inflate the count by scripting many fake IDs. A per-minute cap (120 new rows) limits this.

## Switching it on
Your free Supabase plan allows two active projects. Both are in use (DALIguro and daliguro-staging). Do **not** put this in the DALIguro database. Pick one:

1. **Restore a paused project** you no longer need (e.g. `partsflow-pro` or `daliguro-ppt-studio`) after pausing another, or
2. **Upgrade** the plan to run a third project, or
3. **Create a new project** if you free a slot.

Then:
1. Open the project → **SQL editor** → paste and run `supabase/visitor-counter.sql`.
2. Copy the **Project URL** and the **anon public** key from **Project Settings → API**.
3. In `index.html`, find `var COUNTER={url:"",anonKey:""};` and fill both values.
4. Commit and push. The footer shows the count on the next visit.

To check it works: open the site, then run `select count(*) from site_visits;` in the SQL editor.
