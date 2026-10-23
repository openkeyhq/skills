"""Every pack-lint rule has a passing and a failing fixture. The fixture is a
minimal valid pack built in a temp dir; each test breaks one thing."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import lint_pack  # noqa: E402

DESC = ("Runs a coding agent through OpenKey. Use when: \"run codex on openkey\", \"use openkey in cursor\". "
        "NOT for: connecting or listing (openkey).")
HUB_DESC = ("Entry point for OpenKey. Use when: \"OpenKey\", \"integrate my app\". "
            "NOT for: coding agents (openkey-agents).")


def write(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def skill(root: Path, name: str, desc: str, body: str = "Body.\n\nRead `references/notes.md` when unsure.\n", refs=None, extra_fm: str = ""):
    write(root / "skills" / name / "SKILL.md",
          f"---\nname: {name}\ndescription: >-\n  {desc}\nlicense: MIT\n{extra_fm}---\n\n# {name}\n\n{body}")
    for ref, content in (refs if refs is not None else {"notes.md": "# Notes\n\nSet the base URL first.\n"}).items():
        write(root / "skills" / name / "references" / ref, content)


def make_pack(tmp_path: Path) -> Path:
    root = tmp_path / "pack"
    v = "0.1.0"
    write(root / "VERSION", v + "\n")
    write(root / "scripts" / "live_facts.json", json.dumps({"example_models": ["openai/gpt-5.2"], "virtual_models": ["openkey/auto"],
                                                            "endpoints": [], "docs": []}))
    write(root / ".claude-plugin" / "plugin.json", json.dumps({"name": "openkey", "version": v}))
    write(root / ".claude-plugin" / "marketplace.json", json.dumps({"name": "openkey", "metadata": {"version": v}, "plugins": [{"name": "openkey", "source": "./", "version": v}]}))
    write(root / ".codex-plugin" / "plugin.json", json.dumps({"name": "openkey", "version": v, "skills": "./skills/"}))
    write(root / ".cursor-plugin" / "plugin.json", json.dumps({"name": "openkey", "version": v, "skills": "./skills/"}))
    write(root / "README.md", "# Pack\n\n| Skill | What |\n|---|---|\n| [`openkey`](skills/openkey/SKILL.md) | hub |\n| [`openkey-agents`](skills/openkey-agents/SKILL.md) | ads |\n\nSee [INSTALL.md](INSTALL.md).\n")
    write(root / "INSTALL.md", "# Install\n")
    write(root / ".denylist", "# one per line\nacme-secret-client\nJane Realperson\n")
    skill(root, "openkey", HUB_DESC, body="Hub.\n\nRead `references/connect.md` to connect.\n",
          refs={"connect.md": "# Connect\n\nSet the base URL.\n"})
    skill(root, "openkey-agents", DESC)
    return root


def errors(root: Path) -> list[str]:
    return [f"{e.file}: {e.message}" for e in lint_pack.lint(root, require_denylist=True)]


def test_valid_pack_has_no_errors(tmp_path):
    assert errors(make_pack(tmp_path)) == []


# --- frontmatter ---------------------------------------------------------------

def test_unknown_frontmatter_key(tmp_path):
    root = make_pack(tmp_path); skill(root, "openkey-agents", DESC, extra_fm="argument-hint: x\n")
    assert any("argument-hint" in e for e in errors(root))


def test_allowed_tools_is_forbidden(tmp_path):
    root = make_pack(tmp_path); skill(root, "openkey-agents", DESC, extra_fm="allowed-tools: Read\n")
    assert any("allowed-tools" in e for e in errors(root))


def test_license_must_be_mit(tmp_path):
    root = make_pack(tmp_path)
    p = root / "skills/openkey-agents/SKILL.md"; p.write_text(p.read_text().replace("license: MIT", "license: Apache-2.0"))
    assert any("license" in e for e in errors(root))


def test_name_must_match_directory_and_prefix(tmp_path):
    root = make_pack(tmp_path)
    p = root / "skills/openkey-agents/SKILL.md"; p.write_text(p.read_text().replace("name: openkey-agents", "name: image-ads"))
    errs = errors(root)
    assert any("directory" in e for e in errs)


def test_reserved_words_and_xml_tags(tmp_path):
    root = make_pack(tmp_path)
    skill(root, "openkey-claude-helper", DESC)
    (root / "README.md").write_text((root / "README.md").read_text() + "| [`openkey-claude-helper`](skills/openkey-claude-helper/SKILL.md) | x |\n")
    assert any("reserved" in e for e in errors(root))
    root2 = make_pack(tmp_path / "b"); skill(root2, "openkey-agents", DESC + " <b>bold</b>")
    assert any("XML" in e for e in errors(root2))


def test_description_contract(tmp_path):
    root = make_pack(tmp_path); skill(root, "openkey-agents", "Makes coding agents. NOT for: editing (openkey-edit).")
    assert any("Use when:" in e for e in errors(root))
    root = make_pack(tmp_path / "b"); skill(root, "openkey-agents", "Makes coding agents. Use when: \"x\".")
    assert any("NOT for:" in e for e in errors(root))
    root = make_pack(tmp_path / "c"); skill(root, "openkey-agents", "I make coding agents. Use when: \"x\". NOT for: y (openkey).")
    assert any("first person" in e for e in errors(root))
    root = make_pack(tmp_path / "d"); skill(root, "openkey-agents", DESC + " " + "x" * 1024)
    assert any("1024" in e for e in errors(root))


def test_description_may_name_only_real_skills(tmp_path):
    root = make_pack(tmp_path); skill(root, "openkey-agents", DESC.replace("(openkey)", "(openkey-ghost)"))
    assert any("openkey-ghost" in e for e in errors(root))


# --- body and references -------------------------------------------------------

def test_body_length_limits(tmp_path):
    root = make_pack(tmp_path); skill(root, "openkey-agents", DESC, body="line\n" * 301 + "Read `references/notes.md`.\n")
    assert any("300 lines" in e for e in errors(root))


def test_reference_links_both_ways(tmp_path):
    root = make_pack(tmp_path); skill(root, "openkey-agents", DESC, body="Read `references/missing.md`.\n", refs={"orphan.md": "# O\n"})
    errs = errors(root)
    assert any("missing.md" in e and "does not exist" in e for e in errs)
    assert any("orphan.md" in e and "not linked" in e for e in errs)


def test_no_parent_paths_no_nested_references(tmp_path):
    root = make_pack(tmp_path); skill(root, "openkey-agents", DESC, body="See `../openkey/SKILL.md` and `references/notes.md`.\n")
    assert any("../" in e for e in errors(root))
    root = make_pack(tmp_path / "b"); skill(root, "openkey-agents", DESC, refs={"notes.md": "# N\n", "deep/x.md": "# X\n"})
    assert any("deep/x.md" in e and "only SKILL.md and references" in e for e in errors(root))


def test_reference_may_not_link_another_reference(tmp_path):
    root = make_pack(tmp_path); skill(root, "openkey-agents", DESC, body="Read `references/a.md` and `references/b.md`.\n",
                                       refs={"a.md": "# A\n\nSee `references/b.md`.\n", "b.md": "# B\n"})
    assert any("one level" in e for e in errors(root))


def test_long_reference_needs_table_of_contents(tmp_path):
    long_body = "# Big\n\n" + "\n".join(f"## Section {i}\n\ntext" for i in range(60))
    root = make_pack(tmp_path); skill(root, "openkey-agents", DESC, refs={"notes.md": long_body})
    assert any("table of contents" in e for e in errors(root))
    ok = "# Big\n\n## Contents\n\n- [Section 0](#section-0)\n\n" + "\n".join(f"## Section {i}\n\ntext" for i in range(60))
    root = make_pack(tmp_path / "b"); skill(root, "openkey-agents", DESC, refs={"notes.md": ok})
    assert not any("table of contents" in e for e in errors(root))


# --- forbidden strings, model ids, scaffold -------------------------------------







# --- public-safe -----------------------------------------------------------------

def test_denylist_hits_are_errors_and_word_bounded(tmp_path):
    root = make_pack(tmp_path); skill(root, "openkey-agents", DESC, body="An ad for Acme-Secret-Client. Read `references/notes.md`.\n")
    assert any("denylist" in e and "acme-secret-client" in e.lower() for e in errors(root))
    root = make_pack(tmp_path / "b"); (root / "INSTALL.md").write_text("Jane Realpersonage is not a match.\n")
    assert not any("denylist" in e for e in errors(root))


# --- manifests and integrity -----------------------------------------------------

def test_version_sync(tmp_path):
    root = make_pack(tmp_path); (root / "VERSION").write_text("0.2.0\n")
    assert any("version" in e.lower() for e in errors(root))


def test_readme_and_skill_dirs_match_both_ways(tmp_path):
    root = make_pack(tmp_path); skill(root, "openkey-extra", DESC)
    assert any("openkey-extra" in e and "README" in e for e in errors(root))
    root = make_pack(tmp_path / "b")
    (root / "README.md").write_text((root / "README.md").read_text() + "| [`openkey-ghost`](skills/openkey-ghost/SKILL.md) | x |\n")
    assert any("openkey-ghost" in e for e in errors(root))




def test_relative_links_resolve(tmp_path):
    root = make_pack(tmp_path); (root / "INSTALL.md").write_text("See [x](docs/nope.md).\n")
    assert any("nope.md" in e for e in errors(root))


def test_cli_exit_code(tmp_path, capsys):
    root = make_pack(tmp_path)
    assert lint_pack.main(["--root", str(root)]) == 0
    skill(root, "openkey-agents", DESC, extra_fm="allowed-tools: Read\n")
    assert lint_pack.main(["--root", str(root)]) == 1
    assert "allowed-tools" in capsys.readouterr().out


# --- review follow-ups --------------------------------------------------------------

def test_reference_may_not_link_a_sibling_by_bare_name(tmp_path):
    root = make_pack(tmp_path); skill(root, "openkey-agents", DESC, body="Read `references/a.md` and `references/b.md`.\n",
                                       refs={"a.md": "# A\n\nSee `b.md` and [also](b.md).\n", "b.md": "# B\n"})
    assert any("one level" in e and "b.md" in e for e in errors(root))


def test_missing_denylist_is_an_error_only_when_required(tmp_path):
    root = make_pack(tmp_path); (root / ".denylist").unlink()
    assert any(".denylist" in e for e in errors(root))
    assert not any(".denylist" in f"{p.file}: {p.message}" for p in lint_pack.lint(root, require_denylist=False))


def test_denylist_scans_manifests_tests_and_paths(tmp_path):
    root = make_pack(tmp_path)
    (root / ".codex-plugin" / "plugin.json").write_text(json.dumps({"name": "openkey", "version": "0.1.0", "skills": "./skills/", "interface": {"developerName": "Acme-Secret-Client"}}))
    write(root / "tests" / "fixture-jane-realperson.md", "x")
    errs = errors(root)
    assert any(".codex-plugin/plugin.json" in e and "denylist" in e for e in errs)
    assert any("fixture-jane-realperson.md" in e and "path" in e for e in errs)


def test_denylist_skips_dev_only_paths(tmp_path):
    root = make_pack(tmp_path); write(root / "docs" / "notes.md", "acme-secret-client everywhere"); write(root / "CONTEXT.md", "Jane Realperson")
    assert not any("denylist" in e for e in errors(root))










def test_toc_must_be_near_the_top(tmp_path):
    body = "# Big\n\n" + "\n".join(f"## Section {i}\n\ntext" for i in range(60)) + "\n## Contents\n"
    root = make_pack(tmp_path); skill(root, "openkey-agents", DESC, refs={"notes.md": body})
    assert any("table of contents" in e for e in errors(root))


def test_non_markdown_files_in_a_skill_are_errors(tmp_path):
    root = make_pack(tmp_path); write(root / "skills" / "openkey-agents" / "references" / "data.csv", "a,b"); write(root / "skills" / "openkey-agents" / "scripts" / "x.py", "print(1)")
    errs = errors(root)
    assert any("data.csv" in e for e in errs) and any("x.py" in e for e in errs)


def test_nested_link_does_not_fall_back_to_root(tmp_path):
    root = make_pack(tmp_path); skill(root, "openkey-agents", DESC, refs={"notes.md": "# N\n\nSee [install](INSTALL.md).\n"})
    assert any("INSTALL.md" in e and "does not resolve" in e for e in errors(root))


def test_missing_required_keys_and_prefix_and_semver(tmp_path):
    root = make_pack(tmp_path)
    write(root / "skills" / "openkey-agents" / "SKILL.md", "---\nname: openkey-agents\n---\n\nBody. Read `references/notes.md`.\n")
    errs = errors(root)
    assert any("missing required frontmatter key description" in e for e in errs) and any("missing required frontmatter key license" in e for e in errs)
    root = make_pack(tmp_path / "b"); skill(root, "ads", DESC)
    (root / "README.md").write_text((root / "README.md").read_text() + "| [`ads`](skills/ads/SKILL.md) | x |\n")
    assert any("start with" in e for e in errors(root))
    root = make_pack(tmp_path / "c"); (root / "VERSION").write_text("v1\n")
    assert any("semantic version" in e for e in errors(root))


def test_manifest_skill_lists_are_checked_both_ways(tmp_path):
    root = make_pack(tmp_path)
    (root / ".cursor-plugin" / "plugin.json").write_text(json.dumps({"name": "openkey", "version": "0.1.0", "skills": ["./skills/openkey", "./skills/openkey-ghost"]}))
    errs = errors(root)
    assert any("openkey-ghost" in e and "cursor" in e for e in errs) and any("openkey-agents is not listed" in e for e in errs)


# --- verifier follow-ups ------------------------------------------------------------





def test_dev_only_is_anchored_at_the_root(tmp_path):
    root = make_pack(tmp_path); write(root / "evals" / "docs" / "notes.md", "acme-secret-client"); write(root / "evals" / "CONTEXT.md", "Jane Realperson")
    errs = errors(root)
    assert any("evals/docs/notes.md" in e and "denylist" in e for e in errs) and any("evals/CONTEXT.md" in e for e in errs)


def test_denylist_scans_any_text_suffix_and_strips_inline_comments(tmp_path):
    root = make_pack(tmp_path); write(root / "evals" / "x.ndjson", '{"user": "acme-secret-client"}')
    (root / ".denylist").write_text("acme-secret-client  # the client\n")
    assert any("x.ndjson" in e and "denylist" in e for e in errors(root))


FORBIDDEN_SAMPLES = [
    "https://api.openkey.ai/api/v1", "https://openkey.ai/a/al_abc", "eu-api.openkey.ai", "us-api.openkey.ai",
    "https://eu.openkey.ai", "https://us.openkey.ai", "base_url=\"https://openkey.ai/deepseek\"",
    "npm i @openkey/sdk", "pip install openkey", "https://openkey.ai/go", "sk-ok-t-eu-abc123",
]


def test_forbidden_strings_flagged(tmp_path):
    for i, bad in enumerate(FORBIDDEN_SAMPLES):
        root = make_pack(tmp_path / str(i))
        write(root / "skills/openkey-agents/references/y.md", f"# Y\n\n{bad}\n")
        n = [e for e in errors(root) if "y.md" in e and "forbidden" in e]
        assert len(n) == 1, (bad, n)


def test_forbidden_allows_good_forms(tmp_path):
    root = make_pack(tmp_path)
    write(root / "skills/openkey-agents/references/y.md", "# Y\n\nhttps://openkey.ai/deepseek/v1 and https://api.openkey.ai/v1 and https://openkey.ai/goals\n")
    assert not any("forbidden" in e for e in errors(root))


def test_key_placeholder_allowed(tmp_path):
    root = make_pack(tmp_path)
    write(root / "skills/openkey-agents/references/y.md", "# Y\n\nUse sk-ok-\u2026 or $OPENKEY_API_KEY here.\n")
    assert not any("forbidden" in e for e in errors(root))
    write(root / "skills/openkey-agents/references/y.md", "# Y\n\nsk-ok-t-eu-abc\n")
    assert any("forbidden" in e for e in errors(root))


def test_pasted_key_eval_prompt_is_the_only_exempt_case_file(tmp_path):
    root = make_pack(tmp_path)
    case = root / "evals/cases/openkey-07-no-key-literal"
    write(case / "prompt.md", "Wire OpenKey in. My key is sk-ok-t-eu-AAAA\n")
    write(case / "case.yaml", "note: sk-ok-t-eu-AAAA\n")
    flagged = [e for e in errors(root) if "forbidden" in e]
    assert not any("prompt.md" in e for e in flagged)
    assert any("openkey-07-no-key-literal/case.yaml" in e for e in flagged)


def test_model_id_must_be_listed(tmp_path):
    root = make_pack(tmp_path)
    def put(text): write(root / "skills/openkey-agents/references/y.md", f"# Y\n\n{text}\n")
    put('{"model": "openai/gpt-9"}')
    assert any("openai/gpt-9" in e for e in errors(root))
    for ok in ['{"model": "openai/gpt-5.2"}', 'model="openkey/auto"', "ANTHROPIC_MODEL='openai/gpt-5.2'", "model = \"openkey/auto\""]:
        put(ok)
        assert not any("model id" in e for e in errors(root)), ok
    put("ANTHROPIC_MODEL=\"nope/x\"")
    assert any("nope/x" in e for e in errors(root))


def test_no_mcp_json_required(tmp_path):
    root = make_pack(tmp_path)
    assert not (root / ".mcp.json").exists()
    assert not any("mcp" in e.lower() for e in errors(root))


def test_commands_and_rules_scanned(tmp_path):
    root = make_pack(tmp_path)
    write(root / "commands/x.md", "Use https://eu-api.openkey.ai now\n")
    write(root / "rules/x.mdc", "pip install openkey\n")
    errs = errors(root)
    assert any("commands/x.md" in e and "forbidden" in e for e in errs)
    assert any("rules/x.mdc" in e and "forbidden" in e for e in errs)
    write(root / "commands/x.md", '{"model": "openai/gpt-9"}\n')
    assert any("commands/x.md" in e and "openai/gpt-9" in e for e in errors(root))



def test_superpowers_dir_is_dev_only(tmp_path):
    root = make_pack(tmp_path)
    write(root / ".superpowers" / "x.md", "acme-secret-client and https://eu-api.openkey.ai\n")
    assert errors(root) == []


def test_sync_test_is_dev_only(tmp_path):
    # It names denylisted hosts on purpose to prove they never reach the public tree, and is itself never published.
    root = make_pack(tmp_path)
    write(root / "tests" / "test_sync_public.py", "acme-secret-client\n")
    assert errors(root) == []


# --- final-review gates: command tools, provider-prefixed ids, URL coverage ---------

SCOPED_TOOLS = '[Read, Glob, Grep, Edit, Write, "WebFetch(domain:api.openkey.ai)", "WebFetch(domain:openkey.ai)"]'


def command(root: Path, tools: str):
    write(root / "commands" / "x.md", f"---\ndescription: X\nallowed-tools: {tools}\n---\n\nDo x.\n")


def test_command_may_not_pre_approve_bash_or_unscoped_webfetch(tmp_path):
    for i, bad in enumerate(["[Read, Bash]", '[Read, "Bash(curl *)"]', "[Read, WebFetch]", '["WebFetch(domain:*)"]', "Read Bash"]):
        root = make_pack(tmp_path / str(i)); command(root, bad)
        assert any("commands/x.md" in e and "allowed-tools" in e for e in errors(root)), bad


def test_command_with_scoped_tools_passes(tmp_path):
    root = make_pack(tmp_path); command(root, SCOPED_TOOLS)
    assert errors(root) == []


def _facts(root: Path, **extra):
    facts = json.loads((root / "scripts" / "live_facts.json").read_text())
    facts.update(extra)
    write(root / "scripts" / "live_facts.json", json.dumps(facts))


@pytest.mark.parametrize("line", [
    'export ANTHROPIC_DEFAULT_HAIKU_MODEL="openai/gpt-9"',
    '"ANTHROPIC_DEFAULT_OPUS_MODEL": "openai/gpt-9"',
    'setx ANTHROPIC_DEFAULT_SONNET_MODEL "openai/gpt-9"',
    'Model:    "openai/gpt-9",',
    "    model: openai/gpt-9",
    "Call `openai/gpt-9` for this.",
])
def test_provider_prefixed_id_must_be_listed(tmp_path, line):
    root = make_pack(tmp_path)
    write(root / "skills/openkey-agents/references/y.md", f"# Y\n\n{line}\n")
    assert any("openai/gpt-9" in e and "model id" in e for e in errors(root)), line


def test_provider_prefixed_scan_skips_packages_urls_and_patterns(tmp_path):
    root = make_pack(tmp_path); _facts(root, example_models=["openai/gpt-5.2", "google/gemini-2.5-flash"])
    ok = ("import { GoogleGenAI } from \"@google/genai\";\n"
          "POST /v1beta/models/google/gemini-2.5-flash:generateContent\n"
          "grep '\"id\":\"openai/gpt-9[^\"]*\"'\n"
          "Use `openai/gpt-5.2`. Then `openai/gpt-5.2:nitro`, or google/gemini-2.5-flash.\n")
    write(root / "skills/openkey-agents/references/y.md", "# Y\n\n" + ok)
    assert not any("model id" in e for e in errors(root))
    write(root / "skills/openkey-agents/references/y.md", "# Y\n\nUse google/gemini-9 here.\n")
    assert any("google/gemini-9" in e for e in errors(root))


def _url_pack(tmp_path):
    root = make_pack(tmp_path)
    _facts(root, endpoints=[{"method": "GET", "url": "https://api.openkey.ai/v1/models", "expect": 200},
                            {"method": "POST", "url": "https://api.openkey.ai/v1beta/models/google/gemini-2.5-flash:generateContent", "expect": 401}],
           docs=["https://openkey.ai/docs/errors", "https://openkey.ai/llms-full.txt"])
    return root


def test_cited_openkey_urls_must_be_bases_or_live_facts(tmp_path):
    root = _url_pack(tmp_path)
    good = ("Bases https://openkey.ai, `https://api.openkey.ai` and \"https://api.openkey.ai/v1\".\n"
            "See https://openkey.ai/docs/errors#unauthorized and (https://openkey.ai/llms-full.txt).\n"
            "List: `curl -s https://api.openkey.ai/v1/models | jq`.\n"
            "Templates: https://openkey.ai/docs/<page> and https://api.openkey.ai/v1beta/models/{model}:generateContent.\n")
    write(root / "skills/openkey-agents/references/notes.md", "# Y\n\n" + good)
    write(root / "INSTALL.md", "# Install\n\nCheck https://api.openkey.ai/v1/models.\n")
    assert errors(root) == []
    write(root / "skills/openkey-agents/references/notes.md", "# Y\n\nFetch https://openkey.ai/llms-fulll.txt first.\n")
    assert any("notes.md" in e and "llms-fulll.txt" in e for e in errors(root))
    write(root / "skills/openkey-agents/references/notes.md", "# Y\n\nGET https://api.openkey.ai/v2/{x}/models\n")
    assert any("notes.md" in e and "/v2/" in e for e in errors(root))


def test_url_rule_covers_every_published_file_but_tests(tmp_path):
    root = _url_pack(tmp_path)
    write(root / ".codex-plugin" / "plugin.json", json.dumps({"name": "openkey", "version": "0.1.0", "skills": "./skills/", "interface": {"privacyPolicyURL": "https://openkey.ai/privacy"}}))
    assert any(".codex-plugin/plugin.json" in e and "/privacy" in e for e in errors(root))
    root = _url_pack(tmp_path / "b")
    write(root / "tests" / "test_x.py", "BAD = 'https://openkey.ai/nope'\n")
    write(root / "evals" / "tests" / "test_y.py", "BAD = 'https://openkey.ai/nope'\n")
    assert errors(root) == []
