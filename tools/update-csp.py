#!/usr/bin/env python3
"""Refresh the script hashes in each page's Content-Security-Policy (index.html and projects/*.html).

Each page's JavaScript is inline. The CSP allows it by its SHA-256 hash, so ANY edit to
that script changes the hash and the browser will refuse to run it until the hash is updated.
Run this after every change to the inline script:

    python3 tools/update-csp.py          # rewrite the hash in place
    python3 tools/update-csp.py --check  # exit 1 if the hash is stale (used by tests/site/acceptance.py)
"""
import base64, hashlib, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGES = [ROOT / "index.html", *sorted((ROOT / "projects").glob("*.html"))]
EXEC_TYPES = ("", "text/javascript", "module", "application/javascript")


def script_hashes(html: str) -> list[str]:
    out = []
    for attrs, body in re.findall(r"<script([^>]*)>(.*?)</script>", html, re.S):
        if "src=" in attrs:
            continue
        m = re.search(r'type="([^"]*)"', attrs)
        if (m.group(1) if m else "") not in EXEC_TYPES:
            continue  # e.g. application/ld+json is data, never executed
        digest = hashlib.sha256(body.encode("utf-8")).digest()
        out.append("'sha256-" + base64.b64encode(digest).decode() + "'")
    return out


def refresh(page: pathlib.Path, check: bool) -> int:
    html = page.read_text(encoding="utf-8")
    name = page.relative_to(ROOT)
    m = re.search(r'(<meta http-equiv="Content-Security-Policy" content=")([^"]*)(")', html)
    if not m:
        print(f"No CSP meta tag found in {name}")
        return 1
    policy = m.group(2)
    want = " ".join(script_hashes(html))
    new_policy = re.sub(r"script-src (?:'sha256-[^']+' ?)*", "script-src " + want + " ", policy).replace(want + " ;", want + ";")
    if check:
        if new_policy != policy:
            print(f"{name}: CSP script hash is stale: run python3 tools/update-csp.py")
            return 1
        print(f"{name}: CSP script hash is current")
        return 0
    if new_policy == policy:
        print(f"{name}: CSP script hash already current")
        return 0
    page.write_text(html[: m.start(2)] + new_policy + html[m.end(2):], encoding="utf-8")
    print(f"{name}: updated CSP script-src to", want)
    return 0


def main() -> int:
    check = "--check" in sys.argv
    return max(refresh(p, check) for p in PAGES)


if __name__ == "__main__":
    sys.exit(main())
