"""Unit tests for the eval runner: grading over recorded stream-json, command
building, fixture projects and file grading. No live claude runs."""
import json
import re
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import runner  # noqa: E402

FIX = HERE / "fixtures"
CASES = HERE.parent / "cases"


def load(name):
    return runner.parse_ndjson((FIX / name).read_text())


def grade(fixture, asserts):
    return runner.grade(load(fixture), asserts)


def build(**kw):
    base = dict(prompt="hi", allow=[], plugin_dir=".", model="sonnet", max_turns=5, max_budget=0.5, settings_json=None)
    return runner.build_command(**{**base, **kw})


# --- parsing -----------------------------------------------------------------

def test_parse_collects_tools_in_order():
    t = load("edit_ok.ndjson")
    assert t.tools == ["Read", "Edit"]
    assert t.executed == ["Read", "Edit"]
    assert t.cost == 0.31
    assert t.session_id == "sess-1"


def test_bare_name_is_suffix_after_last_double_underscore():
    assert runner.bare("mcp__server__list_things") == "list_things"
    assert runner.bare("Edit") == "Edit"


def test_denials_are_recorded_and_are_not_executions():
    t = load("bash_denied.ndjson")
    assert [d.name for d in t.denials] == ["Bash"]
    assert t.denials[0].input["command"] == "curl https://example.com"
    assert t.executed == []


def test_no_api_key_source_is_reported_not_graded():
    t = runner.parse_ndjson(json.dumps({"type": "system", "subtype": "init", "session_id": "s", "apiKeySource": "none"}) + "\n" +
                            json.dumps({"type": "result", "result": "Not logged in", "total_cost_usd": 0, "is_error": True, "permission_denials": []}))
    assert t.api_key_source == "none"


# --- grading -----------------------------------------------------------------

def test_tools_called_in_order_passes_on_subsequence():
    assert grade("edit_ok.ndjson", {"tools_called_in_order": ["Read", "Edit"]}).ok


def test_tools_called_in_order_fails_on_wrong_order():
    r = grade("edit_ok.ndjson", {"tools_called_in_order": ["Edit", "Read"]})
    assert not r.ok and any("order" in f for f in r.failures)


def test_tools_not_called():
    assert grade("edit_ok.ndjson", {"tools_not_called": ["Bash"]}).ok
    assert not grade("edit_ok.ndjson", {"tools_not_called": ["Edit"]}).ok


def test_denied_tools():
    assert not grade("bash_denied.ndjson", {"denied_tools": []}).ok
    assert grade("bash_denied.ndjson", {"denied_tools": ["Bash"]}).ok
    assert grade("edit_ok.ndjson", {"denied_tools": []}).ok


def test_result_regexes():
    assert grade("edit_ok.ndjson", {"result_regex": r"api\.openkey\.ai/v1"}).ok
    assert not grade("edit_ok.ndjson", {"result_regex": r"nothing here"}).ok
    assert grade("edit_ok.ndjson", {"result_regex_all": [r"app\.py", r"OPENKEY_API_KEY"]}).ok
    assert not grade("edit_ok.ndjson", {"result_not_regex": r"app\.py"}).ok


def test_empty_output_fails():
    r = runner.grade(runner.parse_ndjson(""), {})
    assert not r.ok and "no stream-json output" in r.failures[0]


# --- command building ----------------------------------------------------------

def test_command_shape():
    cmd = build(plugin_dir="/p")
    assert cmd[cmd.index("--setting-sources") + 1] == "project" and "--bare" not in cmd
    assert cmd[cmd.index("--permission-mode") + 1] == "default" and cmd[cmd.index("--permission-prompts") + 1] == "none"
    assert cmd[cmd.index("--plugin-dir") + 1] == "/p"
    assert json.loads(cmd[cmd.index("--mcp-config") + 1]) == {"mcpServers": {}}
    assert "--strict-mcp-config" in cmd and "stream-json" in cmd


def test_read_is_always_pre_approved_and_allow_adds_editing_tools():
    cmd = build()
    assert cmd[cmd.index("--allowedTools") + 1] == "Read"
    cmd = build(allow=["Read", "Glob", "Grep", "Edit", "Write"])
    assert cmd[cmd.index("--allowedTools") + 1] == "Read,Glob,Grep,Edit,Write"


@pytest.mark.parametrize("tool", ["Bash", "WebSearch", "mcp__x__y"])
def test_tool_outside_the_allowed_set_is_refused(tool):
    with pytest.raises(runner.UnsafeCase):
        build(allow=[tool])


def test_webfetch_may_be_pre_approved():
    cmd = build(allow=["Glob", "WebFetch"])
    assert cmd[cmd.index("--allowedTools") + 1] == "Read,Glob,WebFetch"


def test_api_key_helper_only_when_a_key_is_set():
    assert json.loads(runner.settings_json({"ANTHROPIC_API_KEY": "k"}))["apiKeyHelper"] == "printenv ANTHROPIC_API_KEY"
    assert json.loads(runner.settings_json({})) == {}


# --- fixture projects ------------------------------------------------------------

def test_stage_project_copies_tree(tmp_path):
    d = runner.stage_project("py-openai", CASES, tmp_path)
    assert (d / "app.py").exists() and d.parent == tmp_path
    assert (CASES.parent / "projects" / "py-openai" / "app.py").exists()   # the source is untouched


def test_unknown_fixture_project_errors(tmp_path):
    with pytest.raises(ValueError, match="no fixture project 'nope'"):
        runner.stage_project("nope", CASES, tmp_path)


def test_files_regex_pass_and_fail(tmp_path):
    (tmp_path / "app.py").write_text("base_url='https://api.openkey.ai/v1'")
    assert runner.grade_files(tmp_path, {"files_regex": {"app.py": r"api\.openkey\.ai/v1"}}) == []
    assert runner.grade_files(tmp_path, {"files_regex": {"app.py": r"nowhere"}}) == ["files_regex app.py: /nowhere/ not found"]
    assert runner.grade_files(tmp_path, {"files_regex": {"gone.py": "x"}}) == ["files_regex gone.py: file not found"]


def test_files_not_regex_star(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "a.py").write_text("clean")
    (tmp_path / "src" / "x.py").write_text("key = '" + "sk-ok-" + "t-eu-A'")   # split so the pack lint does not see a literal key
    assert runner.grade_files(tmp_path, {"files_not_regex": {"*": r"sk-ok-[a-z]"}}) == ["files_not_regex src/x.py: /sk-ok-[a-z]/ found"]
    assert runner.grade_files(tmp_path, {"files_not_regex": {"a.py": "sk-ok-"}}) == []
    assert runner.grade_files(tmp_path, {}) == []


def test_file_assertion_keys_cannot_leave_the_project(tmp_path):
    proj = tmp_path / "proj"; proj.mkdir()
    (tmp_path / "secret.txt").write_text("outside")
    for key in ("../secret.txt", str(tmp_path / "secret.txt"), "sub/../../secret.txt"):
        for kind in ("files_regex", "files_not_regex"):
            with pytest.raises(runner.UnsafeCase):
                runner.grade_files(proj, {kind: {key: "outside"}})


def test_symlink_escaping_the_project_is_refused(tmp_path):
    proj = tmp_path / "proj"; proj.mkdir()
    (tmp_path / "secret.txt").write_text("outside")
    (proj / "link.txt").symlink_to(tmp_path / "secret.txt")
    with pytest.raises(runner.UnsafeCase):
        runner.grade_files(proj, {"files_regex": {"link.txt": "outside"}})


def test_case_load_rejects_escaping_keys(tmp_path):
    d = tmp_path / "x-01"; d.mkdir(); (d / "prompt.md").write_text("x")
    (d / "case.yaml").write_text("assert:\n  files_not_regex:\n    ../app.py: y\n")
    with pytest.raises(runner.UnsafeCase):
        runner.load_cases(tmp_path, only=None)


def test_star_scan_skips_vcs_and_dependency_dirs_and_binaries(tmp_path):
    for d in (".git", "node_modules", "__pycache__"):
        (tmp_path / d).mkdir(); (tmp_path / d / "x.js").write_text("LEAK")
    (tmp_path / "blob.bin").write_bytes(b"\xff\xfeLEAK\x80")
    (tmp_path / "src").mkdir(); (tmp_path / "src" / "a.py").write_text("LEAK")
    assert runner.grade_files(tmp_path, {"files_not_regex": {"*": "LEAK"}}) == ["files_not_regex src/a.py: /LEAK/ found"]


# --- denied writes the case approves -------------------------------------------------

def _write(path, content="{}"):
    return runner.Denial("Write", {"file_path": str(path), "content": content})


def test_denied_write_to_an_approved_path_is_applied(tmp_path):
    denials = [_write(tmp_path / ".claude" / "settings.json", '{"a": 1}'),
               _write(tmp_path / "other.txt", "x"),
               runner.Denial("Bash", {"command": "echo x > .claude/settings.json"}),
               _write(".claude/settings.json", '{"a": 2}')]   # relative to the project; the last write wins
    done = runner.apply_approved_writes(tmp_path, denials, [".claude/settings.json"])
    assert done == [".claude/settings.json", ".claude/settings.json"]
    assert (tmp_path / ".claude" / "settings.json").read_text() == '{"a": 2}'
    assert not (tmp_path / "other.txt").exists()


def test_denied_write_outside_the_project_is_never_applied(tmp_path):
    proj = tmp_path / "proj"; proj.mkdir()
    outside = tmp_path / ".claude" / "settings.json"
    assert runner.apply_approved_writes(proj, [_write(outside), _write("../.claude/settings.json")], [".claude/settings.json"]) == []
    assert not outside.exists()


def test_approved_write_through_a_symlink_out_of_the_project_is_not_applied(tmp_path):
    proj = tmp_path / "proj"; proj.mkdir()
    outside = tmp_path / "elsewhere"; outside.mkdir()
    (proj / ".claude").symlink_to(outside)
    assert runner.apply_approved_writes(proj, [_write(proj / ".claude" / "settings.json")], [".claude/settings.json"]) == []
    assert not (outside / "settings.json").exists()


def test_without_approved_paths_nothing_is_applied(tmp_path):
    assert runner.apply_approved_writes(tmp_path, [_write(tmp_path / ".claude" / "settings.json")], []) == []
    assert not (tmp_path / ".claude").exists()


def test_case_load_validates_approved_write_paths(tmp_path):
    d = tmp_path / "x-01"; d.mkdir(); (d / "prompt.md").write_text("x")
    (d / "case.yaml").write_text("allow: [Write]\napprove_denied_writes: [.claude/settings.json]\n")
    assert runner.load_cases(tmp_path, only=None)[0].approve_writes == [".claude/settings.json"]
    for bad in ("[../x]", "[/etc/x]", ".claude/settings.json"):
        (d / "case.yaml").write_text(f"allow: [Write]\napprove_denied_writes: {bad}\n")
        with pytest.raises(runner.UnsafeCase):
            runner.load_cases(tmp_path, only=None)


def test_approved_writes_need_write_in_allow(tmp_path):
    d = tmp_path / "x-01"; d.mkdir(); (d / "prompt.md").write_text("x")
    for allow in ("", "allow: [Read, Edit]\n"):
        (d / "case.yaml").write_text(allow + "approve_denied_writes: [.claude/settings.json]\n")
        with pytest.raises(runner.UnsafeCase, match="needs Write in allow"):
            runner.load_cases(tmp_path, only=None)


# --- cases, budget, guards ----------------------------------------------------------

def test_case_loading_and_sweep_budget(tmp_path):
    c = tmp_path / "cases" / "x-01"
    c.mkdir(parents=True)
    (c / "prompt.md").write_text("Switch it.\n")
    (c / "case.yaml").write_text("skill: x\nfixture_project: py-openai\nallow: [Edit]\nassert:\n  files_regex: {app.py: y}\n")
    cases = runner.load_cases(tmp_path / "cases", only=None)
    assert [k.name for k in cases] == ["x-01"] and cases[0].prompt == "Switch it."
    assert cases[0].fixture_project == "py-openai" and cases[0].allow == ["Edit"]
    assert runner.load_cases(tmp_path / "cases", only="y") == []
    assert runner.over_budget(spent=3.1, cap=3.0) and not runner.over_budget(spent=2.9, cap=3.0)


def test_only_accepts_a_comma_separated_list(tmp_path):
    for name, skill in [("a-01", "a"), ("b-01", "b"), ("c-01", "c")]:
        d = tmp_path / name; d.mkdir(); (d / "prompt.md").write_text("x"); (d / "case.yaml").write_text(f"skill: {skill}\n")
    assert [c.skill for c in runner.load_cases(tmp_path, only="a,c")] == ["a", "c"]


def test_case_prefix_filter_narrows_within_a_skill():
    names = [c.name for c in runner.load_cases(CASES, only=None, cases="openkey-01")]
    assert names and all(n.startswith("openkey-01") for n in names)
    assert runner.load_cases(CASES, only="nope", cases="openkey-01") == []


def test_permissive_checkout_is_refused(tmp_path):
    (tmp_path / ".claude").mkdir()
    for body in ({"permissions": {"allow": ["Bash"]}}, {"permissions": {"defaultMode": "acceptEdits"}}, {"hooks": {"PreToolUse": []}}):
        (tmp_path / ".claude" / "settings.json").write_text(json.dumps(body))
        with pytest.raises(runner.UnsafeCase):
            runner.refuse_permissive_checkout(tmp_path)
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps({"permissions": {"deny": ["Bash"]}}))
    runner.refuse_permissive_checkout(tmp_path)  # deny-only narrows, so it is fine
    (tmp_path / ".claude" / "settings.json").write_text("{not json")
    with pytest.raises(runner.UnsafeCase):
        runner.refuse_permissive_checkout(tmp_path)


def test_live_sweep_requires_credentials():
    with pytest.raises(runner.UnsafeCase):
        runner.require_credentials({}, logged_in=False)
    runner.require_credentials({"ANTHROPIC_API_KEY": "k"}, logged_in=False)
    runner.require_credentials({}, logged_in=True)


def test_zero_matching_cases_is_an_error(tmp_path, capsys):
    (tmp_path / "cases").mkdir()
    assert runner.main(["--cases", str(tmp_path / "cases"), "--only", "nope", "--dry-run"]) == 2
    assert "::error::" in capsys.readouterr().err


def test_dry_run_prints_the_command_and_writes_nothing(tmp_path, capsys):
    res = tmp_path / "res"
    assert runner.main(["--cases", str(CASES), "--dry-run", "--results", str(res)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("claude --setting-sources project -p ") and "--plugin-dir" in out
    assert not res.exists()


# --- every real case must load ------------------------------------------------------

def test_every_real_case_is_well_formed():
    cases = runner.load_cases(CASES, only=None)
    assert cases
    for c in cases:
        assert c.prompt and c.skill, c.name
        assert set(c.allow) <= runner.ALLOWED_TOOLS, c.name
        if c.fixture_project:
            assert (CASES.parent / "projects" / c.fixture_project).is_dir(), c.name
        a = c.asserts
        for pat in [a.get("result_regex"), a.get("result_not_regex"), *(a.get("result_regex_all") or []),
                    *(a.get("files_regex") or {}).values(), *(a.get("files_not_regex") or {}).values()]:
            if pat:
                re.compile(pat)
        if a.get("files_regex") or a.get("files_not_regex"):
            assert c.fixture_project and {"Edit", "Write"} & set(c.allow), f"{c.name}: file asserts need a project and a write tool"
        if c.approve_writes:
            assert c.fixture_project and "Write" in c.allow, f"{c.name}: approved writes need a project and Write"


class _StrictLoader(yaml.SafeLoader):
    pass


def _no_duplicate_keys(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        assert key not in seen, f"duplicate key {key!r}"
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys)


def test_no_case_yaml_carries_a_duplicate_key():
    # yaml.safe_load keeps the last value silently, which turns an assertion into dead text.
    for f in sorted(CASES.glob("*/case.yaml")):
        yaml.load(f.read_text(), Loader=_StrictLoader)
