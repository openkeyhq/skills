#!/usr/bin/env python3
"""Eval runner for the OpenKey skills pack.

Runs `claude -p` per case with only project settings (never the host user's), no
MCP server and a read-mostly allow list, inside a throwaway copy of a fixture
project, then grades the stream-json output and the files the agent left behind.
Tools outside --allowedTools land in permission_denials, so attempts are observable.

Usage:
  python3 evals/runner.py --cases evals/cases [--only skill[,skill]] [--model sonnet]
                          [--case openkey-01,openkey-02] [--max-sweep-usd 3]
                          [--plugin-dir .] [--results evals/results] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# WebFetch is read-only and spends nothing; the skills use it to confirm model ids in the free catalog.
ALLOWED_TOOLS = frozenset({"Read", "Glob", "Grep", "Edit", "Write", "WebFetch"})
CLAUDE_TIMEOUT_S = 600


class UnsafeCase(Exception):
    """A case pre-approves a tool outside ALLOWED_TOOLS, or a checkout or
    project carries settings that could auto-approve one."""


def bare(name: str) -> str:
    """`mcp__server__tool` -> `tool`; built-in names pass through."""
    return name.rsplit("__", 1)[-1].split(":")[-1]


# --- transcript -----------------------------------------------------------------

@dataclass
class Denial:
    name: str
    input: dict


@dataclass
class Transcript:
    tools: list[str] = field(default_factory=list)
    executed: list[str] = field(default_factory=list)
    denials: list[Denial] = field(default_factory=list)
    api_key_source: str = ""
    result: str = ""
    cost: float = 0.0
    session_id: str = ""
    is_error: bool = False
    empty: bool = True


_DENIED_RESULT = ("Permission for this tool use was denied",)


def parse_ndjson(text: str) -> Transcript:
    t = Transcript()
    pending: dict[str, str] = {}
    results: dict[str, dict] = {}
    denied_ids: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        t.empty = False
        kind = ev.get("type")
        if kind == "system" and ev.get("subtype") == "init":
            t.session_id = ev.get("session_id", t.session_id)
            t.api_key_source = str(ev.get("apiKeySource") or "")
        elif kind == "system" and ev.get("subtype") == "permission_denied":
            denied_ids.add(ev.get("tool_use_id", ""))
        elif kind == "assistant":
            for block in (ev.get("message") or {}).get("content") or []:
                if block.get("type") == "tool_use":
                    name = bare(block.get("name", ""))
                    t.tools.append(name)
                    pending[block.get("id", "")] = name
        elif kind == "user":
            for block in (ev.get("message") or {}).get("content") or []:
                if block.get("type") == "tool_result":
                    results[block.get("tool_use_id", "")] = block
        elif kind == "result":
            t.session_id = ev.get("session_id", t.session_id)
            t.result = ev.get("result") or ""
            t.cost = float(ev.get("total_cost_usd") or 0.0)
            t.is_error = bool(ev.get("is_error"))
            for d in ev.get("permission_denials") or []:
                denied_ids.add(d.get("tool_use_id", ""))
                t.denials.append(Denial(bare(d.get("tool_name", "")), d.get("tool_input") or {}))
    # A denied call still gets a tool_result block. "Executed" means: has a
    # result, was never denied, and the result is not the permission system's
    # refusal text.
    for tid, name in pending.items():
        block = results.get(tid)
        if block is None or tid in denied_ids:
            continue
        content = block.get("content")
        text_content = content if isinstance(content, str) else json.dumps(content)
        if any(marker in text_content for marker in _DENIED_RESULT):
            continue
        t.executed.append(name)
    return t


# --- grading ---------------------------------------------------------------------

@dataclass
class Grade:
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


def _subsequence(expected: list[str], actual: list[str]) -> bool:
    it = iter(actual)
    return all(any(x == e for x in it) for e in expected)


def grade(t: Transcript, asserts: dict) -> Grade:
    g = Grade()
    if t.empty:
        g.failures.append("no stream-json output from claude")
        return g

    order = asserts.get("tools_called_in_order")
    if order and not _subsequence(list(order), t.tools):
        g.failures.append(f"tools not called in order {order}; got {t.tools}")
    for name in asserts.get("tools_not_called") or []:
        if name in t.tools:
            g.failures.append(f"tool must not be called: {name}")

    if "denied_tools" in asserts:
        expected = list(asserts["denied_tools"] or [])
        got = [d.name for d in t.denials]
        if expected == []:
            if got:
                g.failures.append(f"no tool may be attempted outside allow, but denied: {got}")
        elif sorted(got) != sorted(expected):
            g.failures.append(f"denied tools expected {expected}, got {got}")

    text = t.result or ""
    if "result_regex" in asserts and not re.search(asserts["result_regex"], text, re.S):
        g.failures.append(f"result did not match /{asserts['result_regex']}/")
    for pat in asserts.get("result_regex_all") or []:
        if not re.search(pat, text, re.S):
            g.failures.append(f"result did not match /{pat}/")
    if "result_not_regex" in asserts and re.search(asserts["result_not_regex"], text, re.S):
        g.failures.append(f"result matched forbidden /{asserts['result_not_regex']}/")
    if t.is_error:
        g.failures.append(f"claude reported is_error: {text[:120]!r}")
    return g


SKIP_DIRS = frozenset({".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", ".next"})


def check_rel_key(rel: str) -> None:
    """A files_* key must be a relative path (or "*") that stays inside the project."""
    parts = Path(rel).parts
    if Path(rel).is_absolute() or ".." in parts:
        raise UnsafeCase(f"file assertion key {rel!r} must be relative with no '..'")


def _inside(project_dir: Path, rel: str) -> Path:
    check_rel_key(rel)
    root = project_dir.resolve()
    f = (root / rel).resolve()
    if not f.is_relative_to(root):
        raise UnsafeCase(f"file assertion key {rel!r} resolves outside the project")
    return f


def _scan_files(project_dir: Path):
    """Every regular file in the project, skipping VCS and dependency dirs."""
    for dirpath, dirs, names in os.walk(project_dir):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for n in sorted(names):
            f = Path(dirpath) / n
            if f.is_file() and not f.is_symlink():
                yield f


def grade_files(project_dir: Path, a: dict) -> list[str]:
    """Grade the fixture project after the run. `files_regex` maps a relative
    path to a pattern it must match; `files_not_regex` maps a path, or "*" for
    every text file outside VCS/dependency dirs, to a pattern that must not
    match. Non-UTF-8 files are skipped by "*". Keys that leave the project
    raise UnsafeCase."""
    out: list[str] = []
    for rel, pat in (a.get("files_regex") or {}).items():
        f = _inside(project_dir, rel)
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            out.append(f"files_regex {rel}: file not found")
            continue
        except UnicodeDecodeError:
            out.append(f"files_regex {rel}: not UTF-8 text")
            continue
        if not re.search(pat, text, re.S):
            out.append(f"files_regex {rel}: /{pat}/ not found")
    root = project_dir.resolve()
    for rel, pat in (a.get("files_not_regex") or {}).items():
        files = list(_scan_files(root)) if rel == "*" else [_inside(project_dir, rel)]
        for f in files:
            try:
                text = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if re.search(pat, text, re.S):
                out.append(f"files_not_regex {f.relative_to(root)}: /{pat}/ found")
    return out


def apply_approved_writes(project_dir: Path, denials: list[Denial], approve: list[str]) -> list[str]:
    """Apply each denied Write to a path in `approve`, as if the user had accepted
    the prompt. Claude Code always asks before writing `.claude/settings.json`, even
    under a pre-approved Write, so `--permission-prompts none` denies it. Writes that
    resolve outside the project are ignored. Returns the paths written, in order."""
    root = project_dir.resolve()
    wanted = set(approve)
    done: list[str] = []
    for d in denials:
        fp, content = d.input.get("file_path"), d.input.get("content")
        if d.name != "Write" or not isinstance(fp, str) or not isinstance(content, str):
            continue
        f = (root / fp).resolve()   # an absolute file_path replaces root
        if not f.is_relative_to(root) or f.relative_to(root).as_posix() not in wanted:
            continue
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
        done.append(f.relative_to(root).as_posix())
    return done


def stage_project(name: str, cases_root: Path, tmp: Path) -> Path:
    """Copy evals/projects/<name> into `tmp`; the copy is the cwd for `claude -p`.
    `cases_root` is evals/cases, so the projects sit next to it."""
    src = Path(cases_root).parent / "projects" / name
    if not src.is_dir():
        raise ValueError(f"no fixture project {name!r}")
    dest = Path(tmp) / name
    shutil.copytree(src, dest)
    return dest


# --- cases -----------------------------------------------------------------------

@dataclass
class Case:
    name: str
    prompt: str
    skill: str
    shape: str
    allow: list[str]
    asserts: dict
    fixture_project: str | None
    model: str | None
    max_turns: int
    max_budget: float
    approve_writes: list[str] = field(default_factory=list)


def load_cases(root: Path, only: str | None, cases: str | None = None) -> list[Case]:
    """`only` filters by skill name; `cases` by case-name prefix (comma-separated). Both narrow."""
    wanted = {s.strip() for s in only.split(",") if s.strip()} if only else None
    prefixes = [s.strip() for s in cases.split(",") if s.strip()] if cases else None
    out: list[Case] = []
    for d in sorted(p for p in Path(root).iterdir() if p.is_dir()):
        spec = d / "case.yaml"
        if not spec.exists():
            continue
        y = yaml.safe_load(spec.read_text()) or {}
        for key in ("files_regex", "files_not_regex"):
            for rel in ((y.get("assert") or {}).get(key) or {}):
                if rel != "*":
                    check_rel_key(rel)
        approve = y.get("approve_denied_writes") or []
        if not isinstance(approve, list) or not all(isinstance(r, str) for r in approve):
            raise UnsafeCase(f"{d.name}: approve_denied_writes must be a list of relative paths")
        for rel in approve:
            check_rel_key(rel)
        allow = [str(a) for a in (y.get("allow") or [])]
        if approve and "Write" not in allow:
            raise UnsafeCase(f"{d.name}: approve_denied_writes needs Write in allow")
        skill = str(y.get("skill", d.name))
        if wanted is not None and skill not in wanted:
            continue
        if prefixes is not None and not any(d.name.startswith(p) for p in prefixes):
            continue
        out.append(Case(
            name=d.name, prompt=(d / "prompt.md").read_text().strip(), skill=skill,
            shape=str(y.get("shape", "routes-right")),
            allow=allow, asserts=y.get("assert") or {},
            fixture_project=y.get("fixture_project"), model=y.get("model"),
            max_turns=int(y.get("max_turns", 10)), max_budget=float(y.get("max_budget_usd", 0.6)),
            approve_writes=list(approve),
        ))
    return out


def settings_json(env: dict | None = None) -> str:
    """The --settings payload: the API key helper when an API key is set
    (non-bare -p on a fresh machine does not read ANTHROPIC_API_KEY on its
    own; without a key the maintainer's claude.ai login carries the run)."""
    env = os.environ if env is None else env
    return json.dumps({"apiKeyHelper": "printenv ANTHROPIC_API_KEY"} if env.get("ANTHROPIC_API_KEY") else {})


def build_command(*, prompt: str, allow: list[str], plugin_dir: str | None, model: str,
                  max_turns: int, max_budget: float, settings_json: str | None) -> list[str]:
    for name in allow:
        if name not in ALLOWED_TOOLS:
            raise UnsafeCase(f"{name} may not be pre-approved; allowed: {sorted(ALLOWED_TOOLS)}")
    cmd = ["claude", "--setting-sources", "project", "-p", prompt, "--output-format", "stream-json",
           "--verbose", "--permission-mode", "default", "--permission-prompts", "none",
           "--strict-mcp-config", "--mcp-config", json.dumps({"mcpServers": {}}),
           "--model", model, "--max-turns", str(max_turns), "--max-budget-usd", str(max_budget)]
    if plugin_dir:
        cmd += ["--plugin-dir", plugin_dir]
    # Read is always allowed: skills tell the agent to read their own references/ files,
    # and a denied Read would fail every case on the harness rather than on the skill.
    cmd += ["--allowedTools", ",".join(dict.fromkeys(["Read", *allow]))]
    if settings_json:
        cmd += ["--settings", settings_json]
    return cmd


def over_budget(*, spent: float, cap: float) -> bool:
    return spent > cap


def refuse_permissive_checkout(cwd: Path) -> None:
    """`--setting-sources project` reads the working directory's .claude/settings*.json.
    Anything there that could pre-approve a tool (permissions.allow, a
    defaultMode other than the default, hooks, or a file that cannot be read)
    is refused; deny-only settings are fine, they can only narrow."""
    for name in ("settings.json", "settings.local.json"):
        p = cwd / ".claude" / name
        if not p.exists():
            continue
        try:
            s = json.loads(p.read_text())
        except json.JSONDecodeError:
            raise UnsafeCase(f"{p} is not valid JSON; evals refuse to run with it")
        perms = s.get("permissions") or {}
        risky = {k: v for k, v in (("permissions.allow", perms.get("allow")), ("permissions.defaultMode", perms.get("defaultMode")), ("hooks", s.get("hooks"))) if v}
        if risky:
            raise UnsafeCase(f"{p} carries {sorted(risky)}; evals refuse to run with it")


def claude_logged_in() -> bool:
    """True when the claude CLI has a claude.ai login of its own."""
    try:
        p = subprocess.run(["claude", "auth", "status", "--json"], capture_output=True, text=True, timeout=30)
        return p.returncode == 0 and bool(json.loads(p.stdout).get("loggedIn"))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


def require_credentials(env: dict, logged_in: bool | None = None) -> None:
    """Fail before the first claude call when a live sweep cannot succeed,
    rather than spending on cases that all fail on sign-in: an API key, or the
    claude CLI's own login."""
    if not env.get("ANTHROPIC_API_KEY"):
        if not (claude_logged_in() if logged_in is None else logged_in):
            raise UnsafeCase("set ANTHROPIC_API_KEY, or sign the claude CLI in (claude auth login)")


@dataclass
class RunOutcome:
    grade: Grade
    transcript: Transcript
    stderr_tail: str = ""
    approved_writes: list[str] = field(default_factory=list)


def _run_claude(cmd: list[str], cwd: Path) -> tuple[str, str, int]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=CLAUDE_TIMEOUT_S, cwd=cwd)
    except subprocess.TimeoutExpired as e:
        return (e.stdout or "") if isinstance(e.stdout, str) else "", f"timed out after {CLAUDE_TIMEOUT_S}s", 124
    except FileNotFoundError:
        return "", "claude binary not found on PATH", 127
    return p.stdout, p.stderr, p.returncode


def run_case(c: Case, args, cases_root: Path) -> RunOutcome:
    cmd = build_command(prompt=c.prompt, allow=c.allow, plugin_dir=args.plugin_dir,
                        model=c.model or args.model, max_turns=c.max_turns, max_budget=c.max_budget,
                        settings_json=settings_json())
    if args.dry_run:
        print(" ".join(json.dumps(x) if (" " in x or x.startswith("{")) else x for x in cmd))
        return RunOutcome(Grade(), Transcript())
    with tempfile.TemporaryDirectory(prefix="openkey-evals-") as tmp:
        cwd = stage_project(c.fixture_project, cases_root, Path(tmp)) if c.fixture_project else Path(tmp)
        refuse_permissive_checkout(cwd)
        out, err, code = _run_claude(cmd, cwd)
        t = parse_ndjson(out)
        if t.empty or code != 0:
            return RunOutcome(Grade([f"claude exited {code}: {err.strip()[-300:]}"]), t, err[-2000:])
        if t.api_key_source in ("", "none") and (t.is_error or not (t.result or "").strip()):
            # A claude.ai login also reports apiKeySource "none" but answers; only an empty or errored run means no credential.
            return RunOutcome(Grade(["claude has no credential (apiKeySource none and no answer); set ANTHROPIC_API_KEY or sign the CLI in"]), t, err[-2000:])
        approved = apply_approved_writes(cwd, t.denials, c.approve_writes)
        g = grade(t, c.asserts)
        g.failures += grade_files(cwd, c.asserts)
        return RunOutcome(g, t, err[-2000:], approved)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="evals/cases")
    ap.add_argument("--only", help="comma-separated skill names")
    ap.add_argument("--case", help="comma-separated case-name prefixes, e.g. openkey-01,openkey-02")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--max-sweep-usd", type=float, default=3.0)
    ap.add_argument("--plugin-dir", default=".")
    ap.add_argument("--results", default="evals/results")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    cases_root = Path(args.cases)
    cases = load_cases(cases_root, args.only, args.case)
    if not cases:
        print(f"::error::no eval cases match --only {args.only!r}; refusing to report a green run", file=sys.stderr)
        return 2

    if not args.dry_run:
        refuse_permissive_checkout(Path.cwd())
        require_credentials(dict(os.environ))
    # claude runs inside the fixture project, so the plugin path must not depend on the cwd.
    if args.plugin_dir:
        args.plugin_dir = str(Path(args.plugin_dir).resolve())

    results_dir = Path(args.results)
    if not args.dry_run:
        results_dir.mkdir(parents=True, exist_ok=True)
    spent = 0.0
    failed: list[str] = []
    rows: list[str] = []
    for c in cases:
        if over_budget(spent=spent, cap=args.max_sweep_usd):
            failed.append(f"{c.name}: skipped, sweep over budget (${spent:.2f} > ${args.max_sweep_usd:.2f})")
            rows.append(f"| {c.name} | {c.skill} | {c.shape} | SKIPPED (budget) | | |")
            continue
        outcome = run_case(c, args, cases_root)
        if args.dry_run:
            continue
        t, g = outcome.transcript, outcome.grade
        spent += t.cost
        status = "PASS" if g.ok else "FAIL"
        rows.append(f"| {c.name} | {c.skill} | {c.shape} | {status} | ${t.cost:.2f} | {'; '.join(g.failures)} |")
        (results_dir / f"{c.name}.json").write_text(json.dumps({
            "case": c.name, "skill": c.skill, "shape": c.shape, "status": status, "failures": g.failures,
            "cost_usd": t.cost, "tools": t.tools, "executed": t.executed,
            "denials": [{"name": d.name, "input": d.input} for d in t.denials],
            "approved_writes": outcome.approved_writes,
            "result": t.result, "stderr_tail": outcome.stderr_tail,
        }, indent=2))
        if not g.ok:
            failed.append(f"{c.name}: {'; '.join(g.failures)}")
    if args.dry_run:
        return 0
    summary = ["| case | skill | shape | status | cost | failures |", "|---|---|---|---|---|---|", *rows,
               "", f"Total: {len(cases)} cases, {len(cases) - len(failed)} passed, ${spent:.2f} spent."]
    (results_dir / "summary.md").write_text("\n".join(summary) + "\n")
    print("\n".join(summary))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
