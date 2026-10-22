#!/usr/bin/env python3
"""Bookkeeping helper for the dev pipeline. Python 3 standard library only.
Run from the project root.

    devtool.py preflight [--no-loop]        git repo + clean tree check; creates .dev/loops/<LOOP_ID>/
    devtool.py devlog [limitations|optimization|log|all] [--count]   print 04-devlog sections
    devtool.py prune-loops [--keep 10]      delete the oldest loop folders
    devtool.py test [--loop LOOP_ID] -- <test command>   run tests; print a condensed result, full log to a file

Output is compact plain text. Errors print one "ERROR: ..." line and exit 1.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import time

DEV = ".dev"
LOOPS = os.path.join(DEV, "loops")
DEVLOG = os.path.join(DEV, "context", "04-devlog.md")
SECTIONS = {"limitations": "Limitations / Improvements", "optimization": "Optimization Targets", "log": "Loop Log"}


def die(msg):
    print("ERROR: " + msg)
    sys.exit(1)


def git(*args):
    r = subprocess.run(["git"] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout


def loop_dirs():
    if not os.path.isdir(LOOPS):
        return []
    return sorted(d for d in os.listdir(LOOPS)
                  if os.path.isdir(os.path.join(LOOPS, d)) and re.fullmatch(r"\d{4}-\d{2}-\d{2}-\d{3}", d))


def cmd_preflight(a):
    code, _ = git("rev-parse", "--is-inside-work-tree")
    if code != 0:
        die("not a git repository. The dev loop needs git.")
    _, status = git("status", "--porcelain")
    changed = [l for l in status.splitlines() if l.strip()]
    if changed:
        print("ERROR: working tree is not clean (%d changes). Commit or stash, then run again." % len(changed))
        for l in changed[:10]:
            print("  " + l)
        sys.exit(1)
    ctx = os.path.join(DEV, "context")
    has_ctx = os.path.isdir(ctx) and any(f.endswith(".md") for f in os.listdir(ctx))
    print("tree: clean")
    print("context: " + ("present" if has_ctx else "missing — A will bootstrap"))
    if a.no_loop:
        return
    today = time.strftime("%Y-%m-%d")
    nums = [int(d[-3:]) for d in loop_dirs() if d.startswith(today)]
    loop_id = "%s-%03d" % (today, max(nums, default=0) + 1)
    os.makedirs(os.path.join(LOOPS, loop_id))
    os.makedirs(ctx, exist_ok=True)
    print("LOOP_ID: " + loop_id)


def sections(text):
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            cur = m.group(1)
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return out


def cmd_devlog(a):
    if not os.path.isfile(DEVLOG):
        die(DEVLOG + " not found.")
    with open(DEVLOG, encoding="utf-8") as f:
        secs = sections(f.read())
    wanted = list(SECTIONS) if a.which == "all" else [a.which]
    for key in wanted:
        name = SECTIONS[key]
        body = secs.get(name)
        if body is None:
            print("## %s — section missing" % name)
            continue
        items = [l for l in body if re.match(r"^\s*([-*]|\d+[.)])\s+\S", l)]
        rows = [l for l in body if l.lstrip().startswith("|")]
        items += rows[2:]  # table rows after the header and separator
        if a.count:
            print("%s: %d" % (name, len(items)))
            continue
        print("## %s (%d)" % (name, len(items)))
        text = "\n".join(l for l in body if not l.startswith("<!--")).strip()
        print(text or "(empty)")
        print()


def cmd_prune(a):
    dirs = loop_dirs()
    drop = dirs[:-a.keep] if len(dirs) > a.keep else []
    for d in drop:
        shutil.rmtree(os.path.join(LOOPS, d))
    print("loops: kept %d, deleted %d%s" % (len(dirs) - len(drop), len(drop), (" (" + ", ".join(drop) + ")") if drop else ""))


FAIL_LINE = re.compile(r"(FAIL|FAILED|ERROR|Error|error:|Exception|Traceback|AssertionError|assert|Expected|Received|expected|actual|✗|✕|panic:)")
SUMMARY_LINE = re.compile(r"(\d+\s+(passed|failed|errors?|skipped|tests?)\b|^Tests?:|^Test Suites:|^(ok|FAIL)\s|Ran \d+ tests?|^OK\b|^FAILED\b)", re.I)


def cmd_test(a):
    cmd = " ".join(a.command).strip()
    if cmd.startswith("-- "):
        cmd = cmd[3:]
    if not cmd:
        die("no test command given. Usage: devtool.py test [--loop ID] -- <test command>")
    log = os.path.join(LOOPS, a.loop, "test.log") if a.loop else os.path.join(LOOPS, "last-test.log")
    os.makedirs(os.path.dirname(log), exist_ok=True)
    t0 = time.time()
    r = subprocess.run(cmd, shell=True, capture_output=True)
    out = (r.stdout + b"\n" + r.stderr).decode("utf-8", "replace")
    with open(log, "w", encoding="utf-8") as f:
        f.write(out)
    lines = out.splitlines()
    print("exit: %d · %.1fs · %d log lines · full log: %s" % (r.returncode, time.time() - t0, len(lines), log))
    summary = [l.strip() for l in lines if SUMMARY_LINE.search(l.strip())]
    print("summary:")
    for l in summary[-8:] or ["(no summary line recognized)"]:
        print("  " + l[:200])
    if r.returncode != 0:
        keep = set()
        for i, l in enumerate(lines):
            if FAIL_LINE.search(l):
                keep.update(range(max(0, i - 1), min(len(lines), i + 3)))
        picked = [lines[i] for i in sorted(keep)][:a.max_lines]
        print("failure lines (first %d):" % len(picked))
        for l in picked:
            print("  " + l[:240])
        print("tail:")
        for l in lines[-10:]:
            print("  " + l[:240])
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("preflight"); s.add_argument("--no-loop", action="store_true")
    s = sub.add_parser("devlog"); s.add_argument("which", nargs="?", default="all", choices=["limitations", "optimization", "log", "all"]); s.add_argument("--count", action="store_true")
    s = sub.add_parser("prune-loops"); s.add_argument("--keep", type=int, default=10)
    s = sub.add_parser("test"); s.add_argument("--loop"); s.add_argument("--max-lines", type=int, default=60); s.add_argument("command", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    {"preflight": cmd_preflight, "devlog": cmd_devlog, "prune-loops": cmd_prune, "test": cmd_test}[a.cmd](a)


if __name__ == "__main__":
    main()
