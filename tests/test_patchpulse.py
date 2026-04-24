import pathlib
import sys
import unittest
from unittest.mock import patch
from urllib.error import URLError

# Allow importing from src/
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import patchpulse  # noqa: E402


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._payload


class PatchPulseCoreTests(unittest.TestCase):
    def test_has_source_errors_detects_error_status(self):
        self.assertFalse(patchpulse.has_source_errors([{"source": "A", "status": "ok"}]))
        self.assertTrue(
            patchpulse.has_source_errors(
                [
                    {"source": "A", "status": "ok"},
                    {"source": "B", "status": "error", "error": "URLError"},
                ]
            )
        )

    def test_count_source_errors_counts_only_error_status(self):
        self.assertEqual(patchpulse.count_source_errors([]), 0)
        self.assertEqual(
            patchpulse.count_source_errors(
                [
                    {"source": "A", "status": "ok"},
                    {"source": "B", "status": "error"},
                    {"source": "C", "status": "error"},
                ]
            ),
            2,
        )

    def test_classify_topic_model_release(self):
        item = {
            "title": "Gemini model release for developers",
            "url": "https://example.com/news",
        }
        self.assertEqual(patchpulse.classify_topic(item), "Model Releases")

    def test_classify_topic_fallback_general(self):
        item = {
            "title": "Weekly community roundup",
            "url": "https://example.com/roundup",
        }
        self.assertEqual(patchpulse.classify_topic(item), "General")

    def test_score_priority_keyword_accumulation(self):
        item = {
            "title": "New API launch includes security update",
            "url": "https://example.com/security",
            "source": "Example Feed",
        }
        # new(1) + api(1) + launch(3) + security(2) + update(1) = 8
        self.assertEqual(patchpulse.score_priority(item), 8)

    def test_fetch_feed_returns_empty_on_transport_error(self):
        with patch("patchpulse.urlopen", side_effect=URLError("boom")):
            items = patchpulse.fetch_feed("Broken Feed", "https://example.com/rss")
        self.assertEqual(items, [])

    def test_fetch_feed_with_stats_reports_transport_error(self):
        with patch("patchpulse.urlopen", side_effect=URLError("boom")):
            items, stats = patchpulse.fetch_feed_with_stats("Broken Feed", "https://example.com/rss")

        self.assertEqual(items, [])
        self.assertEqual(stats["status"], "error")
        self.assertEqual(stats["error"], "URLError")

    def test_fetch_feed_with_stats_retries_and_recovers(self):
        rss = b"""<?xml version='1.0' encoding='UTF-8'?>
<rss><channel>
  <item><title>Recovered</title><link>https://example.com/recovered</link></item>
</channel></rss>
"""
        with (
            patch("patchpulse.urlopen", side_effect=[URLError("flaky"), _FakeResponse(rss)]),
            patch("patchpulse.time.sleep") as sleep_mock,
        ):
            items, stats = patchpulse.fetch_feed_with_stats(
                "Flaky Feed",
                "https://example.com/rss",
                retries=1,
                backoff_seconds=0.5,
            )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Recovered")
        self.assertEqual(stats["status"], "ok")
        self.assertEqual(stats["error"], "")
        self.assertEqual(stats["attempts"], 2)
        self.assertTrue(stats["retried"])
        sleep_mock.assert_called_once_with(0.5)

    def test_fetch_feed_with_stats_retries_exhausted(self):
        with (
            patch("patchpulse.urlopen", side_effect=[URLError("a"), URLError("b")]),
            patch("patchpulse.time.sleep") as sleep_mock,
        ):
            items, stats = patchpulse.fetch_feed_with_stats(
                "Broken Feed",
                "https://example.com/rss",
                retries=1,
                backoff_seconds=0.25,
            )

        self.assertEqual(items, [])
        self.assertEqual(stats["status"], "error")
        self.assertEqual(stats["error"], "URLError")
        self.assertEqual(stats["attempts"], 2)
        self.assertTrue(stats["retried"])
        sleep_mock.assert_called_once_with(0.25)

    def test_compute_retry_delay_respects_cap(self):
        delay = patchpulse._compute_retry_delay(0.5, attempt=3, backoff_cap_seconds=1.0)
        self.assertEqual(delay, 1.0)

    def test_compute_retry_delay_with_seeded_jitter_is_deterministic(self):
        rng_a = patchpulse.random.Random(42)
        rng_b = patchpulse.random.Random(42)

        delay_a = patchpulse._compute_retry_delay(
            1.0,
            attempt=2,
            backoff_cap_seconds=2.0,
            backoff_jitter_ratio=0.2,
            rng=rng_a,
        )
        delay_b = patchpulse._compute_retry_delay(
            1.0,
            attempt=2,
            backoff_cap_seconds=2.0,
            backoff_jitter_ratio=0.2,
            rng=rng_b,
        )

        self.assertAlmostEqual(delay_a, delay_b, places=10)
        self.assertGreaterEqual(delay_a, 1.6)
        self.assertLessEqual(delay_a, 2.4)

    def test_fetch_feed_with_stats_retry_sleep_uses_cap_and_seeded_jitter(self):
        with (
            patch("patchpulse.urlopen", side_effect=[URLError("flaky"), URLError("still bad")]),
            patch("patchpulse.time.sleep") as sleep_mock,
        ):
            items, stats = patchpulse.fetch_feed_with_stats(
                "Flaky Feed",
                "https://example.com/rss",
                retries=1,
                backoff_seconds=1.0,
                backoff_cap_seconds=0.5,
                backoff_jitter_ratio=0.2,
                jitter_seed=42,
            )

        self.assertEqual(items, [])
        self.assertEqual(stats["status"], "error")
        sleep_mock.assert_called_once()
        slept = sleep_mock.call_args[0][0]
        self.assertGreaterEqual(slept, 0.4)
        self.assertLessEqual(slept, 0.6)

    def test_fetch_feed_skips_items_with_missing_fields(self):
        rss = b"""<?xml version='1.0' encoding='UTF-8'?>
<rss><channel>
  <item><title>Valid</title><link>https://example.com/valid</link></item>
  <item><title>No link</title></item>
  <item><link>https://example.com/no-title</link></item>
</channel></rss>
"""
        with patch("patchpulse.urlopen", return_value=_FakeResponse(rss)):
            items, stats = patchpulse.fetch_feed_with_stats("RSS", "https://example.com/rss")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Valid")
        self.assertEqual(stats["status"], "ok")
        self.assertEqual(stats["items"], 1)
        self.assertEqual(stats["skipped"], 2)

    def test_fetch_feed_atom_prefers_alternate_link(self):
        atom = b"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom'>
  <entry>
    <title>Atom entry</title>
    <link rel='self' href='https://example.com/self'/>
    <link rel='alternate' href='https://example.com/alternate'/>
  </entry>
</feed>
"""
        with patch("patchpulse.urlopen", return_value=_FakeResponse(atom)):
            items = patchpulse.fetch_feed("Atom", "https://example.com/atom")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["url"], "https://example.com/alternate")

    def test_render_discord_payload_shape_and_limit(self):
        items = [
            {
                "topic": "Safety & Policy",
                "priority": 3,
                "title": "Critical security update",
                "url": "https://example.com/a",
                "source": "Feed A",
                "published": "2026-04-16T10:00:00Z",
            },
            {
                "topic": "Developer Tooling",
                "priority": 1,
                "title": "New CLI integration",
                "url": "https://example.com/b",
                "source": "Feed B",
                "published": "2026-04-16T09:00:00Z",
            },
        ]
        source_stats = [
            {"source": "Feed A", "status": "ok", "items": 2, "skipped": 1, "attempts": 1, "retried": False},
            {"source": "Feed B", "status": "error", "items": 0, "skipped": 0, "error": "URLError", "attempts": 3, "retried": True},
        ]

        payload = patchpulse.render_discord_payload(items, "2026-04-16", limit=1, source_stats=source_stats)

        self.assertEqual(payload["type"], "discord_message_payload")
        self.assertEqual(payload["date"], "2026-04-16")
        self.assertEqual(payload["item_count"], 1)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["rank"], 1)
        self.assertEqual(payload["items"][0]["title"], "Critical security update")
        self.assertIn("PatchPulse Digest", payload["message"])

        self.assertIn("source_summary", payload)
        self.assertEqual(len(payload["source_summary"]), 2)
        self.assertEqual(payload["source_summary"][1]["status"], "error")
        self.assertEqual(payload["source_summary"][1]["error"], "URLError")
        self.assertEqual(payload["source_summary"][1]["attempts"], 3)
        self.assertTrue(payload["source_summary"][1]["retried"])
        self.assertEqual(payload["source_summary_totals"]["sources"], 2)
        self.assertEqual(payload["source_summary_totals"]["errors"], 1)
        self.assertEqual(payload["source_summary_totals"]["items"], 2)
        self.assertEqual(payload["source_summary_totals"]["skipped"], 1)
        self.assertEqual(payload["source_summary_totals"]["retried_sources"], 1)
        self.assertEqual(payload["source_summary_totals"]["total_attempts"], 4)

    def test_render_report_includes_source_summary(self):
        report = patchpulse.render_report(
            [],
            "2026-04-17",
            source_stats=[
                {"source": "Feed A", "status": "ok", "items": 2, "skipped": 1, "attempts": 1, "retried": False},
                {"source": "Feed B", "status": "error", "error": "URLError", "attempts": 2, "retried": True},
            ],
        )

        self.assertIn("## Source Summary", report)
        self.assertIn("Feed A: items=2, skipped=1, attempts=1, retried=false", report)
        self.assertIn("Feed B: ERROR (URLError), attempts=2, retried=true", report)

    def test_render_discord_digest_source_health_mode_errors_only(self):
        digest_ok = patchpulse.render_discord_digest(
            [
                {
                    "topic": "Model Releases",
                    "priority": 3,
                    "title": "Major model launch",
                    "url": "https://example.com/a",
                    "source": "Feed A",
                }
            ],
            "2026-04-20",
            limit=3,
            source_stats=[{"source": "Feed A", "status": "ok", "items": 1, "skipped": 0}],
            include_source_health=True,
            source_health_mode="errors-only",
        )
        self.assertNotIn("Feed health:", digest_ok)

        digest_error = patchpulse.render_discord_digest(
            [
                {
                    "topic": "Model Releases",
                    "priority": 3,
                    "title": "Major model launch",
                    "url": "https://example.com/a",
                    "source": "Feed A",
                }
            ],
            "2026-04-20",
            limit=3,
            source_stats=[
                {"source": "Feed A", "status": "ok", "items": 1, "skipped": 0},
                {"source": "Feed B", "status": "error", "items": 0, "skipped": 0, "error": "URLError"},
            ],
            include_source_health=True,
            source_health_mode="errors-only",
        )
        self.assertIn("Feed health: 1 source with errors (Feed B)", digest_error)

    def test_render_discord_digest_source_health_mode_always(self):
        digest = patchpulse.render_discord_digest(
            [
                {
                    "topic": "Model Releases",
                    "priority": 3,
                    "title": "Major model launch",
                    "url": "https://example.com/a",
                    "source": "Feed A",
                }
            ],
            "2026-04-20",
            limit=3,
            source_stats=[{"source": "Feed A", "status": "ok", "items": 1, "skipped": 0}],
            include_source_health=True,
            source_health_mode="always",
        )

        self.assertIn("Feed health: all sources OK", digest)

    def test_resolve_source_retry_config_prefers_source_overrides(self):
        args = type(
            "Args",
            (),
            {
                "source_retries": 1,
                "retry_backoff_seconds": 0.5,
                "retry_backoff_cap_seconds": 2.0,
                "retry_backoff_jitter_ratio": 0.1,
                "retry_jitter_seed": 123,
            },
        )()

        cfg = patchpulse.resolve_source_retry_config(
            {
                "retries": 4,
                "retry_backoff_seconds": 1.25,
                "retry_backoff_cap_seconds": 3.5,
                "retry_backoff_jitter_ratio": 0.3,
                "retry_jitter_seed": 42,
            },
            args,
        )

        self.assertEqual(cfg["retries"], 4)
        self.assertEqual(cfg["backoff_seconds"], 1.25)
        self.assertEqual(cfg["backoff_cap_seconds"], 3.5)
        self.assertEqual(cfg["backoff_jitter_ratio"], 0.3)
        self.assertEqual(cfg["jitter_seed"], 42)

    def test_main_applies_per_source_retry_overrides(self):
        calls = []

        def _fake_fetch(name, url, **kwargs):
            calls.append({"name": name, "url": url, **kwargs})
            return [], {"source": name, "status": "ok", "items": 0, "skipped": 0, "attempts": 1, "retried": False}

        with (
            patch("patchpulse.Path.mkdir"),
            patch(
                "patchpulse.load_sources",
                return_value=[
                    {
                        "name": "A",
                        "url": "https://example.com/a",
                        "retries": 3,
                        "retry_backoff_seconds": 1.5,
                    },
                    {"name": "B", "url": "https://example.com/b"},
                ],
            ),
            patch("patchpulse.fetch_feed_with_stats", side_effect=_fake_fetch),
            patch("patchpulse.print_source_summary"),
            patch("patchpulse.argparse.ArgumentParser.parse_args") as parse_args,
        ):
            parse_args.return_value = type(
                "Args",
                (),
                {
                    "sources": "data/sources.json",
                    "outdir": "reports",
                    "format": "markdown",
                    "limit": 8,
                    "source_health_footer": False,
                    "source_health_mode": "errors-only",
                    "fail_on_source_errors": False,
                    "max_source_errors": None,
                    "source_retries": 1,
                    "retry_backoff_seconds": 0.25,
                    "retry_backoff_cap_seconds": 2.0,
                    "retry_backoff_jitter_ratio": 0.2,
                    "retry_jitter_seed": 7,
                },
            )()

            rc = patchpulse.main()

        self.assertEqual(rc, 0)
        self.assertEqual(calls[0]["retries"], 3)
        self.assertEqual(calls[0]["backoff_seconds"], 1.5)
        self.assertEqual(calls[1]["retries"], 1)
        self.assertEqual(calls[1]["backoff_seconds"], 0.25)

    def test_main_fail_on_source_errors_returns_2(self):
        with (
            patch("patchpulse.Path.mkdir"),
            patch("patchpulse.load_sources", return_value=[{"name": "Broken", "url": "https://example.com/rss"}]),
            patch("patchpulse.fetch_feed_with_stats", return_value=([], {"source": "Broken", "status": "error", "error": "URLError", "items": 0, "skipped": 0})),
            patch("patchpulse.print_source_summary"),
            patch("patchpulse.argparse.ArgumentParser.parse_args") as parse_args,
        ):
            parse_args.return_value = type(
                "Args",
                (),
                {
                    "sources": "data/sources.json",
                    "outdir": "reports",
                    "format": "markdown",
                    "limit": 8,
                    "source_health_footer": False,
                    "source_health_mode": "errors-only",
                    "fail_on_source_errors": True,
                    "max_source_errors": None,
                    "source_retries": 0,
                    "retry_backoff_seconds": 0.0,
                    "retry_backoff_cap_seconds": None,
                    "retry_backoff_jitter_ratio": 0.0,
                    "retry_jitter_seed": None,
                },
            )()

            rc = patchpulse.main()

        self.assertEqual(rc, 2)

    def test_main_max_source_errors_allows_threshold(self):
        with (
            patch("patchpulse.Path.mkdir"),
            patch("patchpulse.load_sources", return_value=[{"name": "A", "url": "https://example.com/a"}, {"name": "B", "url": "https://example.com/b"}]),
            patch(
                "patchpulse.fetch_feed_with_stats",
                side_effect=[
                    ([], {"source": "A", "status": "error", "error": "URLError", "items": 0, "skipped": 0}),
                    ([], {"source": "B", "status": "ok", "items": 0, "skipped": 0}),
                ],
            ),
            patch("patchpulse.print_source_summary"),
            patch("patchpulse.argparse.ArgumentParser.parse_args") as parse_args,
        ):
            parse_args.return_value = type(
                "Args",
                (),
                {
                    "sources": "data/sources.json",
                    "outdir": "reports",
                    "format": "markdown",
                    "limit": 8,
                    "source_health_footer": False,
                    "source_health_mode": "errors-only",
                    "fail_on_source_errors": False,
                    "max_source_errors": 1,
                    "source_retries": 0,
                    "retry_backoff_seconds": 0.0,
                    "retry_backoff_cap_seconds": None,
                    "retry_backoff_jitter_ratio": 0.0,
                    "retry_jitter_seed": None,
                },
            )()

            rc = patchpulse.main()

        self.assertEqual(rc, 0)

    def test_main_max_source_errors_exceeds_threshold_returns_2(self):
        with (
            patch("patchpulse.Path.mkdir"),
            patch("patchpulse.load_sources", return_value=[{"name": "A", "url": "https://example.com/a"}, {"name": "B", "url": "https://example.com/b"}]),
            patch(
                "patchpulse.fetch_feed_with_stats",
                side_effect=[
                    ([], {"source": "A", "status": "error", "error": "URLError", "items": 0, "skipped": 0}),
                    ([], {"source": "B", "status": "error", "error": "HTTPError", "items": 0, "skipped": 0}),
                ],
            ),
            patch("patchpulse.print_source_summary"),
            patch("patchpulse.argparse.ArgumentParser.parse_args") as parse_args,
        ):
            parse_args.return_value = type(
                "Args",
                (),
                {
                    "sources": "data/sources.json",
                    "outdir": "reports",
                    "format": "markdown",
                    "limit": 8,
                    "source_health_footer": False,
                    "source_health_mode": "errors-only",
                    "fail_on_source_errors": False,
                    "max_source_errors": 1,
                    "source_retries": 0,
                    "retry_backoff_seconds": 0.0,
                    "retry_backoff_cap_seconds": None,
                    "retry_backoff_jitter_ratio": 0.0,
                    "retry_jitter_seed": None,
                },
            )()

            rc = patchpulse.main()

        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
