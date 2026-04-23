#!/usr/bin/env python3
"""Download selected GBA map PNGs from vgmaps.com."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

INDEX_URL = "https://vgmaps.com/Atlas/GBA/index.htm"
BASE_URL = "https://vgmaps.com/Atlas/GBA/"
USER_AGENT = "Mozilla/5.0 (compatible; gba-map-downloader/1.0)"

GAME_PATTERNS: Dict[str, str] = {
    "zelda-minish-cap": r"^LegendOfZelda-MinishCap-.*\.png$",
    "golden-sun": r"^GoldenSun-(?!LostAge-).*\.png$",
    "golden-sun-the-lost-age": r"^GoldenSun-LostAge-.*\.png$",
    "mother-3": r"^Mother3\(J\)-.*\.png$",
    "pokemon-firered-leafgreen": r"^Pokemon-FireRed&LeafGreenVersions-.*\.png$",
    "pokemon-ruby-sapphire": r"^Pokemon-Ruby&SapphireVersions-.*\.png$",
    "sword-of-mana": r"^SwordOfMana-.*\.png$",
    "final-fantasy-tactics-advance": r"^FinalFantasyTacticsAdvance-.*\.png$",
    "castlevania-aria-of-sorrow": r"^Castlevania-AriaOfSorrow-.*\.png$",
    "metroid-fusion": r"^MetroidFusion-.*\.png$",
    "kirby-nightmare-in-dreamland": r"^Kirby-NightmareInDreamLand-.*\.png$",
    "kirby-amazing-mirror": r"^Kirby&TheAmazingMirror-.*\.png$",
    "wario-land-4": r"^WarioLand4-.*\.png$",
}


def fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req) as resp:
        return resp.read().decode("latin-1", errors="ignore")


def extract_png_links(index_html: str) -> list[str]:
    hrefs = re.findall(r'href="([^"#?]+\.png)"', index_html, flags=re.IGNORECASE)
    unique_sorted = sorted(set(hrefs), key=str.lower)
    return [urljoin(BASE_URL, href) for href in unique_sorted]


def filter_game_urls(all_urls: Iterable[str]) -> Dict[str, list[str]]:
    filtered: Dict[str, list[str]] = {}
    for game, pattern in GAME_PATTERNS.items():
        regex = re.compile(pattern, flags=re.IGNORECASE)
        matches = [u for u in all_urls if regex.match(u.rsplit("/", 1)[-1])]
        filtered[game] = sorted(matches, key=str.lower)
    return filtered


def download_file(url: str, dest: Path, idx: int, total: int) -> str:
    if dest.exists():
        print(f"[{idx}/{total}] skip {dest.name}")
        return "skipped"

    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req) as resp:
        data = resp.read()

    dest.write_bytes(data)
    print(f"[{idx}/{total}] saved {dest.name}")
    return "downloaded"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download selected GBA map PNGs from vgmaps.com into references/maps/{game-name}/",
    )
    parser.add_argument(
        "--output-root",
        default="references/maps",
        help="Output directory root (default: references/maps)",
    )
    args = parser.parse_args()

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    try:
        print(f"Fetching index: {INDEX_URL}")
        html = fetch_text(INDEX_URL)
    except (HTTPError, URLError) as exc:
        print(f"Failed to fetch index page: {exc}", file=sys.stderr)
        return 1

    all_urls = extract_png_links(html)
    per_game = filter_game_urls(all_urls)

    final_counts: Dict[str, Dict[str, int]] = {}

    for game, urls in per_game.items():
        game_dir = output_root / game
        game_dir.mkdir(parents=True, exist_ok=True)

        downloaded = 0
        skipped = 0
        errors = 0

        print(f"\n=== {game} ({len(urls)} PNGs) ===")
        for idx, url in enumerate(urls, start=1):
            filename = url.rsplit("/", 1)[-1]
            dest = game_dir / filename
            try:
                result = download_file(url, dest, idx, len(urls))
                if result == "downloaded":
                    downloaded += 1
                else:
                    skipped += 1
            except (HTTPError, URLError, OSError) as exc:
                errors += 1
                print(f"[{idx}/{len(urls)}] error {filename}: {exc}")

        final_counts[game] = {
            "total": len(urls),
            "downloaded": downloaded,
            "skipped": skipped,
            "errors": errors,
        }

    print("\n=== Final counts per game ===")
    for game, counts in final_counts.items():
        print(
            f"{game}: total={counts['total']}, "
            f"downloaded={counts['downloaded']}, "
            f"skipped={counts['skipped']}, "
            f"errors={counts['errors']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
