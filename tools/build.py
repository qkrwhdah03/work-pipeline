"""Build pipeline distributables.

    python tools/build.py dev          # refresh dev/dist/
    python tools/build.py --all        # all pipelines

<name>/docs/design.md  -> <name>/dist/<name>-pipeline.pdf
<name>/kit/ + docs/install.md (as README.md) -> <name>/dist/<name>-pipeline-kit.zip
"""
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
]

HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>__TITLE__</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>
  @page { size: A4; margin: 18mm 16mm; }
  body { font-family: 'Inter', sans-serif; font-size: 10pt; line-height: 1.7; color: #1a1a1a; background: #fff; }
  h1 { font-size: 22pt; margin: 0 0 4px; }
  h2 { font-size: 14pt; margin: 28px 0 10px; padding-bottom: 6px; border-bottom: 1px solid #ddd; break-after: avoid; }
  h3 { font-size: 11.5pt; margin: 20px 0 8px; break-after: avoid; }
  p { margin: 8px 0; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9pt; break-inside: avoid; }
  th, td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; vertical-align: top; }
  th { background: #f4f4f4; }
  code { font-family: 'JetBrains Mono', monospace; font-size: 8.5pt; background: #f4f4f4; padding: 1px 4px; border-radius: 3px; }
  pre { background: #f6f6f6; border: 1px solid #e6e6e6; border-radius: 4px; padding: 10px 12px; font-size: 8.5pt; line-height: 1.5; white-space: pre-wrap; break-inside: avoid; }
  pre code { background: none; padding: 0; }
  .mermaid { text-align: center; margin: 16px 0; break-inside: avoid; }
  .mermaid svg { max-height: 150mm; max-width: 100%; }
  blockquote { margin: 10px 0; padding: 4px 12px; border-left: 3px solid #ccc; color: #555; }
</style></head><body><div id="c"></div>
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"></script>
<script>
const MD = __MD__;
const r = new marked.Renderer();
r.code = (code, lang) => lang === 'mermaid'
  ? '<div class="mermaid">' + code.replace(/</g, '&lt;') + '</div>'
  : '<pre><code>' + code.replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</code></pre>';
document.getElementById('c').innerHTML = marked.parse(MD, { renderer: r });
mermaid.initialize({ startOnLoad: false, theme: 'neutral', fontFamily: 'Inter' });
// Under headless virtual time mermaid's auto-generated ids collide, so assign ids explicitly
document.fonts.ready.then(async () => {
  const els = [...document.querySelectorAll('.mermaid')];
  for (let i = 0; i < els.length; i++) {
    const { svg } = await mermaid.render('mmd' + i, els[i].textContent);
    els[i].innerHTML = svg;
  }
}).catch(e => console.error('MERMAID', e && e.message));
</script></body></html>'''


def find_chrome():
    for c in CHROME_CANDIDATES:
        if os.path.isfile(c):
            return c
        try:
            subprocess.run([c, "--version"], capture_output=True, check=True)
            return c
        except (OSError, subprocess.CalledProcessError):
            pass
    sys.exit("Chrome/Edge not found.")


def build_pdf(name, base, dist):
    md = io.open(os.path.join(base, "docs", "design.md"), encoding="utf-8").read()
    m = re.search(r"^# (.+)$", md, re.M)
    title = m.group(1).strip() if m else name
    html = HTML.replace("__TITLE__", title).replace("__MD__", json.dumps(md, ensure_ascii=False))
    out = os.path.join(dist, name + "-pipeline.pdf")
    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, "design.html")
        io.open(page, "w", encoding="utf-8").write(html)
        subprocess.run([find_chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        "--virtual-time-budget=20000", "--run-all-compositor-stages-before-draw",
                        "--print-to-pdf=" + out, pathlib.Path(page).as_uri()],
                       capture_output=True, check=True)
    print("  [v]", os.path.relpath(out, ROOT))


def build_zip(name, base, dist):
    kit = os.path.join(base, "kit")
    top = name + "-pipeline-kit"
    out = os.path.join(dist, top + ".zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(base, "docs", "install.md"), top + "/README.md")
        for d, dirs, files in os.walk(kit):
            dirs[:] = sorted(x for x in dirs if x != "__pycache__")  # left behind by running the kit scripts
            rel = os.path.relpath(d, kit).replace(os.sep, "/")
            prefix = top if rel == "." else top + "/" + rel
            for f in sorted(files):
                z.write(os.path.join(d, f), prefix + "/" + f)
    print("  [v]", os.path.relpath(out, ROOT))


def pipelines():
    return sorted(n for n in os.listdir(ROOT)
                  if os.path.isfile(os.path.join(ROOT, n, "docs", "design.md")))


def main():
    args = sys.argv[1:]
    names = pipelines() if args == ["--all"] else args
    if not names:
        sys.exit(__doc__)
    for name in names:
        base = os.path.join(ROOT, name)
        if name not in pipelines():
            sys.exit("Pipeline not found: " + name)
        dist = os.path.join(base, "dist")
        os.makedirs(dist, exist_ok=True)
        print(name)
        build_zip(name, base, dist)
        build_pdf(name, base, dist)


if __name__ == "__main__":
    main()
