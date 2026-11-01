import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from job_radar import filters, notify, sources, store
from job_radar.sources import Job

SEARCH = {
    "titles": ["devops", "backend", "back end", "software engineer"],
    "exclude_titles": ["senior", "lead"],
    "boost_titles": ["junior"],
    "locations": ["israel", "tel aviv"],
}


def job(title, location="Tel Aviv, Israel", id="1"):
    return Job("greenhouse", "Acme", id, title, location, "https://x.test/" + id)


class ParserTests(unittest.TestCase):
    def test_greenhouse(self):
        data = {"jobs": [{"id": 7, "title": "DevOps Engineer",
                          "location": {"name": "Tel Aviv"}, "absolute_url": "https://g/7"}]}
        j = sources.parse_greenhouse("Acme", data)[0]
        self.assertEqual((j.id, j.title, j.location, j.url), ("7", "DevOps Engineer", "Tel Aviv", "https://g/7"))

    def test_lever(self):
        data = [{"id": "abc", "text": "Backend Dev", "categories": {"location": "Israel"},
                 "hostedUrl": "https://l/abc"}]
        j = sources.parse_lever("Acme", data)[0]
        self.assertEqual((j.id, j.title, j.location), ("abc", "Backend Dev", "Israel"))

    def test_ashby_remote(self):
        data = {"jobs": [{"id": "z", "title": "SRE", "location": "Israel", "isRemote": True,
                          "jobUrl": "https://a/z"}]}
        self.assertEqual(sources.parse_ashby("Acme", data)[0].location, "Israel (Remote)")

    def test_missing_fields_dont_crash(self):
        self.assertEqual(len(sources.parse_greenhouse("A", {"jobs": [{"id": 1}]})), 1)


class MatcherTests(unittest.TestCase):
    def setUp(self):
        self.m = filters.Matcher(SEARCH)

    def test_match(self):
        self.assertIsNotNone(self.m.score(job("DevOps Engineer")))

    def test_excluded_seniority(self):
        self.assertIsNone(self.m.score(job("Senior DevOps Engineer")))

    def test_no_title_keyword(self):
        self.assertIsNone(self.m.score(job("Product Designer")))

    def test_wrong_location(self):
        self.assertIsNone(self.m.score(job("DevOps Engineer", "New York, USA")))

    def test_unknown_location_default_excluded(self):
        self.assertIsNone(self.m.score(job("DevOps Engineer", "")))

    def test_junior_ranks_higher(self):
        self.assertGreater(self.m.score(job("Junior Backend Developer")),
                           self.m.score(job("Backend Developer")))

    def test_word_boundaries(self):
        # "lead" must not exclude "Misleading..." style substrings
        self.assertIsNotNone(self.m.score(job("Backend Engineer, Pleaded Systems")))


class StoreTests(unittest.TestCase):
    def test_roundtrip_and_prune(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sub" / "seen.json"
            self.assertEqual(store.load(p), {})
            store.save(p, {"a": "2026-01-01", "b": "2026-10-30", "c": "2026-01-01"})
            seen = store.load(p)
            pruned = store.prune(seen, {"c"}, date(2026, 11, 1))
            self.assertEqual(set(pruned), {"b", "c"})  # a: old and gone; c: still listed


class NotifyTests(unittest.TestCase):
    def test_escapes_html(self):
        msg = notify.format_digest([job("A <b>& B", id="9")])[0]
        self.assertIn("A &lt;b&gt;&amp; B", msg)

    def test_splits_long_digest(self):
        jobs = [job("Backend Engineer " + "x" * 200, id=str(i)) for i in range(60)]
        msgs = notify.format_digest(jobs)
        self.assertGreater(len(msgs), 1)
        self.assertTrue(all(len(m) <= 4096 for m in msgs))

    def test_empty(self):
        self.assertEqual(notify.format_digest([]), [])


class ConfigTests(unittest.TestCase):
    def test_default_config_loads(self):
        import tomllib
        cfg = tomllib.loads((Path(__file__).parent.parent / "config.toml").read_text(encoding="utf-8"))
        self.assertTrue(cfg["companies"])
        filters.Matcher(cfg["search"])


if __name__ == "__main__":
    unittest.main()
