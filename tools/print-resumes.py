"""Print each résumé HTML in resume/ to a text-based PDF. Run from the repo root after build-resumes.js."""
import asyncio, json, pathlib
from playwright.async_api import async_playwright
root = pathlib.Path(__file__).resolve().parent.parent
async def main():
    man = json.loads((root / "resume/manifest.json").read_text())
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        for m in man:
            await pg.goto((root / m["html"]).as_uri()); await pg.evaluate("document.fonts.ready"); await pg.wait_for_timeout(250)
            await pg.pdf(path=str(root / m["pdf"]), format="A4", print_background=False, prefer_css_page_size=True)
        await b.close()
    print("printed", len(man))
asyncio.run(main())
