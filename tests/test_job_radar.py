import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from job_radar import filters, insights, notify, settings, sources, store
from job_radar.sources import Job

SEARCH = {
    "titles": ["devops", "backend", "back end", "software engineer"],
    "exclude_titles": ["senior", "lead"],
    "boost_titles": ["junior"],
    "locations": ["israel", "tel aviv"],
}

DESC = (
    "About Acme\n"
    "Acme is a fast-growing company founded in 2015 with offices worldwide and many customers.\n\n"
    "What you'll do\n"
    "- Build and maintain CI/CD pipelines on AWS\n"
    "- Run Docker and Kubernetes clusters for our services\n\n"
    "Requirements\n"
    "- 2+ years of experience with Linux\n"
    "- Experience with Terraform\n"
    "- Hebrew speaker, hybrid work from our Tel Aviv office"
)


def job(title, location="Tel Aviv, Israel", id="1", description=""):
    return Job("greenhouse", "Acme", id, title, location, "https://x.test/" + id, description)


class ParserTests(unittest.TestCase):
    def test_greenhouse_with_escaped_html(self):
        data = {"jobs": [{"id": 7, "title": "DevOps Engineer", "location": {"name": "Tel Aviv"},
                          "absolute_url": "https://g/7",
                          "content": "&lt;p&gt;Build things &amp;amp; ship&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Docker&lt;/li&gt;&lt;/ul&gt;"}]}
        j = sources.parse_greenhouse("Acme", data)[0]
        self.assertEqual((j.id, j.title, j.location, j.url), ("7", "DevOps Engineer", "Tel Aviv", "https://g/7"))
        self.assertIn("Build things & ship", j.description)
        self.assertIn("- Docker", j.description)
        self.assertNotIn("<", j.description)

    def test_lever_description_and_lists(self):
        data = [{"id": "abc", "text": "Backend Dev", "categories": {"location": "Israel"},
                 "hostedUrl": "https://l/abc", "descriptionPlain": "We build payments.",
                 "lists": [{"text": "Requirements", "content": "<li>Python</li><li>SQL</li>"}],
                 "additionalPlain": "Great team."}]
        j = sources.parse_lever("Acme", data)[0]
        self.assertEqual((j.id, j.title, j.location), ("abc", "Backend Dev", "Israel"))
        for part in ("We build payments.", "Requirements", "- Python", "Great team."):
            self.assertIn(part, j.description)

    def test_ashby_remote_and_description(self):
        data = {"jobs": [{"id": "z", "title": "SRE", "location": "Israel", "isRemote": True,
                          "jobUrl": "https://a/z", "descriptionPlain": "Keep it running."}]}
        j = sources.parse_ashby("Acme", data)[0]
        self.assertEqual(j.location, "Israel (Remote)")
        self.assertEqual(j.description, "Keep it running.")

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


class InsightsTests(unittest.TestCase):
    def test_summary_skips_company_intro(self):
        s = insights.summary(DESC)
        self.assertIn("CI/CD", s)
        self.assertNotIn("founded", s)
        self.assertNotIn("Terraform", s)  # stops before "Requirements"
        self.assertLessEqual(len(s), 321)

    def test_summary_falls_back_to_start(self):
        s = insights.summary("We are hiring a developer to build our new mobile app for customers.")
        self.assertIn("mobile app", s)

    def test_years(self):
        self.assertEqual(insights.years_required(DESC), 2)
        self.assertIsNone(insights.years_required("Founded 10 years ago. Great snacks."))

    def test_good_to_know(self):
        lines = insights.good_to_know(job("Junior DevOps Engineer", description=DESC),
                                      ["AWS", "Docker", "Java"])
        text = "\n".join(lines)
        self.assertIn("Junior-level role", text)
        self.assertIn("2+ years", text)
        self.assertIn("Matches your skills: AWS, Docker", text)
        self.assertIn("Also asks for:", text)
        self.assertIn("Terraform", text)
        self.assertIn("Hybrid", text)
        self.assertIn("Hebrew", text)

    def test_java_is_not_javascript(self):
        self.assertEqual(insights.tech_found("we use JavaScript daily"), ["JavaScript"])

    def test_no_description(self):
        lines = insights.good_to_know(job("DevOps Engineer"), ["AWS"])
        self.assertEqual(lines, [])


class StoreTests(unittest.TestCase):
    def test_roundtrip_and_prune(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sub" / "seen.json"
            self.assertEqual(store.load(p), {})
            store.save(p, {"a": "2026-01-01", "b": "2026-10-30", "c": "2026-01-01"})
            seen = store.load(p)
            pruned = store.prune(seen, {"c"}, date(2026, 11, 1))
            self.assertEqual(set(pruned), {"b", "c"})


class NotifyTests(unittest.TestCase):
    def test_message_has_all_parts(self):
        msg = notify.format_job_message(job("Junior DevOps Engineer", description=DESC), ["AWS"])
        for part in ("Junior DevOps Engineer", "Acme", "Tel Aviv, Israel", "📝", "💡", 'href="https://x.test/1"'):
            self.assertIn(part, msg)
        self.assertLess(len(msg), 4096)

    def test_escapes_html(self):
        msg = notify.format_job_message(job("A <b>& B", id="9"))
        self.assertIn("A &lt;b&gt;&amp; B", msg)

    def test_no_description_still_works(self):
        msg = notify.format_job_message(job("Backend Developer"))
        self.assertIn("No description available", msg)
        self.assertIn("https://x.test/1", msg)

    def test_plain_keeps_link(self):
        plain = notify.to_plain(notify.format_job_message(job("Backend Developer", description=DESC)))
        self.assertIn("Open the job: https://x.test/1", plain)
        self.assertNotIn("<b>", plain)


class SettingsTests(unittest.TestCase):
    BASE = {"search": {"titles": ["devops"], "exclude_titles": ["senior"], "boost_titles": [],
                       "locations": ["israel"]}, "profile": {"skills": ["AWS"]}}

    def _write(self, d, content):
        p = Path(d) / "my_search.json"
        p.write_text(content, encoding="utf-8")
        return p

    def test_missing_file_changes_nothing(self):
        cfg, used = settings.apply_overrides(self.BASE, "/nonexistent/my_search.json")
        self.assertFalse(used)
        self.assertEqual(cfg, self.BASE)

    def test_override_replaces_lists(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, json.dumps({
                "titles": ["qa", "sdet"], "exclude_titles": [], "boost_titles": ["junior"],
                "locations": ["tel aviv"], "skills": ["Python"], "field": "QA"}))
            cfg, used = settings.apply_overrides(self.BASE, p)
        self.assertTrue(used)
        self.assertEqual(cfg["search"]["titles"], ["qa", "sdet"])
        self.assertEqual(cfg["search"]["exclude_titles"], [])       # empty is allowed: any level
        self.assertEqual(cfg["search"]["boost_titles"], ["junior"])
        self.assertEqual(cfg["search"]["locations"], ["tel aviv"])
        self.assertEqual(cfg["profile"]["skills"], ["Python"])
        self.assertEqual(self.BASE["search"]["titles"], ["devops"])  # original untouched

    def test_empty_titles_keeps_old_ones(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, json.dumps({"titles": []}))
            cfg, _ = settings.apply_overrides(self.BASE, p)
        self.assertEqual(cfg["search"]["titles"], ["devops"])

    def test_broken_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, "{not json")
            cfg, used = settings.apply_overrides(self.BASE, p)
        self.assertFalse(used)
        self.assertEqual(cfg, self.BASE)

    def test_pages_url(self):
        self.assertEqual(settings.pages_url("Matar/job-radar"), "https://matar.github.io/job-radar/")
        self.assertIsNone(settings.pages_url(None))
        self.assertIsNone(settings.pages_url("nonsense"))


class ButtonTests(unittest.TestCase):
    def test_button_added_only_when_url_given(self):
        self.assertNotIn("reply_markup", notify.build_payload("1", "hi"))
        p = notify.build_payload("1", "hi", "https://x.github.io/r/")
        markup = json.loads(p["reply_markup"])
        self.assertEqual(markup["inline_keyboard"][0][0]["url"], "https://x.github.io/r/")


class ConfigTests(unittest.TestCase):
    def test_default_config_loads(self):
        import tomllib
        cfg = tomllib.loads((Path(__file__).parent.parent / "config.toml").read_text(encoding="utf-8"))
        self.assertTrue(cfg["companies"])
        self.assertTrue(cfg["profile"]["skills"])
        filters.Matcher(cfg["search"])


if __name__ == "__main__":
    unittest.main()
