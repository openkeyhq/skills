"""The live gate compares live_facts.json with the API. Tests inject a fake probe and fetch: no network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_live  # noqa: E402

MSG = "https://api.openkey.ai/v1/messages"
DOC = "https://openkey.ai/docs/models"
FACTS = {
    "endpoints": [
        {"method": "GET", "url": "https://api.openkey.ai/v1/models", "expect": 200},
        {"method": "POST", "url": MSG, "expect": 401},
    ],
    "example_models": ["openai/gpt-9", "acme/model-1"],
    "virtual_models": ["openkey/auto"],
    "docs": [DOC],
}
CATALOG = {"data": [{"id": "openai/gpt-9"}, {"id": "acme/model-1"}]}


def fake_probe(overrides=None):
    table = {("GET", "https://api.openkey.ai/v1/models"): 200, ("POST", MSG): 401, ("GET", DOC): 200}
    table.update(overrides or {})
    return lambda method, url, timeout: table[(method, url)]


def fake_fetch(catalog=CATALOG):
    return lambda url: catalog


def test_all_match_returns_no_problems():
    assert check_live.check(FACTS, fake_probe(), fake_fetch()) == []


def test_status_mismatch_reported():
    got = check_live.check(FACTS, fake_probe({("POST", MSG): 404}), fake_fetch())
    assert got == [f"MISMATCH POST {MSG} expected 401 got 404"]


def test_unknown_example_model_reported():
    catalog = {"data": [{"id": "acme/model-1"}]}
    assert check_live.check(FACTS, fake_probe(), fake_fetch(catalog)) == ["UNKNOWN_MODEL openai/gpt-9"]


def test_virtual_model_not_required_in_catalog():
    assert "openkey/auto" not in {m["id"] for m in CATALOG["data"]}
    assert check_live.check(FACTS, fake_probe(), fake_fetch()) == []


def test_doc_page_must_return_200():
    got = check_live.check(FACTS, fake_probe({("GET", DOC): 404}), fake_fetch())
    assert got == [f"MISMATCH GET {DOC} expected 200 got 404"]


def test_live_ids_reads_data_ids():
    assert check_live.live_ids(fake_fetch()) == {"openai/gpt-9", "acme/model-1"}
