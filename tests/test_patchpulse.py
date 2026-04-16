import pathlib
import sys
import unittest

# Allow importing from src/
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import patchpulse  # noqa: E402


class PatchPulseCoreTests(unittest.TestCase):
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

        payload = patchpulse.render_discord_payload(items, "2026-04-16", limit=1)

        self.assertEqual(payload["type"], "discord_message_payload")
        self.assertEqual(payload["date"], "2026-04-16")
        self.assertEqual(payload["item_count"], 1)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["rank"], 1)
        self.assertEqual(payload["items"][0]["title"], "Critical security update")
        self.assertIn("PatchPulse Digest", payload["message"])


if __name__ == "__main__":
    unittest.main()
