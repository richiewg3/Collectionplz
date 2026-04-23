#!/usr/bin/env python3
"""Download selected GB/GBC map PNGs from VGMaps.

This script parses the GB/GBC atlas index page, extracts all direct .png URLs for a
fixed list of games, and downloads them into references/maps/{game-name}/.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

INDEX_URL = "https://vgmaps.com/Atlas/GB-GBC/index.htm"
USER_AGENT = "Mozilla/5.0 (compatible; GBGBC-Map-Downloader/1.0)"

# Mapping of requested game names to the index page anchor for each game section.
GAMES = {
    "Shantae": "Shantae",
    "Super Mario Land": "SuperMarioLand",
    "Super Mario Land 2: 6 Golden Coins": "SuperMarioLand26GoldenCoins",
    "Tiny Toon Adventures": "TinyToonAdventuresBabsBigBreak",
    "Tomb Raider: Curse of the Sword": "TombRaiderCurseOfTheSword",
    "Zelda: Link's Awakening DX": "LegendOfZeldaLinksAwakeningDX",
    "Zelda: Oracle of Ages": "LegendOfZeldaOracleOfAges",
    "Zelda: Oracle of Seasons": "LegendOfZeldaOracleOfSeasons",
    "Wario Land: Super Mario Land 3": "WarioLandSuperMarioLand3",
    "Wario Land 3": "WarioLand3",
}


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug


def fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=60) as response:
        # vgmaps pages are largely latin1-ish html
        return response.read().decode("latin1", errors="ignore")


def extract_sections(html: str) -> list[tuple[int, str]]:
    anchors = []
    pattern = re.compile(r"<a\s+name\s*=\s*\"?([^\"\s>]+)", re.IGNORECASE)
    for match in pattern.finditer(html):
        anchors.append((match.start(), match.group(1)))
    return anchors


def extract_png_urls_for_anchor(html: str, anchors: list[tuple[int, str]], wanted_anchor: str) -> list[str]:
    start_idx = None
    for idx, anchor in anchors:
        if anchor.lower() == wanted_anchor.lower():
            start_idx = idx
            break

    if start_idx is None:
        raise ValueError(f"Could not find anchor: {wanted_anchor}")

    end_idx = len(html)
    for idx, _anchor in anchors:
        if idx > start_idx:
            end_idx = idx
            break

    section = html[start_idx:end_idx]
    hrefs = re.findall(r"href\s*=\s*\"([^\"]+\.png)\"", section, flags=re.IGNORECASE)

    seen = set()
    urls = []
    for href in hrefs:
        full_url = urljoin(INDEX_URL, href)
        if full_url not in seen:
            seen.add(full_url)
            urls.append(full_url)
    return urls


def download_file(url: str, dest: Path) -> None:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=120) as response, dest.open("wb") as out:
        out.write(response.read())


def main() -> int:
    try:
        html = fetch_text(INDEX_URL)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to fetch index page: {exc}", file=sys.stderr)
        return 1

    anchors = extract_sections(html)
    base_dir = Path("references/maps")
    base_dir.mkdir(parents=True, exist_ok=True)

    totals: dict[str, tuple[int, int, int]] = {}

    for game_name, anchor in GAMES.items():
        try:
            png_urls = extract_png_urls_for_anchor(html, anchors, anchor)
        except Exception as exc:  # noqa: BLE001
            print(f"\n{game_name}: ERROR extracting URLs ({exc})", file=sys.stderr)
            totals[game_name] = (0, 0, 0)
            continue

        folder = base_dir / slugify(game_name)
        folder.mkdir(parents=True, exist_ok=True)

        print(f"\n{game_name}: {len(png_urls)} PNG(s) found")

        downloaded = 0
        skipped = 0

        for i, url in enumerate(png_urls, start=1):
            filename = Path(urlparse(url).path).name
            dest = folder / filename

            if dest.exists():
                skipped += 1
                print(f"  [{i}/{len(png_urls)}] skip  {filename}")
                continue

            try:
                download_file(url, dest)
                downloaded += 1
                print(f"  [{i}/{len(png_urls)}] saved {filename}")
            except Exception as exc:  # noqa: BLE001
                print(f"  [{i}/{len(png_urls)}] FAIL  {filename} ({exc})", file=sys.stderr)

        totals[game_name] = (len(png_urls), downloaded, skipped)

    print("\nFinal counts per game:")
    for game_name, (total, downloaded, skipped) in totals.items():
        print(f"- {game_name}: total={total}, downloaded={downloaded}, skipped={skipped}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
