# scripts/prefetch_readme_badges.py
"""Prefetches README badge images into assets/cache for offline first-run rendering.

Scans Docs/README*.md for remote image URLs, downloads each one as a real PNG
and stores it under assets/cache/<logical-name>, using the same naming function
the README viewer resolves at runtime (get_logical_filename). The assets/ tree
is bundled by the PyInstaller specs, so the packaged app renders the README
without any network access.

Re-run this script whenever a README badge URL changes.

Usage:
    python scripts/prefetch_readme_badges.py            # fetch missing badges
    python scripts/prefetch_readme_badges.py --force    # re-fetch everything
    python scripts/prefetch_readme_badges.py --prune    # also delete cache files
                                                        # no longer referenced

Exit codes: 0 = all badges present, 1 = one or more downloads failed.
"""

import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.components.simple_dialogs import badge_download_url, get_logical_filename

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE_DIR = os.path.join(ROOT, "assets", "cache")

IMG_PATTERNS = (
    r'!\[.*?\]\((https?://.*?)\)',
    r'<img.*?src=["\'](https?://.*?)["\']',
)


def collect_badge_urls():
    """Every remote image URL referenced by the localized READMEs."""
    urls = set()
    for readme in sorted(glob.glob(os.path.join(ROOT, "Docs", "README*.md"))):
        with open(readme, encoding="utf-8") as f:
            text = f.read()
        for pattern in IMG_PATTERNS:
            urls.update(re.findall(pattern, text))
    return sorted(urls)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Re-download even if cached.")
    parser.add_argument("--prune", action="store_true", help="Delete cache files no longer referenced.")
    args = parser.parse_args()

    import requests

    os.makedirs(CACHE_DIR, exist_ok=True)
    urls = collect_badge_urls()
    if not urls:
        print("No remote badge URLs found in Docs/README*.md")
        return 0

    headers = {"User-Agent": "Mozilla/5.0"}
    expected = set()
    failures = 0
    print(f"Badge cache: {CACHE_DIR}")
    print(f"Referenced badges: {len(urls)}\n")

    for url in urls:
        filename = get_logical_filename(url)
        expected.add(filename)
        path = os.path.join(CACHE_DIR, filename)

        if os.path.exists(path) and not args.force:
            with open(path, "rb") as f:
                is_png = f.read(4) == b"\x89PNG"
            state = "cached" if is_png else "cached (NOT a PNG — rerun with --force)"
            if not is_png:
                failures += 1
            print(f"  [skip] {filename} ({state})")
            continue

        try:
            r = requests.get(badge_download_url(url), headers=headers, timeout=20)
            if r.status_code != 200:
                print(f"  [FAIL] {filename} — HTTP {r.status_code}")
                failures += 1
                continue
            if r.content[:4] != b"\x89PNG":
                print(f"  [FAIL] {filename} — server returned non-PNG content")
                failures += 1
                continue
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"  [ ok ] {filename} ({len(r.content)} bytes)")
        except requests.RequestException as e:
            print(f"  [FAIL] {filename} — {e}")
            failures += 1

    if args.prune:
        for existing in sorted(os.listdir(CACHE_DIR)):
            if existing not in expected:
                os.remove(os.path.join(CACHE_DIR, existing))
                print(f"  [prune] {existing} (no longer referenced)")

    print()
    if failures:
        print(f"RESULT: {failures} badge(s) unavailable. Re-run when online; "
              "the app still works, those badges just render from the network.")
        return 1
    print(f"RESULT: all {len(expected)} badges present in assets/cache as PNG.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
