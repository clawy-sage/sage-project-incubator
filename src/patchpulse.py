#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import random
import time
import xml.etree.ElementTree as ET
from urllib.error import HTTPError, URLError
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


def _extract_items_from_root(root: ET.Element, source_name: str) -> tuple[list[dict], int]:
    items: list[dict] = []
    skipped = 0

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
        else:
            skipped += 1

    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//a:entry", ns):
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        link = ""
        for link_el in entry.findall("a:link", ns):
            rel = (link_el.attrib.get("rel") or "alternate").strip().lower()
            href = (link_el.attrib.get("href") or "").strip()
            if not href:
                continue
            if rel == "alternate":
                link = href
                break
            if not link:
                link = href
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
        else:
            skipped += 1

    return items, skipped


def _compute_retry_delay(
    backoff_seconds: float,
    attempt: int,
    backoff_cap_seconds: float | None = None,
    backoff_jitter_ratio: float = 0.0,
    rng: random.Random | None = None,
) -> float:
    delay = max(0.0, float(backoff_seconds)) * max(1, int(attempt))

    if backoff_cap_seconds is not None:
        delay = min(delay, max(0.0, float(backoff_cap_seconds)))

    jitter_ratio = max(0.0, float(backoff_jitter_ratio))
    if jitter_ratio > 0 and delay > 0:
        rand = (rng or random).random()
        low = max(0.0, 1.0 - jitter_ratio)
        high = 1.0 + jitter_ratio
        factor = low + (high - low) * rand
        delay *= factor

    return delay


def fetch_feed_with_stats(
    source_name: str,
    url: str,
    retries: int = 0,
    backoff_seconds: float = 0.0,
    backoff_cap_seconds: float | None = None,
    backoff_jitter_ratio: float = 0.0,
    jitter_seed: int | None = None,
) -> tuple[list[dict], dict]:
    stats = {
        "source": source_name,
        "items": 0,
        "skipped": 0,
        "status": "ok",
        "error": "",
        "attempts": 0,
        "retried": False,
    }

    max_attempts = max(1, int(retries) + 1)
    delay = max(0.0, float(backoff_seconds))
    rng = random.Random(jitter_seed) if jitter_seed is not None else None

    raw = b""
    for attempt in range(1, max_attempts + 1):
        stats["attempts"] = attempt
        try:
            with urlopen(url, timeout=20) as resp:
                raw = resp.read()
            stats["status"] = "ok"
            stats["error"] = ""
            stats["retried"] = attempt > 1
            break
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            stats["status"] = "error"
            stats["error"] = type(exc).__name__
            if attempt < max_attempts:
                if delay > 0:
                    sleep_for = _compute_retry_delay(
                        delay,
                        attempt,
                        backoff_cap_seconds=backoff_cap_seconds,
                        backoff_jitter_ratio=backoff_jitter_ratio,
                        rng=rng,
                    )
                    time.sleep(sleep_for)
                continue
            stats["retried"] = max_attempts > 1
            return [], stats

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        stats["status"] = "error"
        stats["error"] = "ParseError"
        return [], stats

    items, skipped = _extract_items_from_root(root, source_name)
    stats["items"] = len(items)
    stats["skipped"] = skipped
    return items, stats


def fetch_feed(source_name: str, url: str, retries: int = 0, backoff_seconds: float = 0.0) -> list[dict]:
    items, _ = fetch_feed_with_stats(source_name, url, retries=retries, backoff_seconds=backoff_seconds)
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


def render_source_summary(source_stats: list[dict]) -> list[str]:
    lines = ["## Source Summary", ""]
    for st in source_stats:
        attempts = int(st.get("attempts", 1) or 1)
        retried = bool(st.get("retried", False))
        if st.get("status") == "error":
            lines.append(
                f"- {st['source']}: ERROR ({st.get('error', 'UnknownError')}), attempts={attempts}, retried={str(retried).lower()}"
            )
        else:
            lines.append(
                f"- {st['source']}: items={st.get('items', 0)}, skipped={st.get('skipped', 0)}, attempts={attempts}, retried={str(retried).lower()}"
            )
    lines.append("")
    return lines


def render_report(items: list[dict], date: str, source_stats: list[dict] | None = None) -> str:
    lines = [f"# PatchPulse Report – {date}", ""]

    if source_stats:
        lines.extend(render_source_summary(source_stats))

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


def render_discord_digest(
    items: list[dict],
    date: str,
    limit: int,
    source_stats: list[dict] | None = None,
    include_source_health: bool = False,
    source_health_mode: str = "errors-only",
) -> str:
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

    if include_source_health and source_stats is not None:
        mode = source_health_mode.strip().lower()
        if mode not in {"errors-only", "always"}:
            mode = "errors-only"

        error_sources = [st.get("source", "unknown") for st in source_stats if st.get("status") == "error"]
        if error_sources or mode == "always":
            lines.append("")
            if error_sources:
                names = ", ".join(error_sources)
                label = "source" if len(error_sources) == 1 else "sources"
                lines.append(f"⚠️ Feed health: {len(error_sources)} {label} with errors ({names})")
            else:
                lines.append("✅ Feed health: all sources OK")

    return "\n".join(lines)


def render_discord_payload(
    items: list[dict], date: str, limit: int, source_stats: list[dict] | None = None
) -> dict:
    top = items[:limit]
    message_text = render_discord_digest(items, date, limit)

    payload = {
        "type": "discord_message_payload",
        "generated_at": f"{date}T00:00:00Z",
        "date": date,
        "item_count": len(top),
        "message": message_text,
        "items": [
            {
                "rank": idx,
                "topic": it.get("topic", "General"),
                "priority": int(it.get("priority", 0)),
                "title": it.get("title", ""),
                "url": it.get("url", ""),
                "source": it.get("source", "unknown"),
                "published": it.get("published", ""),
            }
            for idx, it in enumerate(top, 1)
        ],
    }

    if source_stats is not None:
        payload["source_summary"] = [
            {
                "source": st.get("source", "unknown"),
                "status": st.get("status", "ok"),
                "items": int(st.get("items", 0) or 0),
                "skipped": int(st.get("skipped", 0) or 0),
                "error": st.get("error", ""),
                "attempts": int(st.get("attempts", 1) or 1),
                "retried": bool(st.get("retried", False)),
            }
            for st in source_stats
        ]
        payload["source_summary_totals"] = {
            "sources": len(source_stats),
            "errors": sum(1 for st in source_stats if st.get("status") == "error"),
            "items": sum(int(st.get("items", 0) or 0) for st in source_stats),
            "skipped": sum(int(st.get("skipped", 0) or 0) for st in source_stats),
            "retried_sources": sum(1 for st in source_stats if bool(st.get("retried", False))),
            "total_attempts": sum(int(st.get("attempts", 1) or 1) for st in source_stats),
        }

    return payload


def print_source_summary(source_stats: list[dict]) -> None:
    print("source summary:")
    for st in source_stats:
        attempts = int(st.get("attempts", 1) or 1)
        retried = bool(st.get("retried", False))
        if st.get("status") == "error":
            print(
                f"- {st['source']}: ERROR ({st.get('error', 'UnknownError')}), attempts={attempts}, retried={str(retried).lower()}"
            )
        else:
            print(
                f"- {st['source']}: items={st.get('items', 0)}, skipped={st.get('skipped', 0)}, attempts={attempts}, retried={str(retried).lower()}"
            )


def has_source_errors(source_stats: list[dict]) -> bool:
    return any(st.get("status") == "error" for st in source_stats)


def count_source_errors(source_stats: list[dict]) -> int:
    return sum(1 for st in source_stats if st.get("status") == "error")


def resolve_source_retry_config(source: dict, args: argparse.Namespace) -> dict:
    def _coerce_int(value, default: int | None) -> int | None:
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _coerce_float(value, default: float | None) -> float | None:
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    cap = _coerce_float(
        source.get("retry_backoff_cap_seconds"),
        args.retry_backoff_cap_seconds,
    )

    return {
        "retries": max(0, _coerce_int(source.get("retries"), args.source_retries) or 0),
        "backoff_seconds": max(
            0.0,
            _coerce_float(source.get("retry_backoff_seconds"), args.retry_backoff_seconds) or 0.0,
        ),
        "backoff_cap_seconds": cap if cap is None else max(0.0, cap),
        "backoff_jitter_ratio": max(
            0.0,
            _coerce_float(source.get("retry_backoff_jitter_ratio"), args.retry_backoff_jitter_ratio) or 0.0,
        ),
        "jitter_seed": _coerce_int(source.get("retry_jitter_seed"), args.retry_jitter_seed),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PatchPulse MVP")
    parser.add_argument("--sources", default="data/sources.json")
    parser.add_argument("--outdir", default="reports")
    parser.add_argument("--format", choices=["markdown", "discord", "discord-json"], default="markdown")
    parser.add_argument("--limit", type=int, default=8, help="Max items for discord outputs")
    parser.add_argument(
        "--source-health-footer",
        action="store_true",
        help="Append source health footer in discord text output",
    )
    parser.add_argument(
        "--source-health-mode",
        choices=["errors-only", "always"],
        default="errors-only",
        help="Control footer rendering when --source-health-footer is set",
    )
    parser.add_argument(
        "--fail-on-source-errors",
        action="store_true",
        help="Exit with code 2 if any source fetch/parsing error occurred",
    )
    parser.add_argument(
        "--max-source-errors",
        type=int,
        default=None,
        help="Allowed number of source errors before exiting with code 2 (e.g. 1 tolerates one broken source)",
    )
    parser.add_argument(
        "--source-retries",
        type=int,
        default=0,
        help="Retry attempts per source for transport errors (0 disables retries)",
    )
    parser.add_argument(
        "--retry-backoff-seconds",
        type=float,
        default=0.0,
        help="Linear backoff base in seconds between retries (actual delay = base * attempt)",
    )
    parser.add_argument(
        "--retry-backoff-cap-seconds",
        type=float,
        default=None,
        help="Optional upper cap for retry sleep duration in seconds",
    )
    parser.add_argument(
        "--retry-backoff-jitter-ratio",
        type=float,
        default=0.0,
        help="Optional jitter ratio for retry backoff (0.2 => ±20% jitter)",
    )
    parser.add_argument(
        "--retry-jitter-seed",
        type=int,
        default=None,
        help="Optional random seed for deterministic retry jitter (useful for tests)",
    )
    args = parser.parse_args()

    sources = load_sources(Path(args.sources))
    all_items: list[dict] = []
    source_stats: list[dict] = []
    for s in sources:
        source_name = s.get("name", "unknown")
        retry_cfg = resolve_source_retry_config(s, args)
        items, stats = fetch_feed_with_stats(
            source_name,
            s["url"],
            retries=retry_cfg["retries"],
            backoff_seconds=retry_cfg["backoff_seconds"],
            backoff_cap_seconds=retry_cfg["backoff_cap_seconds"],
            backoff_jitter_ratio=retry_cfg["backoff_jitter_ratio"],
            jitter_seed=retry_cfg["jitter_seed"],
        )
        all_items.extend(items)
        source_stats.append(stats)

    unique_items = dedup(all_items)
    enriched_items = enrich(unique_items)
    ranked_items = sort_items(enriched_items)
    today = dt.date.today().isoformat()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    limit = max(args.limit, 1)
    if args.format == "markdown":
        report = outdir / f"{today}.md"
        report.write_text(render_report(ranked_items, today, source_stats), encoding="utf-8")
        print(f"wrote {report}")
    elif args.format == "discord":
        digest = outdir / f"{today}-discord.txt"
        digest.write_text(
            render_discord_digest(
                ranked_items,
                today,
                limit,
                source_stats=source_stats,
                include_source_health=args.source_health_footer,
                source_health_mode=args.source_health_mode,
            ),
            encoding="utf-8",
        )
        print(f"wrote {digest}")
    else:
        payload_file = outdir / f"{today}-discord.json"
        payload = render_discord_payload(ranked_items, today, limit, source_stats=source_stats)
        payload_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {payload_file}")

    print_source_summary(source_stats)

    source_error_count = count_source_errors(source_stats)

    if args.fail_on_source_errors and source_error_count > 0:
        return 2

    if args.max_source_errors is not None:
        max_errors = max(0, args.max_source_errors)
        if source_error_count > max_errors:
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
