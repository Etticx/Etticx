import importlib.util
from pathlib import Path
import unittest
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("update_profile", ROOT / "scripts/update_profile.py")
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


class ProfileTests(unittest.TestCase):
    def test_paginates_and_excludes_private_repos_and_fork_stars(self):
        calls = []
        def fake(path):
            calls.append(path)
            if path == "users/Etticx":
                return {"followers": 6, "created_at": "2020-06-18T02:21:36Z"}
            if path.startswith("search/commits?"):
                self.assertIn("is%3Apublic", path)
                return {"total_count": 123, "incomplete_results": False}
            if path.endswith("&page=1"):
                return [{"private": False, "fork": False, "stargazers_count": 2}] * 100
            return [
                {"private": True, "fork": False, "stargazers_count": 900},
                {"private": False, "fork": True, "stargazers_count": 500},
            ]
        result = profile.collect_stats("Etticx", fake)
        self.assertEqual(result["public_repos"], 101)
        self.assertEqual(result["stars"], 200)
        self.assertEqual(result["commits"], 123)
        self.assertTrue(any("page=2" in path for path in calls))

    def test_incomplete_commit_results_fail_instead_of_publishing_bad_stats(self):
        def fake(path):
            if path == "users/Etticx":
                return {}
            if path.startswith("users/Etticx/repos?"):
                return []
            return {"incomplete_results": True}
        with self.assertRaisesRegex(RuntimeError, "incomplete commit count"):
            profile.collect_stats("Etticx", fake)

    def test_invalid_username_is_rejected_before_network(self):
        with self.assertRaises(ValueError):
            profile.collect_stats("../someone")

    def test_actual_cards_are_valid_svg_with_escaped_contact(self):
        import json
        config = json.loads((ROOT / "profile/config.json").read_text())
        stats = json.loads((ROOT / "profile/stats.json").read_text())
        portrait = (ROOT / "profile/avatar.txt").read_text()
        for theme in profile.THEMES:
            with self.subTest(theme=theme):
                svg = profile.render(config, stats, portrait, theme)
                root = ET.fromstring(svg)
                text = "".join(root.itertext())
                self.assertIn("Game Dev & Business Analyst @ PETRONAS", text)
                self.assertIn("SHIELD / BioGuard", text)
                self.assertIn("indexed", text)
                self.assertEqual(len(root.findall(".//{http://www.w3.org/2000/svg}text[@class='portrait']")), 32)

    def test_overflowing_bio_fails_instead_of_clipping(self):
        import json
        config = json.loads((ROOT / "profile/config.json").read_text())
        stats = json.loads((ROOT / "profile/stats.json").read_text())
        config["about"] = [["Test", "x" * 100]]
        with self.assertRaisesRegex(ValueError, "too long"):
            profile.render(config, stats, "ASCII", "dark")


if __name__ == "__main__":
    unittest.main()
