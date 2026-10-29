import datetime as dt
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import update_profile_stats as profile


class ProfileStatsTests(unittest.TestCase):
    def test_collects_all_pages_and_only_public_owned_repositories(self):
        repos = [
            {"private": False, "owner": {"login": "BMAquino-lab"}, "stargazers_count": i % 3}
            for i in range(98)
        ]
        repos += [
            {"private": True, "owner": {"login": "BMAquino-lab"}, "stargazers_count": 100},
            {"private": False, "owner": {"login": "someone-else"}, "stargazers_count": 100},
        ]
        last = [{"private": False, "owner": {"login": "BMAquino-lab"}, "stargazers_count": 5}]
        seen = []

        def fetch(url, token, payload=None):
            seen.append((url, token, payload))
            if url.endswith("page=1"):
                return repos
            if url.endswith("page=2"):
                return last
            self.assertEqual(url, "https://api.github.com/graphql")
            return {"data": {"user": {"contributionsCollection": {"contributionCalendar": {"totalContributions": 29}}}}}

        now = dt.datetime(2026, 10, 29, 3, tzinfo=dt.timezone.utc)
        result = profile.collect_metrics("token", fetch=fetch, now=now)
        self.assertEqual(result, {"repositories": 99, "stars": sum(i % 3 for i in range(98)) + 5, "contributions": 29})
        self.assertEqual(seen[-1][2]["variables"], {"login": "BMAquino-lab", "from": "2025-10-29T03:00:00Z", "to": "2026-10-29T03:00:00Z"})

    def test_api_error_does_not_create_a_fake_zero(self):
        def fetch(url, token, payload=None):
            if url.endswith("page=1"):
                return []
            return {"errors": [{"message": "not authorized"}]}

        with self.assertRaisesRegex(RuntimeError, "contributions response"):
            profile.collect_metrics("token", fetch=fetch)

    def test_generated_assets_and_accessible_text_are_idempotent(self):
        metrics = {"repositories": 6, "stars": 0, "contributions": 29}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "assets").mkdir()
            readme = root / "README.md"
            readme.write_text("intro\n" + profile.START + "\nold\n" + profile.END + "\nprojects\n", encoding="utf-8")
            self.assertTrue(profile.update_files(root, metrics))
            text = readme.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("intro\n" + profile.START))
            self.assertTrue(text.endswith(profile.END + "\nprojects\n"))
            self.assertIn("6 repositories, 0 stars, and 29 contributions", text)
            for name in ("profile-stats.svg", "profile-stats-mobile.svg"):
                svg = (root / "assets" / name).read_text(encoding="utf-8")
                ET.fromstring(svg)
                self.assertIn("29 public contributions", svg)
                self.assertIn("prefers-reduced-motion: no-preference", svg)
            self.assertFalse(profile.update_files(root, metrics))

    def test_missing_or_duplicate_markers_are_rejected(self):
        metrics = {"repositories": 6, "stars": 0, "contributions": 29}
        for text in ("unmarked", profile.START + profile.START + profile.END, profile.END + profile.START):
            with self.subTest(text=text), self.assertRaises(ValueError):
                profile.update_readme(text, metrics)


if __name__ == "__main__":
    unittest.main()
