#!/usr/bin/env python3
"""Paper animations with Manim, run from a pipeline-owned environment. Python 3 standard library only.

    animtool.py check                      is Manim usable? where, which version, LaTeX or not
    animtool.py setup                      create the shared Manim environment (once per machine, ~0.5 GB)
    animtool.py render <scene.py> [--scene NAME] [--final] [--cols 4]
        draft (default): 480p, then steps.png — the last frame of every play(), one image for review
        --final: 1080p30 MP4 + GIF next to scene.py

Manim never goes into the user's own Python. It lives in one environment per user:
    Linux / macOS  ~/.cache/research-pipeline/manim/     Windows  %LOCALAPPDATA%\\research-pipeline\\manim\\
MANIM_PYTHON=<python with manim> overrides it. Errors print one "ERROR: ..." line and exit 1.
"""
import argparse
import io
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MANIM_SPEC = ["python=3.11", "manim=0.19"]


def die(msg):
    print("ERROR: " + msg)
    sys.exit(1)


def home():
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "research-pipeline", "manim")


ENV = os.path.join(home(), "env")


def env_python(env):
    """conda layout (env/python.exe on Windows, env/bin/python) or venv layout (env/Scripts/python.exe)."""
    cands = [os.path.join(env, "python.exe"), os.path.join(env, "Scripts", "python.exe")] if os.name == "nt" \
        else [os.path.join(env, "bin", "python")]
    return next((c for c in cands if os.path.isfile(c)), cands[0])


def env_paths(env):
    """Folders to put on PATH so the env's DLLs / tools (dvisvgm, ffmpeg) are found."""
    if os.name == "nt":
        return [env, os.path.join(env, "Library", "bin"), os.path.join(env, "Scripts")]
    return [os.path.join(env, "bin")]


def manim_version(py):
    try:
        r = subprocess.run([py, "-c", "import manim; print(manim.__version__)"], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def find_python():
    """(python, env folder or None, version) of the first interpreter with Manim."""
    cands = []
    if os.environ.get("MANIM_PYTHON"):
        cands.append((os.environ["MANIM_PYTHON"], None))
    if os.path.isfile(env_python(ENV)):
        cands.append((env_python(ENV), ENV))
    cands.append((sys.executable, None))
    for py, env in cands:
        v = manim_version(py)
        if v:
            return py, env, v
    return None, None, None


def run_env(py, env):
    e = dict(os.environ)
    extra = env_paths(env) if env else [os.path.dirname(py)]
    e["PATH"] = os.pathsep.join(extra + [e.get("PATH", "")])
    e["PYTHONPATH"] = os.pathsep.join([HERE] + ([e["PYTHONPATH"]] if e.get("PYTHONPATH") else []))
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONDONTWRITEBYTECODE"] = "1"  # no __pycache__ next to scene.py
    return e


def latex_status(py, env):
    probe = "import shutil; print(bool(shutil.which('latex')), bool(shutil.which('dvisvgm')))"
    r = subprocess.run([py, "-c", probe], capture_output=True, text=True, env=run_env(py, env))
    latex, dvisvgm = (r.stdout.split() + ["False", "False"])[:2]
    if latex == "True" and dvisvgm == "True":
        return "LaTeX: yes — formula() uses MathTex"
    return "LaTeX: no — formula() falls back to matplotlib / plain text (fine for most formulas)"


# ------------------------------------------------------------------ setup

def mamba_platform():
    m = platform.machine().lower()
    arm = m in ("arm64", "aarch64")
    if sys.platform == "darwin":
        return "osx-arm64" if arm else "osx-64"
    if os.name == "nt":
        return "win-64"
    return "linux-aarch64" if arm else "linux-64"


def get_micromamba():
    """A conda-compatible installer. micromamba first — on PATH, cached, or downloaded (~10 MB, self-contained, no
    shared package cache to fight over); an existing mamba / conda only when the download fails."""
    if shutil.which("micromamba"):
        return shutil.which("micromamba"), "micromamba"
    name = "micromamba.exe" if os.name == "nt" else "micromamba"
    local = os.path.join(home(), "bin", name)
    if os.path.isfile(local):
        return local, "micromamba"
    exe, kind = download_micromamba(local)
    if exe:
        return exe, kind
    for other in ("mamba", "conda"):
        if shutil.which(other):
            return shutil.which(other), other
    return None, kind


def download_micromamba(local):
    url = "https://micro.mamba.pm/api/micromamba/%s/latest" % mamba_platform()
    print("downloading micromamba (%s) ..." % mamba_platform(), flush=True)
    try:
        data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "research-pipeline"}), timeout=120).read()
    except OSError as e:
        return None, "micromamba download failed: %s" % e
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:bz2") as t:
        member = next((m for m in t.getmembers() if m.name.endswith(("bin/micromamba", "bin/micromamba.exe"))), None)
        if member is None:
            return None, "micromamba archive had no binary"
        os.makedirs(os.path.dirname(local), exist_ok=True)
        with open(local, "wb") as f:
            f.write(t.extractfile(member).read())
    os.chmod(local, 0o755)
    return local, "micromamba"


def cmd_setup(a):
    py, env, v = find_python()
    if py and not a.force:
        print("manim: %s already usable · %s" % (v, py))
        return
    os.makedirs(home(), exist_ok=True)
    log = os.path.join(home(), "setup.log")
    exe, kind = get_micromamba()
    if exe:
        # conda-forge brings cairo, pango and ffmpeg along on every OS — no compiler, no sudo
        if kind == "micromamba":
            cmd = [exe, "create", "-y", "-p", ENV, "-r", os.path.join(home(), "root"), "-c", "conda-forge"] + MANIM_SPEC
        else:
            cmd = [exe, "create", "-y", "-p", ENV, "-c", "conda-forge", "--override-channels"] + MANIM_SPEC
        e = dict(os.environ)
        # a shared conda's package cache is often read-only: keep packages in our own folder
        rc = os.path.join(home(), "condarc")
        with open(rc, "w", encoding="utf-8") as f:
            f.write("pkgs_dirs:\n  - %s\n" % os.path.join(home(), "pkgs").replace("\\", "/"))
        e["CONDARC"], e["CONDA_PKGS_DIRS"] = rc, os.path.join(home(), "pkgs")
        how = "conda-forge via " + kind
    else:
        # last resort: venv + pip — wheels exist for Windows and macOS; Linux needs the cairo / pango dev packages
        import venv
        venv.create(ENV, with_pip=True)
        cmd = [env_python(ENV), "-m", "pip", "install", "manim"]
        e, how = dict(os.environ), "pip (no conda installer: %s)" % kind
    print("installing Manim into %s with %s — a few minutes, ~0.5 GB ..." % (ENV, how), flush=True)
    with open(log, "w", encoding="utf-8") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=e)
    py, env, v = find_python()
    if r.returncode != 0 or not py:
        tail = open(log, encoding="utf-8", errors="replace").read().splitlines()[-6:]
        hint = ""
        if not exe and sys.platform.startswith("linux"):
            hint = " On Linux pip needs: sudo apt install libcairo2-dev libpango1.0-dev pkg-config (or install conda)."
        die("Manim setup failed (%s). Log: %s · last lines: %s.%s" % (how, log, " | ".join(tail), hint))
    print("manim: %s ready · %s" % (v, py))
    print(latex_status(py, env))


def cmd_check(a):
    py, env, v = find_python()
    if not py:
        print("manim: not installed — run `animtool.py setup` (one time, ~0.5 GB, nothing touches your own Python)")
        return
    print("manim: %s · %s" % (v, py))
    print(latex_status(py, env))


# ------------------------------------------------------------------ render

SHEET = r'''
import sys, av
from PIL import Image, ImageDraw
lst, sheet, cols, video, gif = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
paths = [l.strip()[6:-1].replace("file:", "", 1) for l in open(lst, encoding="utf-8") if l.startswith("file ")]
def last_frame(p):
    img = None
    with av.open(p) as c:
        for fr in c.decode(video=0):
            img = fr
    return img.to_image() if img else None
from PIL import ImageChops
def same(a, b):  # video compression leaves noise, so compare small grayscale versions with a tolerance
    h = ImageChops.difference(a.convert("L").resize((96, 54)), b.convert("L").resize((96, 54))).histogram()
    return sum(i * n for i, n in enumerate(h)) / (96 * 54) < 1.0 and not any(h[40:])
tiles, prev = [], None
for p in paths:  # one tile per play(); a step that leaves the frame unchanged (a wait) adds nothing to review
    t = last_frame(p)
    if t and (prev is None or not same(t, prev)):
        tiles.append(t)
    prev = t or prev
if tiles:
    cols = min(cols, len(tiles))  # no empty columns to pay for
    w = 400; h = int(tiles[0].height * w / tiles[0].width)
    rows = (len(tiles) + cols - 1) // cols
    out = Image.new("RGB", (cols * w + (cols + 1) * 6, rows * (h + 22) + 6), "white")
    d = ImageDraw.Draw(out)
    for i, t in enumerate(tiles):
        x, y = 6 + (i % cols) * (w + 6), 6 + (i // cols) * (h + 22)
        out.paste(t.resize((w, h)), (x, y + 18)); d.rectangle([x, y + 18, x + w - 1, y + 17 + h], outline="#999999")
        d.text((x, y + 3), "step %d" % (i + 1), fill="black")
    out.save(sheet)
with av.open(video) as c:
    s = c.streams.video[0]; dur = float(s.duration * s.time_base) if s.duration else 0.0
    print("video: %dx%d · %.1fs · %d steps" % (s.width, s.height, dur, len(tiles)))
    if gif != "-":
        frames, step = [], max(1, round(float(s.average_rate or 30) / 12))
        for i, fr in enumerate(c.decode(video=0)):
            if i % step == 0:
                im = fr.to_image(); frames.append(im.resize((960, int(im.height * 960 / im.width))))
        if frames:
            frames[0].save(gif, save_all=True, append_images=frames[1:], duration=int(1000 * step / float(s.average_rate or 30)), loop=0, optimize=True)
'''


def scene_name(path):
    m = re.search(r"^class\s+(\w+)\s*\(\s*(?:\w+\.)?\w*Scene\s*\)", open(path, encoding="utf-8").read(), re.M)
    if not m:
        die("no Scene class found in %s — pass --scene NAME" % path)
    return m.group(1)


def condensed_error(log_text, scene_file):
    base = re.escape(os.path.basename(scene_file))
    where = []
    for l in log_text.splitlines():
        m = re.search(base + r'(?:", line |:)(\d+)', l)
        if m and m.group(1) not in where:
            where.append(m.group(1))
    err = [l.strip(" │") for l in log_text.splitlines() if re.match(r"^\s*[│ ]*\w+(Error|Exception)\b.*", l)]
    return where, (err[-1].strip() if err else "unknown error")


def cmd_render(a):
    scene = os.path.abspath(a.scene_file)
    if not os.path.isfile(scene):
        die("not found: " + scene)
    py, env, v = find_python()
    if not py:
        die("Manim is not installed — run `animtool.py setup` first (one time).")
    name = a.scene or scene_name(scene)
    out = os.path.dirname(scene)
    media = os.path.join(out, ".media")
    q = ["--resolution", "1920,1080", "--frame_rate", "30"] if a.final else ["-ql"]
    cmd = [py, "-m", "manim", "render"] + q + ["--media_dir", media, "-v", "WARNING", "--progress_bar", "none", scene, name]
    log = os.path.join(out, "render.log")
    with open(log, "w", encoding="utf-8") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=run_env(py, env), cwd=out)
    text = open(log, encoding="utf-8", errors="replace").read()
    if r.returncode != 0:
        where, err = condensed_error(text, scene)
        die("render failed — %s%s · full log: %s" % (err, (" · scene.py line " + ", ".join(where)) if where else "", log))
    vids = [os.path.join(d, f) for d, _, fs in os.walk(os.path.join(media, "videos")) for f in fs
            if f == name + ".mp4" and "partial_movie_files" not in d]
    if not vids:
        die("render finished but no %s.mp4 was found · log: %s" % (name, log))
    vid = max(vids, key=os.path.getmtime)
    lst = os.path.join(os.path.dirname(vid), "partial_movie_files", name, "partial_movie_file_list.txt")
    final_mp4 = os.path.join(out, name + ".mp4")
    shutil.copyfile(vid, final_mp4)
    sheet = os.path.join(out, "steps.png")
    gif = os.path.join(out, name + ".gif") if a.final else "-"
    r = subprocess.run([py, "-c", SHEET, lst, sheet, str(a.cols), final_mp4, gif],
                       capture_output=True, text=True, env=run_env(py, env))
    if r.returncode != 0:
        die("frames / GIF step failed: " + (r.stderr.strip().splitlines() or ["?"])[-1])
    print(r.stdout.strip())
    print("mp4: " + final_mp4)
    if a.final:
        print("gif: " + gif)
    print("steps: %s  (read this one image to review the animation)" % sheet)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    s = sub.add_parser("setup"); s.add_argument("--force", action="store_true", help="reinstall even if Manim is found")
    s = sub.add_parser("render"); s.add_argument("scene_file"); s.add_argument("--scene"); s.add_argument("--final", action="store_true")
    s.add_argument("--cols", type=int, default=4)
    a = ap.parse_args()
    {"check": cmd_check, "setup": cmd_setup, "render": cmd_render}[a.cmd](a)


if __name__ == "__main__":
    main()
