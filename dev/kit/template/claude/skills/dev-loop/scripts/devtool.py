#!/usr/bin/env python3
"""Bookkeeping helper for the dev pipeline. Python 3 standard library only.
Run from the project root.

    devtool.py preflight [--no-loop]        git repo + clean tree check; creates .dev/loops/<LOOP_ID>/
    devtool.py devlog [limitations|optimization|log|all] [--count]   print 04-devlog sections
    devtool.py prune-loops [--keep 10]      delete the oldest loop folders
    devtool.py test [--loop LOOP_ID] -- <test command>   run tests; print a condensed result, full log to a file
    devtool.py memory [--budget 6000]       size of .dev/context (~tokens per file) and whether to compact it
    devtool.py memory-check [--record]      after compacting: nothing lost vs. HEAD (spec IDs, headings, open items)
    devtool.py auto [--budget 6000] [--min-targets 3]   after a passed loop: run optimization (E) / compaction (F)?

Output is compact plain text. Errors print one "ERROR: ..." line and exit 1.
"""
import argparse
import json
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
CONTEXT = os.path.join(DEV, "context")
ARCHIVE = os.path.join(DEV, "archive")      # moved-out history (old Loop Log rows); agents don't read it
MEMORY = os.path.join(DEV, "memory.json")   # context size after the last compaction
SPEC_ID = re.compile(r"\b[FDU]-\d{2,4}\b")
KEEP_LOG_ROWS = 20


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


def items_in(body):
    """List items and table rows (after header + separator) of one section."""
    items = [l for l in body if re.match(r"^\s*([-*]|\d+[.)])\s+\S", l)]
    rows = [l for l in body if l.lstrip().startswith("|")]
    return items + rows[2:]


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
        items = items_in(body)
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


def tokens(text):
    return len(text) // 4  # rough: ~4 characters per token for English


def context_files():
    if not os.path.isdir(CONTEXT):
        die(CONTEXT + " not found.")
    return sorted(os.path.join(CONTEXT, f) for f in os.listdir(CONTEXT) if f.endswith(".md"))


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def last_compaction():
    try:
        return json.loads(read(MEMORY)).get("tokens")
    except (OSError, ValueError):
        return None


def memory_state(budget):
    files = [(p, tokens(read(p))) for p in context_files()]
    total = sum(t for _, t in files)
    log_rows = len(items_in(sections(read(DEVLOG)).get(SECTIONS["log"], []))) if os.path.isfile(DEVLOG) else 0
    last = last_compaction()
    if log_rows > KEEP_LOG_ROWS:
        why = "yes (Loop Log has %d rows, keep %d)" % (log_rows, KEEP_LOG_ROWS)
    elif total <= budget:
        why = "no (~%d tokens, budget %d)" % (total, budget)
    elif last and total < last * 1.25:
        why = "no (~%d tokens over budget %d, but < 25%% growth since the last compaction at ~%d)" % (total, budget, last)
    else:
        why = "yes (~%d tokens, budget %d%s)" % (total, budget, ", last compaction ~%d" % last if last else "")
    return files, total, log_rows, why


def cmd_memory(a):
    files, total, log_rows, why = memory_state(a.budget)
    for p, t in files:
        print("  %-34s ~%5d tokens" % (os.path.basename(p), t))
    print("total: ~%d tokens · Loop Log rows: %d · last compaction: %s" % (total, log_rows, last_compaction() or "never"))
    print("compact: " + why)


def head_text(path):
    code, out = git("show", "HEAD:" + path.replace(os.sep, "/"))
    return out if code == 0 else None


def cmd_memory_check(a):
    """Compare .dev/context (+ .dev/archive) with HEAD: every spec ID, every heading, every open devlog item survives."""
    problems, before, after = [], 0, 0
    now_ids = set()
    for p in context_files() + ([os.path.join(ARCHIVE, f) for f in os.listdir(ARCHIVE)] if os.path.isdir(ARCHIVE) else []):
        now_ids |= set(SPEC_ID.findall(read(p)))
    for p in context_files():
        old, new = head_text(p), read(p)
        after += tokens(new)
        if old is None:
            continue  # new file
        before += tokens(old)
        name = os.path.basename(p)
        lost = sorted(set(SPEC_ID.findall(old)) - now_ids)
        if lost:
            problems.append("%s: spec IDs gone: %s" % (name, ", ".join(lost)))
        heads = lambda t: [l.strip() for l in t.splitlines() if re.match(r"^#{1,3}\s", l)]
        gone = [h for h in heads(old) if h not in heads(new)]
        if gone:
            problems.append("%s: headings gone: %s" % (name, " | ".join(gone)))
    for p in context_files():
        old = head_text(p)
        if old is None:
            continue
        for key in ("limitations", "optimization"):
            n_old = len(items_in(sections(old).get(SECTIONS[key], [])))
            n_new = len(items_in(sections(read(p)).get(SECTIONS[key], [])))
            if n_new < n_old:
                problems.append("%s: %s has %d items, was %d — open items are never merged or dropped"
                                % (os.path.basename(p), SECTIONS[key], n_new, n_old))
    for d in (CONTEXT, ARCHIVE):
        code, out = git("status", "--porcelain", "--", d)
        for l in out.splitlines():
            if l[:2].strip() == "D":
                problems.append("file deleted: " + l[3:])
    print("tokens: ~%d -> ~%d (%+d%%)" % (before, after, round(100.0 * (after - before) / before) if before else 0))
    if problems:
        print("ERROR: compaction lost information:")
        for x in problems:
            print("  " + x)
        sys.exit(1)
    print("check: ok — all spec IDs, headings and open items kept")
    if a.record:
        with open(MEMORY, "w", encoding="utf-8") as f:
            json.dump({"tokens": after, "date": time.strftime("%Y-%m-%d")}, f)
            f.write("\n")
        print("recorded: " + MEMORY)


def cmd_auto(a):
    """After a passed loop: should the orchestrator run E (optimization) and F (compaction)?"""
    opt = items_in(sections(read(DEVLOG)).get(SECTIONS["optimization"], [])) if os.path.isfile(DEVLOG) else []
    high = [l for l in opt if "[high]" in l.lower()]
    if high:
        print("optimize: yes (%d targets, %d [high])" % (len(opt), len(high)))
    elif len(opt) >= a.min_targets:
        print("optimize: yes (%d targets, threshold %d)" % (len(opt), a.min_targets))
    else:
        print("optimize: no (%d targets, threshold %d, no [high])" % (len(opt), a.min_targets))
    print("compact: " + memory_state(a.budget)[3])


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("preflight"); s.add_argument("--no-loop", action="store_true")
    s = sub.add_parser("devlog"); s.add_argument("which", nargs="?", default="all", choices=["limitations", "optimization", "log", "all"]); s.add_argument("--count", action="store_true")
    s = sub.add_parser("prune-loops"); s.add_argument("--keep", type=int, default=10)
    s = sub.add_parser("test"); s.add_argument("--loop"); s.add_argument("--max-lines", type=int, default=60); s.add_argument("command", nargs=argparse.REMAINDER)
    s = sub.add_parser("memory"); s.add_argument("--budget", type=int, default=6000)
    s = sub.add_parser("memory-check"); s.add_argument("--record", action="store_true")
    s = sub.add_parser("auto"); s.add_argument("--budget", type=int, default=6000); s.add_argument("--min-targets", type=int, default=3)
    a = ap.parse_args()
    {"preflight": cmd_preflight, "devlog": cmd_devlog, "prune-loops": cmd_prune, "test": cmd_test, "memory": cmd_memory,
     "memory-check": cmd_memory_check, "auto": cmd_auto}[a.cmd](a)


if __name__ == "__main__":
    main()
