#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path


def load_opportunities(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def score_opportunity(item: dict, profile_keywords: list[str], preferred_levels: list[str], remote_preference: str) -> tuple[int, dict]:
    title = (item.get("title") or "").lower()
    tags = [str(t).lower() for t in item.get("tags", [])]
    level = (item.get("level") or "").lower()
    remote = (item.get("remote") or "").lower()

    reasons: list[str] = []
    score = 0

    # 1) Skill-match score
    skill_hits = 0
    for kw in profile_keywords:
        kw_l = kw.lower().strip()
        if not kw_l:
            continue
        if kw_l in title or kw_l in tags:
            skill_hits += 1
    score += skill_hits * 2
    if skill_hits:
        reasons.append(f"skill-match: {skill_hits} keyword hit(s)")

    # 2) Remote-fit score
    remote_pref = remote_preference.lower()
    if remote_pref == "remote" and remote == "remote":
        score += 2
        reasons.append("remote-fit: preferred remote")
    elif remote_pref == "hybrid" and remote in {"hybrid", "remote"}:
        score += 2
        reasons.append("remote-fit: preferred hybrid/remote")
    elif remote_pref == "onsite" and remote == "onsite":
        score += 2
        reasons.append("remote-fit: preferred onsite")

    # 3) Seniority-fit score
    if preferred_levels and level in preferred_levels:
        score += 2
        reasons.append(f"seniority-fit: {level}")

    # Small bonus for AI/ML-focused roles (matches Fubsi interest)
    if any(x in title or x in tags for x in ("ai", "ml", "machine learning", "llm")):
        score += 1
        reasons.append("focus-bonus: AI/ML")

    details = {
        "skill_hits": skill_hits,
        "level": level,
        "remote": remote,
        "reasons": reasons,
    }
    return score, details


def rank_opportunities(
    opportunities: list[dict], profile_keywords: list[str], preferred_levels: list[str], remote_preference: str
) -> list[dict]:
    ranked = []
    for item in opportunities:
        score, details = score_opportunity(item, profile_keywords, preferred_levels, remote_preference)
        row = dict(item)
        row["score"] = score
        row["details"] = details
        ranked.append(row)

    ranked.sort(key=lambda x: (-int(x.get("score", 0)), x.get("title", "").lower()))
    return ranked


def render_markdown(ranked: list[dict], date: str) -> str:
    lines = [f"# CareerPulse Report – {date}", "", "Top Opportunities (ranked):", ""]
    if not ranked:
        lines.append("Keine Opportunities gefunden.")
        return "\n".join(lines) + "\n"

    for i, item in enumerate(ranked, 1):
        lines.append(f"{i}. **{item.get('title', 'Untitled')}** — score `{item.get('score', 0)}`")
        lines.append(f"   - company: {item.get('company', 'unknown')}")
        lines.append(f"   - level: {item.get('level', 'unknown')}")
        lines.append(f"   - remote: {item.get('remote', 'unknown')}")
        lines.append(f"   - url: <{item.get('url', '')}>")
        if item.get("details", {}).get("reasons"):
            lines.append(f"   - why: {', '.join(item['details']['reasons'])}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="CareerPulse Iteration 1")
    parser.add_argument("--input", default="data/careerpulse_sample.json", help="Input opportunities JSON")
    parser.add_argument("--outdir", default="reports", help="Output directory")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument(
        "--profile-keywords",
        default="python,node.js,javascript,ai,machine learning,docker",
        help="Comma-separated keyword profile",
    )
    parser.add_argument("--levels", default="junior,mid", help="Comma-separated preferred levels")
    parser.add_argument("--remote", default="hybrid", choices=["remote", "hybrid", "onsite"])
    args = parser.parse_args()

    opportunities = load_opportunities(Path(args.input))
    profile_keywords = [x.strip() for x in args.profile_keywords.split(",") if x.strip()]
    preferred_levels = [x.strip().lower() for x in args.levels.split(",") if x.strip()]

    ranked = rank_opportunities(opportunities, profile_keywords, preferred_levels, args.remote)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()

    if args.format == "markdown":
        out = outdir / f"careerpulse-{today}.md"
        out.write_text(render_markdown(ranked, today), encoding="utf-8")
    else:
        out = outdir / f"careerpulse-{today}.json"
        out.write_text(json.dumps({"date": today, "results": ranked}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
