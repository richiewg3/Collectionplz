#!/usr/bin/env python3
"""Download modern game map PNGs from vgmaps.com atlas index pages."""

from __future__ import annotations

import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict

TARGET_GAMES = OrderedDict(
    {
        "shantae-and-the-pirates-curse": {
            "page": "https://vgmaps.com/Atlas/3DS/index.htm",
            "names": ["Shantae and the Pirate's Curse", "Shantae and the Pirates Curse"],
        },
        "stardew-valley": {
            "page": "https://vgmaps.com/Atlas/PC/index.htm",
            "names": ["Stardew Valley"],
        },
        "chained-echoes": {
            "page": "https://vgmaps.com/Atlas/PC/index.htm",
            "names": ["Chained Echoes"],
        },
    }
)

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}



def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())



def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read()
    return data.decode("latin-1", errors="replace")



def discover_png_urls(index_html: str, index_url: str, game_names: list[str]) -> list[str]:
    normalized_names = {normalize(name) for name in game_names}

    # Each game is generally in a single <table> block on vgmaps index pages.
    tables = re.findall(r"<table\b.*?</table>", index_html, flags=re.IGNORECASE | re.DOTALL)
    urls: list[str] = []

    for table in tables:
        compact = normalize(re.sub(r"<[^>]+>", " ", table))
        if not any(name in compact for name in normalized_names):
            continue

        for href in re.findall(r'href\s*=\s*"([^"]+\.png)"', table, flags=re.IGNORECASE):
            urls.append(urllib.parse.urljoin(index_url, href))

    # Fallback: scan the full page if table-level matching yielded nothing.
    if not urls:
        all_hrefs = re.findall(r'href\s*=\s*"([^"]+\.png)"', index_html, flags=re.IGNORECASE)
        for href in all_hrefs:
            href_norm = normalize(href)
            if any(name in href_norm for name in normalized_names):
                urls.append(urllib.parse.urljoin(index_url, href))

    # Stable dedupe preserving original order.
    return list(OrderedDict.fromkeys(urls))



def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)



def download_file(url: str, destination: str) -> None:
    req = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(req, timeout=120) as response, open(destination, "wb") as handle:
        handle.write(response.read())



def main() -> int:
    page_cache: dict[str, str] = {}
    summary: dict[str, dict[str, int]] = {}

    for slug, config in TARGET_GAMES.items():
        page_url = config["page"]
        page_html = page_cache.get(page_url)
        if page_html is None:
            print(f"Fetching index: {page_url}")
            page_html = fetch_html(page_url)
            page_cache[page_url] = page_html

        png_urls = discover_png_urls(page_html, page_url, config["names"])
        target_dir = os.path.join("references", "maps", slug)
        ensure_dir(target_dir)

        print(f"\nGame: {slug}")
        print(f"Found {len(png_urls)} PNG URL(s).")
        for found_url in png_urls:
            print(f"  URL: {found_url}")

        downloaded = 0
        skipped = 0

        for idx, url in enumerate(png_urls, start=1):
            filename = os.path.basename(urllib.parse.urlparse(url).path)
            destination = os.path.join(target_dir, filename)

            if os.path.exists(destination):
                skipped += 1
                print(f"[{slug}] {idx}/{len(png_urls)} skip existing: {filename}")
                continue

            try:
                print(f"[{slug}] {idx}/{len(png_urls)} downloading: {filename}")
                download_file(url, destination)
                downloaded += 1
            except urllib.error.URLError as exc:
                print(f"[{slug}] {idx}/{len(png_urls)} failed: {url} ({exc})", file=sys.stderr)

        summary[slug] = {
            "found": len(png_urls),
            "downloaded": downloaded,
            "skipped": skipped,
        }

    print("\nFinal counts per game:")
    for slug, counts in summary.items():
        print(
            f"- {slug}: found={counts['found']}, downloaded={counts['downloaded']}, "
            f"skipped={counts['skipped']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
