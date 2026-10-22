#!/usr/bin/env python3
"""Lookup helper for the research pipeline. Python 3 standard library only.

    researchtool.py search  "<query>" [--n 10] [--since YEAR]   find candidates (OpenAlex)
    researchtool.py meta    <arXiv id | DOI | "title">          merged metadata: arXiv + Crossref + OpenAlex
    researchtool.py cites   <arXiv id | DOI> [--n 10] [--since YEAR]   most-cited works citing it
    researchtool.py page    <url> [--grep REGEX] [--links REGEX]   fetch a page as a browser; title, GitHub links, matching links
    researchtool.py venue-url "<title>" <CVPR2024|ICCV2023|WACV2024>   the paper's CVF Open Access page
    researchtool.py github  <owner/repo> [--paper "<title>"] [--paper <arXiv id>] [--page <project page>]
                                                                repo exists? README names the paper? page links the repo?
    researchtool.py bibtex  <venue page URL> [DOI] [arXiv id]   first link that shows BibTeX
    researchtool.py fulltext <arXiv id> [--out FILE]            arXiv HTML -> plain text file + outline

Output is compact plain text. Errors print one "ERROR: ..." line and exit 1.
Optional env: OPENALEX_API_KEY, SEMANTIC_SCHOLAR_API_KEY (not required).
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
UA_TOOL = "research-pipeline/1.0 (Claude Code research kit)"
ARXIV_ID = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")
DOI = re.compile(r"(10\.\d{4,9}/[^\s\"<>]+)")


def die(msg):
    print("ERROR: " + msg)
    sys.exit(1)


def fetch(url, browser=False, accept=None, retries=2):
    headers = {"User-Agent": UA_BROWSER if browser else UA_TOOL}
    if accept:
        headers["Accept"] = accept
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                time.sleep(3 * (attempt + 1))
                continue
            return e.code, ""
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt < retries:
                time.sleep(2)
                continue
            return 0, str(e)
    return 0, ""


def fetch_json(url):
    status, body = fetch(url)
    if status != 200:
        return None
    try:
        return json.loads(body)
    except ValueError:
        return None


def openalex(path, **params):
    if os.environ.get("OPENALEX_API_KEY"):
        params["api_key"] = os.environ["OPENALEX_API_KEY"]
    return fetch_json("https://api.openalex.org/" + path + "?" + urllib.parse.urlencode(params))


def oa_line(w):
    loc = (w.get("primary_location") or {}).get("source") or {}
    ids = w.get("ids") or {}
    arx = ""
    for l in w.get("locations") or []:
        m = ARXIV_ID.search((l.get("landing_page_url") or ""))
        if m and "arxiv" in (l.get("landing_page_url") or ""):
            arx = m.group(1)
            break
    doi = (ids.get("doi") or "").replace("https://doi.org/", "")
    return "{y} | {v} | {c} cites | {t} | doi:{d} | arXiv:{a} | {oid}".format(
        y=w.get("publication_year") or "?", v=loc.get("display_name") or "?",
        c=w.get("cited_by_count", "?"), t=w.get("title") or w.get("display_name") or "?",
        d=doi or "-", a=arx or "-", oid=(w.get("id") or "").rsplit("/", 1)[-1])


def is_preprint(w):
    src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
    doi = (w.get("doi") or "").lower()
    return "arxiv" in src.lower() or "10.48550" in doi or w.get("type") == "preprint"


def published_work(title):
    """OpenAlex work with this exact title, preferring the published version over the arXiv record."""
    res = openalex("works", search=title, **{"per-page": 8})
    same = [w for w in (res or {}).get("results", []) if norm(w.get("title")) == norm(title)]
    if not same:
        return None
    return max(same, key=lambda w: (not is_preprint(w), w.get("cited_by_count") or 0))


def resolve_openalex(ref):
    """OpenAlex work for an arXiv id, DOI or title — the published version when one exists."""
    m = DOI.search(ref)
    if m and not ARXIV_ID.fullmatch(ref) and "10.48550" not in m.group(1):
        w = fetch_json("https://api.openalex.org/works/doi:" + urllib.parse.quote(m.group(1)))
        if w:
            return w
    m = ARXIV_ID.search(ref)
    if m:
        arx = arxiv_entry(m.group(1))
        if arx and arx.get("doi"):
            w = fetch_json("https://api.openalex.org/works/doi:" + urllib.parse.quote(arx["doi"]))
            if w:
                return w
        if arx:
            return published_work(arx["title"]) or fetch_json(
                "https://api.openalex.org/works/doi:10.48550/arXiv." + m.group(1))
    return published_work(ref)


def oa_abstract(w):
    inv = (w or {}).get("abstract_inverted_index")
    if not inv:
        return None
    pos = sorted((i, word) for word, idx in inv.items() for i in idx)
    return " ".join(word for _, word in pos)


def arxiv_entry(arxiv_id=None, title=None):
    if arxiv_id:
        q = "id_list=" + arxiv_id
    else:
        q = "search_query=" + urllib.parse.quote('ti:"%s"' % title) + "&max_results=1"
    status, body = fetch("https://export.arxiv.org/api/query?" + q)
    if status != 200:
        return None
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    try:
        e = ET.fromstring(body).find("a:entry", ns)
    except ET.ParseError:
        return None
    if e is None or e.find("a:title", ns) is None:
        return None
    t = lambda tag: re.sub(r"\s+", " ", (e.findtext(tag, "", ns) or "")).strip()
    return {
        "id": ARXIV_ID.search(t("a:id")).group(0) if ARXIV_ID.search(t("a:id")) else t("a:id"),
        "title": t("a:title"), "published": t("a:published")[:10],
        "authors": [re.sub(r"\s+", " ", a.findtext("a:name", "", ns)) for a in e.findall("a:author", ns)],
        "comment": t("x:comment"), "journal_ref": t("x:journal_ref"), "doi": t("x:doi"),
        "abstract": t("a:summary"),
    }


def crossref(doi=None, title=None):
    if doi:
        j = fetch_json("https://api.crossref.org/works/" + urllib.parse.quote(doi))
        item = (j or {}).get("message")
    else:
        j = fetch_json("https://api.crossref.org/works?rows=1&query.bibliographic=" + urllib.parse.quote(title))
        items = ((j or {}).get("message") or {}).get("items") or []
        item = items[0] if items else None
    if not item:
        return None
    issued = (item.get("issued") or {}).get("date-parts") or [[None]]
    return {"title": html.unescape((item.get("title") or [""])[0]), "venue": html.unescape((item.get("container-title") or [""])[0]),
            "year": issued[0][0], "doi": item.get("DOI"), "volume": item.get("volume"),
            "issue": item.get("issue"), "type": item.get("type"),
            "authors": [" ".join(filter(None, [a.get("given"), a.get("family")])) for a in item.get("author") or []]}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


# ---------------------------------------------------------------- commands

def cmd_search(a):
    params = {"search": a.query, "per-page": a.n, "sort": "relevance_score:desc"}
    if a.since:
        params["filter"] = "from_publication_date:%d-01-01" % a.since
    res = openalex("works", **params)
    if res is None:
        die("OpenAlex search failed (rate limit or network). Fall back to WebSearch.")
    print("# year | venue | cites | title | doi | arXiv | openalex id")
    for w in res.get("results", []):
        print(oa_line(w))


def cmd_meta(a):
    ref = a.ref.strip()
    m_arx = ARXIV_ID.search(ref) if ("arxiv" in ref.lower() or ARXIV_ID.fullmatch(ref)) else None
    m_doi = None if m_arx else DOI.search(ref)

    # 1. Find the title, whatever the input was
    arx = arxiv_entry(m_arx.group(1)) if m_arx else None
    cr = crossref(doi=m_doi.group(1)) if m_doi else None
    title = (arx or {}).get("title") or (cr or {}).get("title") or (None if m_doi else ref)
    if not title:
        die("no record found for: " + ref)
    # 2. arXiv record by title when the input wasn't an arXiv id
    if not arx:
        arx = arxiv_entry(title=title)
        if arx and norm(arx["title"]) != norm(title):
            arx = None  # title search hit a different paper
    # 3. The published OpenAlex work, then its DOI for Crossref
    w = resolve_openalex(m_doi.group(1) if m_doi else (arx and arx.get("doi")) or title)
    if w and norm(w.get("title")) != norm(title):
        w = None
    pub_doi = (m_doi.group(1) if m_doi else None) or (arx or {}).get("doi") or None
    if not pub_doi and w and not is_preprint(w):
        pub_doi = (w.get("doi") or "").replace("https://doi.org/", "") or None
    if not cr and pub_doi:
        cr = crossref(doi=pub_doi)
    if not cr:
        cr = crossref(title=title)
        if cr and norm(cr["title"]) != norm(title):
            cr = None
    if not (arx or cr or w):
        die("no record found in arXiv, Crossref or OpenAlex for: " + ref)

    out = []
    if arx:
        out += ["[arXiv] " + arx["id"] + " · first version " + arx["published"],
                "  title: " + arx["title"],
                "  authors: " + ", ".join(arx["authors"]),
                "  journal_ref: " + (arx["journal_ref"] or "-"),
                "  comment: " + (arx["comment"] or "-"),
                "  doi: " + (arx["doi"] or "-")]
    if cr:
        vi = "".join(filter(None, [cr["volume"], "(%s)" % cr["issue"] if cr["issue"] else None]))
        out += ["[Crossref] " + (cr["doi"] or "-") + " · " + (cr["type"] or "?"),
                "  title: " + cr["title"],
                "  venue: %s %s · %s" % (cr["venue"] or "?", vi, cr["year"] or "?"),
                "  authors: " + ", ".join(cr["authors"][:8])]
    if w:
        loc = (w.get("primary_location") or {})
        oa = (w.get("open_access") or {}).get("oa_url") or "-"
        out += ["[OpenAlex] " + (w.get("id") or "").rsplit("/", 1)[-1],
                "  title: " + (w.get("title") or "?"),
                "  venue: %s · %s" % (((loc.get("source") or {}).get("display_name")) or "?", w.get("publication_year")),
                "  cites: %s (OpenAlex, %s)" % (w.get("cited_by_count"), time.strftime("%Y-%m-%d")),
                "  open access: " + oa]
    if arx:
        out += ["[abstract, exact — arXiv]", arx["abstract"]]
    elif oa_abstract(w):
        out += ["[abstract — OpenAlex, may differ slightly in punctuation]", oa_abstract(w)]
    print("\n".join(out))


def cmd_cites(a):
    w = resolve_openalex(a.ref)
    if not w:
        die("could not resolve in OpenAlex: " + a.ref)
    wid = w["id"].rsplit("/", 1)[-1]
    flt = "cites:" + wid + (",from_publication_date:%d-01-01" % a.since if a.since else "")
    res = openalex("works", filter=flt, sort="cited_by_count:desc", **{"per-page": a.n})
    if res is None:
        die("OpenAlex citing-works query failed.")
    print("# cited by %s works in total · top %d by citations" % (w.get("cited_by_count"), a.n))
    print("# year | venue | cites | title | doi | arXiv | openalex id")
    for x in res.get("results", []):
        print(oa_line(x))


class _Text(HTMLParser):
    """HTML -> text. Keeps math alttext, marks headings, skips scripts/styles/nav."""
    SKIP = {"script", "style", "nav", "header", "footer", "button"}
    BLOCK = {"p", "div", "section", "li", "tr", "br", "figcaption", "table", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip, self.in_math = [], 0, 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag in self.SKIP:
            self.skip += 1
        elif tag == "math":
            self.out.append(" $" + (d.get("alttext") or "") + "$ ")
            self.in_math += 1
        elif tag in self.BLOCK:
            self.out.append("\n")
            if re.fullmatch(r"h[1-6]", tag):
                self.out.append("#" * int(tag[1]) + " ")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag == "math" and self.in_math:
            self.in_math -= 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip and not self.in_math:
            self.out.append(data)

    def text(self):
        t = "".join(self.out)
        t = re.sub(r"[ \t ]+", " ", t)
        t = re.sub(r" *\n *", "\n", t)
        return re.sub(r"\n{3,}", "\n\n", t).strip()


def cmd_page(a):
    status, body = fetch(a.url, browser=True)
    if status == 404:
        die("HTTP 404 for %s — the URL is wrong (not a block). For CVF papers use `venue-url`." % a.url)
    if status != 200:
        die("HTTP %s for %s — the site may block automated access; use the DOI record or another official page." % (status, a.url))
    title = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
    cvf = re.search(r'id="papertitle">\s*(.*?)\s*<', body, re.S)
    print("status: 200")
    print("title: " + html.unescape(re.sub(r"\s+", " ", title.group(1))).strip() if title else "title: -")
    if cvf:
        print("paper title (CVF): " + html.unescape(cvf.group(1).strip()))
    gh = sorted(set(re.findall(r"https?://github\.com/[\w.-]+/[\w.-]+", body)))
    gh = [g.rstrip(".") for g in gh if not re.search(r"github\.com/(features|about|login|sponsors)/", g)]
    print("github links: " + (", ".join(gh[:10]) if gh else "-"))
    if a.links:
        found = [(h, re.sub(r"<[^>]+>|\s+", " ", t).strip())
                 for h, t in re.findall(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', body, re.S | re.I)]
        found = [(urllib.parse.urljoin(a.url, h), html.unescape(t)) for h, t in found
                 if re.search(a.links, h, re.I) or re.search(a.links, html.unescape(t), re.I)]
        print("links matching /%s/ (%d):" % (a.links, len(found)))
        for h, t in found[:20]:
            print("  %s — %s" % (h, t[:120]))
    if a.grep:
        p = _Text(); p.feed(body)
        lines = [l for l in p.text().splitlines() if re.search(a.grep, l, re.I)]
        print("lines matching /%s/ (%d):" % (a.grep, len(lines)))
        for l in lines[:20]:
            print("  " + l[:300])


def cmd_github(a):
    repo = re.sub(r"^https?://github\.com/", "", a.repo).strip("/")
    r = fetch_json("https://api.github.com/repos/" + repo)
    if not r:
        die("repo not found or GitHub API unavailable: " + repo)
    print("repo: %s · owner type: %s · stars: %s · archived: %s" % (
        r["full_name"], (r.get("owner") or {}).get("type"), r.get("stargazers_count"), r.get("archived")))
    print("description: " + (r.get("description") or "-"))
    print("homepage: " + (r.get("homepage") or "-"))
    if a.paper:
        status, readme = fetch("https://api.github.com/repos/%s/readme" % repo, accept="application/vnd.github.raw")
        if status != 200:
            print("README: not available")
            return
        hits = []
        for key in a.paper:
            m = ARXIV_ID.fullmatch(key.strip())
            if m and m.group(1) in readme:
                hits.append("arXiv id")
            elif not m and norm(key) and norm(key) in norm(readme):
                hits.append("title")
        print("README mentions the paper: %s" % ("yes (" + ", ".join(hits) + ")" if hits else "no"))
    if a.page:
        status, body = fetch(a.page, browser=True)
        linked = status == 200 and ("github.com/" + repo.lower()) in body.lower()
        print("linked from %s: %s" % (a.page, "yes" if linked else "no" if status == 200 else "page unreachable (HTTP %s)" % status))


CVF_CONF = re.compile(r"^(CVPR|ICCV|WACV)(\d{4})$", re.I)


def cmd_venue_url(a):
    """Find a paper's CVF Open Access page from its title (URL slugs can't be guessed reliably)."""
    m = CVF_CONF.match(a.conf.strip())
    if not m:
        die("venue-url supports CVF conferences (CVPR<year>, ICCV<year>, WACV<year>). For others use WebSearch.")
    conf = m.group(1).upper() + m.group(2)
    listing = "https://openaccess.thecvf.com/%s?day=all" % conf
    status, body = fetch(listing, browser=True)
    if status != 200:
        status, body = fetch("https://openaccess.thecvf.com/" + conf, browser=True)
    if status != 200:
        die("could not load the %s listing (HTTP %s)." % (conf, status))
    want = norm(a.title)
    for href, text in re.findall(r'<dt class="ptitle">\s*<br>\s*<a href="([^"]+)">(.*?)</a>', body, re.S | re.I):
        if norm(html.unescape(text)) == want:
            print("url: " + urllib.parse.urljoin("https://openaccess.thecvf.com/", href))
            return
    die("title not found in the %s listing — check the conference/year, or it may be a workshop paper." % conf)


BIB = re.compile(r"@(inproceedings|article|misc|incollection|book)\s*\{", re.I)


def bibtex_candidates(ref):
    """URLs that may serve BibTeX for one reference, best first."""
    ref = ref.strip()
    if ref.startswith("http"):
        if "proceedings.neurips.cc" in ref and "/hash/" in ref:
            yield re.sub(r"-Abstract(-[A-Za-z_]+)?\.html$", "-Bibtex.bib", ref.replace("/hash/", "/file/"))
        elif "openaccess.thecvf.com" in ref or "proceedings.mlr.press" in ref:
            yield ref  # the venue's html page carries the BibTeX block
        m = ARXIV_ID.search(ref) if "arxiv.org" in ref else None
        if m:
            yield "https://arxiv.org/bibtex/" + m.group(1)
        return
    m = DOI.search(ref)
    if m and not ARXIV_ID.fullmatch(ref):
        yield "https://api.crossref.org/works/%s/transform/application/x-bibtex" % m.group(1)
        return
    m = ARXIV_ID.search(ref)
    if m:
        yield "https://arxiv.org/bibtex/" + m.group(1)


def cmd_bibtex(a):
    """Try refs in the given order (venue page, DOI, arXiv id); print the first URL that serves BibTeX."""
    tried = []
    for ref in a.refs:
        for url in bibtex_candidates(ref):
            status, body = fetch(url, browser=True)
            if status == 200 and BIB.search(body):
                kind = ("venue" if any(s in url for s in ("thecvf", "mlr.press", "neurips.cc"))
                        else "Crossref (DOI)" if "crossref" in url else "arXiv")
                print("bibtex: %s · source: %s" % (url, kind))
                return
            tried.append("%s (HTTP %s)" % (url, status))
    die("no BibTeX link verified. Tried: " + ("; ".join(tried) or "nothing usable in the refs given"))


def cmd_fulltext(a):
    m = ARXIV_ID.search(a.ref)
    if not m:
        die("fulltext needs an arXiv id; for a local PDF read the file directly.")
    aid = m.group(0)
    status, body = fetch("https://arxiv.org/html/" + aid, browser=True)
    if status != 200 or "ltx_document" not in body:
        die("no arXiv HTML for %s (HTTP %s). Read the PDF instead: https://arxiv.org/pdf/%s" % (aid, status, aid))
    p = _Text(); p.feed(body)
    text = p.text()
    out = a.out or os.path.join(".research", "cache", aid.replace("/", "_") + ".txt")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    lines = text.splitlines()
    print("saved: %s · %d lines · %d chars" % (out, len(lines), len(text)))
    print("outline (line: heading):")
    for i, l in enumerate(lines, 1):
        if l.startswith("#"):
            print("  %d: %s" % (i, l[:120]))
    caps = [(i, l) for i, l in enumerate(lines, 1) if re.match(r"(Table|Figure|Fig\.)\s*\d+", l)]
    if caps:
        print("tables / figures (line: caption):")
        for i, l in caps[:40]:
            print("  %d: %s" % (i, l[:110]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--n", type=int, default=10); s.add_argument("--since", type=int)
    s = sub.add_parser("meta"); s.add_argument("ref")
    s = sub.add_parser("cites"); s.add_argument("ref"); s.add_argument("--n", type=int, default=10); s.add_argument("--since", type=int)
    s = sub.add_parser("page"); s.add_argument("url"); s.add_argument("--grep"); s.add_argument("--links", help="regex on link href or text")
    s = sub.add_parser("venue-url"); s.add_argument("title"); s.add_argument("conf", help="e.g. CVPR2024, ICCV2023")
    s = sub.add_parser("github"); s.add_argument("repo"); s.add_argument("--paper", action="append", default=[], help="title or arXiv id; repeatable"); s.add_argument("--page", help="project / venue page that should link the repo")
    s = sub.add_parser("bibtex"); s.add_argument("refs", nargs="+")
    s = sub.add_parser("fulltext"); s.add_argument("ref"); s.add_argument("--out")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    {"search": cmd_search, "meta": cmd_meta, "cites": cmd_cites, "page": cmd_page, "venue-url": cmd_venue_url,
     "github": cmd_github, "bibtex": cmd_bibtex, "fulltext": cmd_fulltext}[a.cmd](a)


if __name__ == "__main__":
    main()
