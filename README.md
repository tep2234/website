# Alvin Diaz Merasol — portfolio

Static site served by GitHub Pages at https://tep2234.github.io/website/. No build step for the page itself.

## Layout
| Path | What it is |
| --- | --- |
| `index.html` | The home page: markup, styles and scripts in one file. Includes the project reel (the swipeable carousel in Featured projects). |
| `projects/daliguro.html` | DALIguro case study page: folder-to-page transition, recording with captions and chapters, scroll-told story, live item-analysis demo. Its font and colour tokens are copied from `index.html`; keep them in step. |
| `assets/js/chibi.js` | Chibi Alvin: the animated guide on the home page (follows the mouse, points at folders, offers a 60-second tour), the corner companion on wide screens, tool reactions, easter eggs and the 404 character. Loads after the page, never blocks it. |
| `assets/img/alvin-sprite.webp` | His sprite sheet: 9 columns × 11 rows of 384 px frames. Rebuild with `python3 tools/make-chibi-sprite.py --site`. |
| `assets/img/dg/` | Stills taken from the DALIguro recording. `assets/media/daliguro-app.vtt` holds its captions. |
| `assets/img`, `assets/media`, `assets/fonts` | Screenshots, screen recordings with posters, self-hosted fonts. |
| `resume/` | Résumé hub files: one PDF, Word file and print page per role. `resume-data.json` is the single source. |
| `tools/` | Scripts that rebuild the résumé files. |
| `tests/site/acceptance.py` | Site acceptance tests: features, 8 screen widths, axe WCAG 2.2 AA, performance (Playwright + Chromium), plus the reel and the case study page (layout, axe, CSP, mobile CLS/LCP/blocking-time budget). |
| `tests/resume/ats_check.py` | ATS checks for all 9 résumé versions in PDF, DOCX and HTML (needs pypdf and pandoc). |
| `tests/page-views/` | Browser tests for the footer page-view counter. See `docs/VISITOR-COUNTER.md`. |
| `sitemap.xml` | Sitemap for search engines. |

## Updating the résumé
Edit `resume/resume-data.json` only, then from the repo root:

```bash
node tools/build-resumes.js      # Word files, print pages, manifest
python3 tools/print-resumes.py   # text-based PDFs (needs Playwright with Chromium)
```

The résumé hub on the home page reads its role list from the manifest data embedded in `index.html`; update that block too if you add or rename a role.

## Deploying
Merging to `main` runs `.github/workflows/static.yml`, which publishes the repository to GitHub Pages.

## Content Security Policy
Every page allows its inline scripts by hash. After editing any inline script, run `python3 tools/update-csp.py` (it covers `index.html` and `projects/*.html`).

## Notes
- Traffic: the footer shows a public page-view total from Abacus (free, no account); private analytics use Cloudflare Web Analytics once a site token is added. Neither uses Supabase. See `docs/VISITOR-COUNTER.md`.
- `robots.txt` only works at the root of a domain (`tep2234.github.io/robots.txt`), so this project site doesn't ship one. Submit `sitemap.xml` in Google Search Console instead.
- The contact form has no server. It opens the visitor's email app with the inquiry filled in, or copies it; it never claims a message was sent.
