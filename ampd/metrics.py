"""Metrics registry for the /metrics endpoint — Prometheus text format,
zero dependencies, thread-safe, and FLAT.

Design rules (the hard-won kind):
* The scrape path must NEVER touch the renderer. Everything /metrics serves
  is read from plain dicts that the live layers (browser watchdog, musickit
  status counting, stream/audio listener gauges) already maintain. A debug
  route that fights the renderer it is debugging is how /health hung once.
* Instrumentation at call sites is unconditional and must not be able to
  break a request — the registry methods are dict ops only, no locks held
  across user code.
"""
import threading

# fixed buckets (seconds) — covers the known shapes: instant pings, normal
# evals, slow evals (>5s is logged), stalled evals (~60s), bounded worst case
BUCKETS = (0.005, 0.025, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120)


def _key(name, labels):
    if not labels:
        return name
    inner = ",".join(f'{k}="{_escape(v)}"' for k, v in sorted(labels.items()))
    return f"{name}{{{inner}}}"


def _escape(v):
    return str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class Registry:
    """Counters + gauges + fixed-bucket histograms, rendered as text."""

    def __init__(self):
        self._lock = threading.Lock()
        self._counters = {}          # (name, labeltext) -> value
        self._gauges = {}            # (name, labeltext) -> value
        self._hist = {}              # name -> {"sum": f, "count": i, "buckets": {le: i}}
        self._meta = {}              # name -> help/type set at first use

    # ------------------------------------------------------------- record

    def _note(self, name, mtype, help_text):
        with self._lock:
            self._meta.setdefault(name, (mtype, help_text or name))

    def inc(self, name, labels=None, value=1, help_text=None):
        self._note(name, "counter", help_text)
        with self._lock:
            k = _key(name, labels or {})
            self._counters[k] = self._counters.get(k, 0) + value

    def gauge(self, name, value, labels=None, help_text=None):
        self._note(name, "gauge", help_text)
        with self._lock:
            self._gauges[_key(name, labels or {})] = value

    def observe(self, name, seconds, help_text=None):
        self._note(name, "histogram", help_text)
        with self._lock:
            h = self._hist.setdefault(name, {
                "sum": 0.0, "count": 0,
                "buckets": {le: 0 for le in BUCKETS}})
            h["sum"] += seconds
            h["count"] += 1
            for le in BUCKETS:
                if seconds <= le:
                    h["buckets"][le] += 1

    # ------------------------------------------------------------- render

    def render(self):
        """Prometheus text exposition. Deterministic ordering (dict insert
        order), monotonic buckets, +Inf closeout."""
        with self._lock:
            meta = dict(self._meta)
            counters = dict(self._counters)
            gauges = dict(self._gauges)
            hist = {n: {k: (dict(v) if k == "buckets" else v)
                        for k, v in h.items()} for n, h in self._hist.items()}
        out = []
        for name, (mtype, help_text) in meta.items():
            out.append(f"# HELP {name} {help_text}")
            out.append(f"# TYPE {name} {mtype}")
            if mtype == "counter":
                for k, v in counters.items():
                    if k.split("{")[0] == name:
                        out.append(f"{k} {_num(v)}")
            elif mtype == "gauge":
                for k, v in gauges.items():
                    if k.split("{")[0] == name:
                        out.append(f"{k} {_num(v)}")
            else:  # histogram
                h = hist.get(name, {"sum": 0.0, "count": 0, "buckets": {}})
                for le, c in h["buckets"].items():
                    out.append(f'{name}_bucket{{le="{_num(le)}"}} {c}')
                out.append(f'{name}_bucket{{le="+Inf"}} {h["count"]}')
                out.append(f'{name}_sum {_num(h["sum"])}')
                out.append(f'{name}_count {h["count"]}')
        return "\n".join(out) + "\n"


def _num(v):
    if isinstance(v, int):
        return str(v)
    return repr(float(v))


# module-level singleton
METRICS = Registry()
