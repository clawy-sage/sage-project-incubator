#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from urllib.request import urlopen


TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Model Releases": ("model", "release", "launch", "gpt", "claude", "gemini", "llama"),
    "Developer Tooling": ("api", "sdk", "cli", "tool", "developer", "integration", "plugin"),
    "Safety & Policy": ("safety", "policy", "governance", "compliance", "security", "risk"),
    "Research": ("research", "paper", "benchmark", "evaluation", "study"),
    "Business & Partnerships": ("pricing", "enterprise", "partnership", "acquisition", "funding"),
}

PRIORITY_KEYWORDS: dict[str, int] = {
    "release": 3,
    "launch": 3,
    "breaking": 3,
    "security": 2,
    "vulnerability": 2,
    "new": 1,
    "update": 1,
    "api": 1,
}


def load_sources(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_feed(source_name: str, url: str) -> list[dict]:
    with urlopen(url, timeout=20) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    items: list[dict] = []

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if title and link:
            items.append(
                {
                    "title": title,
                    "url": link,
                    "published": pub,
                    "source": source_name,
                }
            )

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
            items.append(
                {
                    "title": title,
                    "url": link,
                    "published": pub,
                    "source": source_name,
                }
            )

    return items


def classify_topic(item: dict) -> str:
    hay = f"{item.get('title', '')} {item.get('url', '')}".lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in hay for keyword in keywords):
            return topic
    return "General"


def score_priority(item: dict) -> int:
    hay = f"{item.get('title', '')} {item.get('url', '')}".lower()
    score = 0
    for keyword, points in PRIORITY_KEYWORDS.items():
        if keyword in hay:
            score += points

    source = item.get("source", "").lower()
    if "openai" in source or "anthropic" in source:
        score += 1

    return score


def enrich(items: list[dict]) -> list[dict]:
    enriched: list[dict] = []
    for item in items:
        copy = dict(item)
        copy["topic"] = classify_topic(copy)
        copy["priority"] = score_priority(copy)
        enriched.append(copy)
    return enriched


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


def sort_items(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda it: (-int(it.get("priority", 0)), it.get("title", "").lower()))


def render_report(items: list[dict], date: str) -> str:
    lines = [f"# PatchPulse Report – {date}", ""]
    if not items:
        return "\n".join(lines + ["Keine neuen Items gefunden.", ""])

    grouped: dict[str, list[dict]] = {}
    for it in items:
        grouped.setdefault(it.get("topic", "General"), []).append(it)

    for topic in sorted(grouped.keys()):
        lines.append(f"## {topic}")
        lines.append("")
        for i, it in enumerate(grouped[topic], 1):
            lines.append(f"{i}. {it['title']}")
            lines.append(f"   - {it['url']}")
            lines.append(f"   - source: {it.get('source', 'unknown')}")
            lines.append(f"   - priority: {it.get('priority', 0)}")
            if it.get("published"):
                lines.append(f"   - published: {it['published']}")
        lines.append("")

    return "\n".join(lines)


def render_discord_digest(items: list[dict], date: str, limit: int) -> str:
    lines = [f"**PatchPulse Digest ({date})**", ""]
    if not items:
        lines.append("Keine neuen Items gefunden.")
        return "\n".join(lines)

    top = items[:limit]
    for idx, it in enumerate(top, 1):
        lines.append(
            f"{idx}. **[{it.get('topic','General')}]** {it['title']}"
            f" _(prio {it.get('priority', 0)}, {it.get('source', 'unknown')})_"
        )
        lines.append(f"   <{it['url']}>")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="PatchPulse MVP")
    parser.add_argument("--sources", default="data/sources.json")
    parser.add_argument("--outdir", default="reports")
    parser.add_argument("--format", choices=["markdown", "discord"], default="markdown")
    parser.add_argument("--limit", type=int, default=8, help="Max items for discord digest")
    args = parser.parse_args()

    sources = load_sources(Path(args.sources))
    all_items: list[dict] = []
    for s in sources:
        try:
            all_items.extend(fetch_feed(s.get("name", "unknown"), s["url"]))
        except Exception:
            continue

    unique_items = dedup(all_items)
    enriched_items = enrich(unique_items)
    ranked_items = sort_items(enriched_items)
    today = dt.date.today().isoformat()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.format == "markdown":
        report = outdir / f"{today}.md"
        report.write_text(render_report(ranked_items, today), encoding="utf-8")
        print(f"wrote {report}")
    else:
        digest = outdir / f"{today}-discord.txt"
        digest.write_text(render_discord_digest(ranked_items, today, max(args.limit, 1)), encoding="utf-8")
        print(f"wrote {digest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
