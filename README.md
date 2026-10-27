# Alvin Diaz Merasol — portfolio

Static site served by GitHub Pages at https://tep2234.github.io/website/. No build step for the page itself.

## Layout
| Path | What it is |
| --- | --- |
| `index.html` | The whole site: markup, styles and scripts in one file. |
| `assets/img`, `assets/media`, `assets/fonts` | Screenshots, screen recordings with posters, self-hosted fonts. |
| `resume/` | Résumé hub files: one PDF, Word file and print page per role. `resume-data.json` is the single source. |
| `tools/` | Scripts that rebuild the résumé files. |
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

## Notes
- Traffic: the footer shows a public page-view total from Abacus (free, no account); private analytics use Cloudflare Web Analytics once a site token is added. Neither uses Supabase. See `docs/VISITOR-COUNTER.md`.
- `robots.txt` only works at the root of a domain (`tep2234.github.io/robots.txt`), so this project site doesn't ship one. Submit `sitemap.xml` in Google Search Console instead.
- The contact form has no server. It opens the visitor's email app with the inquiry filled in, or copies it; it never claims a message was sent.
