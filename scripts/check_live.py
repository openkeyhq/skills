#!/usr/bin/env python3
"""Live gate: every URL and model id the pack cites must still match the real API.

Exit 0 all match; 1 mismatch or unknown model (printed); 2 network error.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_FACTS = Path(__file__).with_name("live_facts.json")
MODELS_URL = "https://api.openkey.ai/v1/models"
# The edge answers 403 to urllib's default User-Agent.
UA = {"User-Agent": "openkey-skills-check/1.0"}


def load_facts(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def probe(method: str, url: str, timeout: float) -> int:
    """Unauthenticated request; returns the status even for 4xx/5xx."""
    data = b"{}" if method == "POST" else None
    headers = dict(UA, **({"Content-Type": "application/json"} if data else {}))
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def make_fetch(timeout: float):
    def fetch(url: str) -> dict:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as resp:
            return json.load(resp)
    return fetch


def live_ids(fetch) -> set:
    return {m["id"] for m in fetch(MODELS_URL)["data"]}


def check(facts: dict, probe=probe, fetch=None, timeout: float = 10) -> list:
    fetch = fetch or make_fetch(timeout)
    problems = []
    targets = [(e["method"], e["url"], e["expect"]) for e in facts["endpoints"]]
    targets += [("GET", url, 200) for url in facts["docs"]]
    for method, url, expect in targets:
        got = probe(method, url, timeout)
        if got != expect:
            problems.append(f"MISMATCH {method} {url} expected {expect} got {got}")
    known = live_ids(fetch)
    problems += [f"UNKNOWN_MODEL {m}" for m in facts["example_models"] if m not in known]
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--facts", type=Path, default=DEFAULT_FACTS)
    ap.add_argument("--timeout", type=float, default=10)
    args = ap.parse_args(argv)
    try:
        problems = check(load_facts(args.facts), timeout=args.timeout)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"NETWORK_ERROR {e}", file=sys.stderr)
        return 2
    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
