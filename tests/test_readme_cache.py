import glob
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.components.simple_dialogs import (
    badge_download_url,
    get_logical_filename,
    resolve_readme_images,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE_DIR = os.path.join(ROOT, "assets", "cache")
README_PATTERNS = (
    r'!\[.*?\]\((https?://.*?)\)',
    r'<img.*?src=["\'](https?://.*?)["\']',
)


def readme_badge_urls():
    urls = set()
    for readme in sorted(glob.glob(os.path.join(ROOT, "Docs", "README*.md"))):
        with open(readme, encoding="utf-8") as f:
            text = f.read()
        for pattern in README_PATTERNS:
            urls.update(re.findall(pattern, text))
    return sorted(urls)


class TestBadgeDownloadUrl(unittest.TestCase):
    def test_png_extension_inserted_before_query(self):
        url = "https://img.shields.io/badge/Release-v5.0.0--Enterprise-emerald?style=for-the-badge&logo=shield"
        self.assertEqual(
            badge_download_url(url),
            "https://img.shields.io/badge/Release-v5.0.0--Enterprise-emerald.png?style=for-the-badge&logo=shield",
        )

    def test_existing_png_extension_untouched(self):
        url = "https://img.shields.io/badge/x-y-z.png?style=flat"
        self.assertEqual(badge_download_url(url), url)

    def test_non_shields_url_untouched(self):
        url = "https://example.com/logo.svg"
        self.assertEqual(badge_download_url(url), url)


class TestResolveReadmeImages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="readme_cache_")
        self.url = "https://img.shields.io/badge/Release-v5.0.0--Enterprise-emerald?style=for-the-badge"
        self.md = f"# Title\n\n[![Release]({self.url})](https://example.com)\n"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cached_badge_resolves_to_local_file(self):
        cached = os.path.join(self.tmp, get_logical_filename(self.url))
        with open(cached, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")

        md, missing = resolve_readme_images(self.md, ROOT, [self.tmp])
        self.assertEqual(missing, [])
        self.assertNotIn(self.url, md)
        self.assertIn("file:///", md)

    def test_uncached_badge_reported_missing(self):
        md, missing = resolve_readme_images(self.md, ROOT, [self.tmp])
        self.assertEqual(missing, [self.url])
        self.assertIn(self.url, md)

    def test_second_cache_dir_consulted(self):
        """First dir empty -> falls through to the bundled/second dir."""
        empty = os.path.join(self.tmp, "empty")
        populated = os.path.join(self.tmp, "populated")
        os.makedirs(empty)
        os.makedirs(populated)
        with open(os.path.join(populated, get_logical_filename(self.url)), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")

        md, missing = resolve_readme_images(self.md, ROOT, [empty, populated])
        self.assertEqual(missing, [])
        self.assertIn("file:///", md)

    def test_local_relative_images_still_resolve(self):
        assets_dir = os.path.join(self.tmp, "assets")
        os.makedirs(assets_dir)
        with open(os.path.join(assets_dir, "shot.png"), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")

        md, missing = resolve_readme_images("![Shot](../assets/shot.png)", self.tmp, [self.tmp])
        self.assertEqual(missing, [])
        self.assertIn("file:///", md)
        self.assertNotIn("../assets/shot.png", md)

    def test_html_img_tags_are_resolved(self):
        cached = os.path.join(self.tmp, get_logical_filename(self.url))
        with open(cached, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")

        md, missing = resolve_readme_images(f'<img src="{self.url}" alt="b">', ROOT, [self.tmp])
        self.assertEqual(missing, [])
        self.assertIn("file:///", md)


class TestShippedBadgeCache(unittest.TestCase):
    """The packaged cache must match the current READMEs, or first run goes to the network."""

    def test_every_readme_badge_has_a_png_in_assets_cache(self):
        urls = readme_badge_urls()
        self.assertTrue(urls, "no remote badge URLs found in Docs/README*.md")

        missing = []
        for url in urls:
            path = os.path.join(CACHE_DIR, get_logical_filename(url))
            if not os.path.exists(path):
                missing.append(f"{os.path.basename(path)} (missing)")
                continue
            with open(path, "rb") as f:
                if f.read(4) != b"\x89PNG":
                    missing.append(f"{os.path.basename(path)} (not a PNG)")
        self.assertEqual(missing, [], f"run scripts/prefetch_readme_badges.py: {missing}")


if __name__ == "__main__":
    unittest.main()
