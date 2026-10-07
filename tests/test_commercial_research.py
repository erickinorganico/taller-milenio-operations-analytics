import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import research_company as r


class ResearchTests(unittest.TestCase):
    def test_blocks_platforms_and_credentials(self):
        for url in ["https://www.linkedin.com/company/test", "https://maps.google.com/", "http://user:pass@example.com/", "file:///tmp/test", "https://example.com:8080/", "https://example.com/?token=abc"]:
            with self.subTest(url=url), self.assertRaises(ValueError): r.normalize(url)

    def test_private_resolved_addresses_fail(self):
        with patch.object(r.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]):
            with self.assertRaises(ValueError): r.public_addresses("example.test", 443)

    def test_cross_host_redirect_rejected_before_connection(self):
        with self.assertRaises(ValueError): r.fetch("https://other.test/", "example.test")

    def test_bounded_scrape_and_cache(self):
        body = "<html><body><main><h1>Empresa de prueba</h1><p>" + ("Atendemos servicios empresariales en Tijuana. " * 20) + "</p>" + "".join(f'<a href="/servicios/{n}">Servicio</a>' for n in range(10)) + "</main></body></html>"
        def fake(url, host, **kwargs): return (404, "", url) if url.endswith("robots.txt") else (200, body, url)
        with tempfile.TemporaryDirectory() as directory, patch.object(r, "fetch", side_effect=fake) as fetch, patch.object(r.time, "sleep"):
            result = r.investigate("https://example.test", cache_dir=directory)
            self.assertEqual(len(result["pages"]), 4)
            self.assertEqual(result["successful_pages"], 4)
            self.assertEqual(fetch.call_count, 5)
            again = r.investigate("https://example.test", cache_dir=directory)
            self.assertTrue(again["cache_hit"])
            self.assertEqual(fetch.call_count, 5)

    def test_robots_denial_visible(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(r, "fetch", return_value=(200, "User-agent: *\nDisallow: /", "https://example.test/robots.txt")) as fetch:
            result = r.investigate("https://example.test", cache_dir=directory)
            self.assertEqual(result["successful_pages"], 0)
            self.assertEqual(result["pages"][0]["status"], "failed")
            self.assertEqual(fetch.call_count, 1)


if __name__ == "__main__": unittest.main()
