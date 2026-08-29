#!/usr/bin/env python3
"""Update Hugo data for Google Scholar author statistics."""

from __future__ import annotations

import argparse
import datetime as dt
import html.parser
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_USER_ID = "nvAQ5LwAAAAJ"
DEFAULT_OUTPUT = Path("data/scholar.yml")


class ScholarStatsParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._capture = False
        self._buffer: list[str] = []
        self.cells: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "td":
            return
        classes = dict(attrs).get("class", "")
        if "gsc_rsb_sc1" in classes or "gsc_rsb_std" in classes:
            self._capture = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._capture:
            text = " ".join("".join(self._buffer).split())
            if text:
                self.cells.append(text)
            self._capture = False


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def int_from_text(value: str | int | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"\d[\d,]*", str(value))
    if not match:
        return None
    return int(match.group(0).replace(",", ""))


def from_serpapi(user_id: str, api_key: str) -> dict[str, int]:
    params = urllib.parse.urlencode(
        {
            "engine": "google_scholar_author",
            "author_id": user_id,
            "api_key": api_key,
        }
    )
    payload = fetch_json(f"https://serpapi.com/search.json?{params}")
    table = payload.get("cited_by", {}).get("table", [])
    stats: dict[str, int] = {}
    for row in table:
        metric = str(row.get("citations", "")).lower()
        all_value = row.get("all")
        if metric == "citations":
            stats["citations"] = int_from_text(all_value) or 0
        elif metric == "h-index":
            stats["h_index"] = int_from_text(all_value) or 0
        elif metric == "i10-index":
            stats["i10_index"] = int_from_text(all_value) or 0
    if {"citations", "h_index", "i10_index"} - stats.keys():
        raise RuntimeError("SerpAPI response did not include all Scholar metrics")
    return stats


def from_google_scholar(user_id: str) -> dict[str, int]:
    url = f"https://scholar.google.com/citations?user={urllib.parse.quote(user_id)}&hl=en"
    parser = ScholarStatsParser()
    parser.feed(fetch_text(url))

    stats: dict[str, int] = {}
    index = 0
    while index < len(parser.cells):
        label = parser.cells[index].lower()
        if label in {"citations", "h-index", "i10-index"} and index + 1 < len(parser.cells):
            value = int_from_text(parser.cells[index + 1])
            if value is not None:
                key = {"citations": "citations", "h-index": "h_index", "i10-index": "i10_index"}[label]
                stats[key] = value
            index += 3
        else:
            index += 1

    if {"citations", "h_index", "i10_index"} - stats.keys():
        raise RuntimeError("Could not parse Google Scholar metrics")
    return stats


def write_hugo_data(output: Path, user_id: str, stats: dict[str, int]) -> None:
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    profile_url = f"https://scholar.google.com/citations?user={user_id}&hl=en"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(
            [
                f'profile_url: "{profile_url}"',
                f'user_id: "{user_id}"',
                f'citations: {stats["citations"]}',
                f'h_index: {stats["h_index"]}',
                f'i10_index: {stats["i10_index"]}',
                f'updated: "{today}"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", default=os.getenv("GOOGLE_SCHOLAR_USER_ID", DEFAULT_USER_ID))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    try:
        api_key = os.getenv("SERPAPI_KEY")
        stats = from_serpapi(args.user_id, api_key) if api_key else from_google_scholar(args.user_id)
        write_hugo_data(args.output, args.user_id, stats)
    except Exception as exc:
        print(f"Scholar stats update failed: {exc}", file=sys.stderr)
        return 1

    print(
        "Updated Scholar stats: "
        f"citations={stats['citations']}, h-index={stats['h_index']}, i10-index={stats['i10_index']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
