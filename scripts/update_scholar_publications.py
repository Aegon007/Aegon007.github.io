#!/usr/bin/env python3
"""Merge Google Scholar publications into the Hugo publications data file."""

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
from typing import Any
from zoneinfo import ZoneInfo

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised in environments without PyYAML
    raise SystemExit("PyYAML is required: python3 -m pip install PyYAML") from exc


DEFAULT_USER_ID = "nvAQ5LwAAAAJ"
DEFAULT_OUTPUT = Path("data/publications.yml")


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def normalize_title(value: str) -> str:
    value = re.sub(r"^\s*(poster|demo)\s*[:\-]\s*", "", value, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def int_from_text(value: Any) -> int | None:
    match = re.search(r"\d[\d,]*", str(value or ""))
    return int(match.group(0).replace(",", "")) if match else None


def fetch_json(url: str) -> dict[str, Any]:
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


class ScholarPublicationsParser(html.parser.HTMLParser):
    """Parse publication rows from a Google Scholar author profile."""

    def __init__(self) -> None:
        super().__init__()
        self.publications: list[dict[str, Any]] = []
        self._row: dict[str, Any] | None = None
        self._capture: tuple[str, str] | None = None
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())

        if tag == "tr" and "gsc_a_tr" in classes:
            self._row = {"gray": []}
            return
        if self._row is None:
            return

        if tag == "a" and "gsc_a_at" in classes:
            self._row["url"] = urllib.parse.urljoin(
                "https://scholar.google.com", attributes.get("href") or ""
            )
            self._start_capture("title", tag)
        elif tag == "div" and "gs_gray" in classes:
            self._start_capture("gray", tag)
        elif tag == "a" and "gsc_a_ac" in classes:
            self._start_capture("citations", tag)
        elif tag == "span" and "gsc_a_h" in classes:
            self._start_capture("year", tag)

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._capture and tag == self._capture[1]:
            field = self._capture[0]
            value = clean_text("".join(self._buffer))
            if field == "gray":
                if value:
                    self._row["gray"].append(value)
            elif value:
                self._row[field] = value
            self._capture = None
            self._buffer = []

        if tag == "tr" and self._row is not None:
            gray = self._row.pop("gray", [])
            if gray:
                self._row["authors"] = gray[0]
            if len(gray) > 1:
                self._row["publication"] = gray[1]
            if self._row.get("title"):
                self.publications.append(self._row)
            self._row = None

    def _start_capture(self, field: str, tag: str) -> None:
        self._capture = (field, tag)
        self._buffer = []


def from_serpapi(user_id: str, api_key: str) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "engine": "google_scholar_author",
            "author_id": user_id,
            "sort": "pubdate",
            "num": 100,
            "api_key": api_key,
        }
    )
    payload = fetch_json(f"https://serpapi.com/search.json?{params}")
    publications: list[dict[str, Any]] = []
    for article in payload.get("articles", []):
        cited_by = article.get("cited_by") or {}
        publications.append(
            {
                "title": clean_text(article.get("title")),
                "authors": clean_text(article.get("authors")),
                "publication": clean_text(article.get("publication")),
                "year": int_from_text(article.get("year")),
                "citations": int_from_text(cited_by.get("value")) or 0,
                "url": clean_text(article.get("link")),
                "scholar_id": clean_text(article.get("citation_id")),
            }
        )
    if not publications:
        raise RuntimeError("SerpAPI returned no Scholar publications")
    return publications


def from_google_scholar(user_id: str) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "user": user_id,
            "hl": "en",
            "pagesize": 100,
            "sortby": "pubdate",
        }
    )
    parser = ScholarPublicationsParser()
    parser.feed(fetch_text(f"https://scholar.google.com/citations?{params}"))
    if not parser.publications:
        raise RuntimeError("Could not parse publications from Google Scholar")
    for publication in parser.publications:
        publication["year"] = int_from_text(publication.get("year"))
        publication["citations"] = int_from_text(publication.get("citations")) or 0
    return parser.publications


def infer_section(publication: str, title: str) -> str:
    text = f"{publication} {title}".casefold()
    if "patent" in text:
        return "patent"
    if "workshop" in text or "poster" in text:
        return "workshop"
    if any(word in text for word in ("journal", "transactions", "letters", "magazine")):
        return "journal"
    if any(word in text for word in ("conference", "symposium", "proceedings", "congress")):
        return "conference"
    return "other"


def build_citation(publication: dict[str, Any]) -> str:
    authors = clean_text(publication.get("authors"))
    title = clean_text(publication.get("title"))
    venue = clean_text(publication.get("publication"))
    year = publication.get("year")

    parts = []
    if authors:
        parts.append(authors)
    if title:
        parts.append(f'"{title}"')
    if venue:
        parts.append(venue)
    if year and str(year) not in venue:
        parts.append(str(year))
    return ", ".join(parts).rstrip(".") + "."


def merge_publications(
    data: dict[str, Any], scholar_publications: list[dict[str, Any]], user_id: str
) -> tuple[dict[str, Any], int, int]:
    items = list(data.get("items") or [])
    existing_by_title = {
        normalize_title(clean_text(item.get("title"))): item
        for item in items
        if clean_text(item.get("title"))
    }

    added = 0
    matched = 0
    seen: set[str] = set()
    for publication in scholar_publications:
        title = clean_text(publication.get("title"))
        key = normalize_title(title)
        if not key:
            continue
        if key in seen:
            item = existing_by_title.get(key)
            current_citations = int_from_text(publication.get("citations")) or 0
            if item is not None and current_citations >= (
                int_from_text(item.get("scholar_citations")) or 0
            ):
                item["scholar_citations"] = current_citations
                if publication.get("url"):
                    item["scholar_url"] = publication["url"]
                if publication.get("scholar_id"):
                    item["scholar_id"] = publication["scholar_id"]
            continue
        seen.add(key)

        item = existing_by_title.get(key)
        if item is None:
            item = {
                "section": infer_section(
                    clean_text(publication.get("publication")), title
                ),
                "selected": False,
                "year": publication.get("year") or 0,
                "title": title,
                "citation": build_citation(publication),
            }
            items.append(item)
            existing_by_title[key] = item
            added += 1
        else:
            matched += 1

        if publication.get("url"):
            item["scholar_url"] = publication["url"]
        if publication.get("scholar_id"):
            item["scholar_id"] = publication["scholar_id"]
        item["scholar_citations"] = int_from_text(publication.get("citations")) or 0

    section_keys = {section.get("key") for section in data.get("sections", [])}
    if "other" not in section_keys:
        data.setdefault("sections", []).append(
            {"key": "other", "title": "Other Publications"}
        )

    items.sort(
        key=lambda item: (
            -(int_from_text(item.get("year")) or 0),
            normalize_title(clean_text(item.get("title"))),
        )
    )
    data["scholar_profile"] = (
        f"https://scholar.google.com/citations?user={user_id}&hl=en"
    )
    timezone = ZoneInfo(os.getenv("SCHOLAR_TIMEZONE", "America/Chicago"))
    data["updated"] = dt.datetime.now(timezone).date().isoformat()
    data["items"] = items
    return data, added, matched


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user-id", default=os.getenv("GOOGLE_SCHOLAR_USER_ID", DEFAULT_USER_ID)
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        data = yaml.safe_load(args.output.read_text(encoding="utf-8")) or {}
        api_key = os.getenv("SERPAPI_KEY")
        publications = (
            from_serpapi(args.user_id, api_key)
            if api_key
            else from_google_scholar(args.user_id)
        )
        merged, added, matched = merge_publications(data, publications, args.user_id)
        if not args.dry_run:
            args.output.write_text(
                yaml.safe_dump(
                    merged,
                    sort_keys=False,
                    allow_unicode=True,
                    width=120,
                ),
                encoding="utf-8",
            )
    except Exception as exc:
        print(f"Scholar publications update failed: {exc}", file=sys.stderr)
        return 1

    mode = "SerpAPI" if os.getenv("SERPAPI_KEY") else "Google Scholar HTML"
    print(
        f"Scholar publications ({mode}): fetched={len(publications)}, "
        f"matched={matched}, added={added}, dry_run={args.dry_run}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
