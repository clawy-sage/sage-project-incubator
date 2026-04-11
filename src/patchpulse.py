#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from urllib.request import urlopen


def load_sources(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_feed(url: str) -> list[dict]:
    with urlopen(url, timeout=20) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    items: list[dict] = []

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if title and link:
            items.append({"title": title, "url": link, "published": pub})

    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//a:entry", ns):
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        link_el = entry.find("a:link", ns)
        link = (link_el.attrib.get("href", "") if link_el is not None else "").strip()
        pub = (
            entry.findtext("a:updated", default="", namespaces=ns)
            or entry.findtext("a:published", default="", namespaces=ns)
            or ""
        ).strip()
        if title and link:
            items.append({"title": title, "url": link, "published": pub})

    return items


def dedup(items: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for it in items:
        key = hashlib.sha1(it["url"].encode("utf-8")).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def render_report(items: list[dict], date: str) -> str:
    lines = [f"# PatchPulse Report – {date}", ""]
    if not items:
        return "\n".join(lines + ["Keine neuen Items gefunden.", ""])

    for i, it in enumerate(items, 1):
        lines.append(f"{i}. {it['title']}")
        lines.append(f"   - {it['url']}")
        if it.get("published"):
            lines.append(f"   - published: {it['published']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="PatchPulse MVP")
    parser.add_argument("--sources", default="data/sources.json")
    parser.add_argument("--outdir", default="reports")
    args = parser.parse_args()

    sources = load_sources(Path(args.sources))
    all_items: list[dict] = []
    for s in sources:
        try:
            all_items.extend(fetch_feed(s["url"]))
        except Exception:
            continue

    unique_items = dedup(all_items)
    today = dt.date.today().isoformat()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    report = outdir / f"{today}.md"
    report.write_text(render_report(unique_items, today), encoding="utf-8")
    print(f"wrote {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
