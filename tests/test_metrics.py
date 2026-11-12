"""Unit tests for the metrics registry (Prometheus text format).

Scrapers are picky: label escaping, bucket monotonicity, +Inf closeout and
HELP/TYPE placement must all be exact or prometheus rejects the scrape.
"""
import os
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tonearm.metrics import Registry


class TestCounters(unittest.TestCase):
    def test_inc_and_labels(self):
        r = Registry()
        r.inc("tonearm_apple_requests_total", {"code": "2xx"})
        r.inc("tonearm_apple_requests_total", {"code": "2xx"})
        r.inc("tonearm_apple_requests_total", {"code": "4xx"}, value=5)
        out = r.render()
        self.assertIn('tonearm_apple_requests_total{code="2xx"} 2', out)
        self.assertIn('tonearm_apple_requests_total{code="4xx"} 5', out)
        self.assertIn("# TYPE tonearm_apple_requests_total counter", out)

    def test_label_escaping(self):
        r = Registry()
        r.inc("x_total", {"path": 'a"b\\c\nd'})
        self.assertIn('x_total{path="a\\"b\\\\c\\nd"} 1', r.render())

    def test_gauge_overwrite(self):
        r = Registry()
        r.gauge("depth", 3)
        r.gauge("depth", 7)
        self.assertIn("depth 7", r.render())
        self.assertNotIn("depth 3", r.render())


class TestHistogram(unittest.TestCase):
    def test_buckets_monotonic_with_inf(self):
        r = Registry()
        for v in (0.01, 0.3, 4.0, 90.0):
            r.observe("tonearm_cdp_eval_duration_seconds", v)
        out = r.render()
        buckets = [line for line in out.splitlines()
                   if line.startswith("tonearm_cdp_eval_duration_seconds_bucket")]
        counts = []
        for line in buckets:
            le, c = line.rsplit(" ", 1)
            if le.endswith('+Inf"'):
                self.assertEqual(c, "4", "+Inf must equal total count")
            counts.append(int(c))
        self.assertEqual(counts, sorted(counts), "buckets must be monotonic")
        self.assertIn("tonearm_cdp_eval_duration_seconds_sum 94.31", out)
        self.assertIn("tonearm_cdp_eval_duration_seconds_count 4", out)

    def test_empty_histogram_renders(self):
        r = Registry()
        r.observe("h", 0.5)
        out = r.render()
        self.assertIn('h_bucket{le="+Inf"} 1', out)
        self.assertIn("h_count 1", out)


class TestScrapeSafety(unittest.TestCase):
    def test_render_never_raises_on_weird_labels(self):
        r = Registry()
        r.inc("c_total", {"a": "", "b": "''", "c": "\\\\"})
        self.assertIn("c_total", r.render())

    def test_thread_safety_smoke(self):
        r = Registry()
        def hammer():
            for i in range(200):
                r.observe("h", (i % 100) / 1000)
                r.inc("c_total", {"t": str(i % 3)})
                r.gauge("g", i)
        threads = [threading.Thread(target=hammer) for _ in range(4)]
        for t in threads: t.start()
        for t in threads: t.join()
        out = r.render()
        # 800 increments spread over 3 labels
        total = sum(int(line.rsplit(" ", 1)[1]) for line in out.splitlines()
                    if line.startswith('c_total{'))
        self.assertEqual(total, 800)

    def test_deterministic_render(self):
        r = Registry()
        r.inc("c", {"k": "v"})
        r.gauge("g", 1)
        self.assertEqual(r.render(), r.render())


if __name__ == "__main__":
    unittest.main(verbosity=2)
