import html
from pathlib import Path
import re
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_profile_cards as cards
import update_profile_stats as stats


class ProfileCardsTests(unittest.TestCase):
    def test_cards_keep_every_skill_accessible(self):
        readme = html.unescape((ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("Skills as text", readme)
        for group, _, items in cards.GROUPS:
            with self.subTest(group=group):
                self.assertIn(group, readme)
                for skill, _ in items:
                    self.assertIn(skill, readme)

    def test_generated_cards_are_self_contained_and_reproducible(self):
        for mobile, filename in ((False, "tech-cards.svg"), (True, "tech-cards-mobile.svg")):
            with self.subTest(filename=filename):
                rendered = cards.render_tech_cards(mobile=mobile)
                self.assertEqual(rendered, (ROOT / "assets" / filename).read_text(encoding="utf-8"))
                root = ET.fromstring(rendered)
                ids = [node.get("id") for node in root.iter() if node.get("id")]
                self.assertEqual(len(ids), len(set(ids)), "SVG IDs must not collide")
                references = re.findall(r"url\(#([^)]+)\)", rendered)
                self.assertTrue(set(references).issubset(set(ids)), "Every gradient reference must resolve")
                self.assertNotIn("<script", rendered.lower())
                self.assertNotIn("<image", rendered.lower())
                self.assertIn("Google Apps Script", rendered)
                self.assertIn("SQL", rendered)

    def test_contact_destinations_are_the_verified_ones(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn('href="https://bmaquino-lab.github.io/PORTFOLIO-WEBSITE/"', readme)
        self.assertIn('href="https://www.linkedin.com/in/aquino-brian/"', readme)
        self.assertIn('href="mailto:aquinobrianmichael@gmail.com"', readme)
        self.assertNotIn("brian.aquino.dev@gmail.com", readme)

    def test_daily_stats_refresh_preserves_cards_and_links(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        updated = stats.update_readme(readme, {"repositories": 7, "stars": 2, "contributions": 31})
        self.assertEqual(readme.split(stats.END, 1)[1], updated.split(stats.END, 1)[1])

    def test_footer_is_reproducible_and_describes_membership(self):
        for mobile, filename in ((False, "profile-footer.svg"), (True, "profile-footer-mobile.svg")):
            rendered = cards.render_footer(mobile=mobile)
            self.assertEqual(rendered, (ROOT / "assets" / filename).read_text(encoding="utf-8"))
            ET.fromstring(rendered)
            self.assertIn("YSES RESIDENT MEMBER", rendered)


if __name__ == "__main__":
    unittest.main()
