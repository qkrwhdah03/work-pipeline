#!/usr/bin/env python3
"""Lookup helper for the research pipeline. Python 3 standard library only.

    researchtool.py search  "<query>" [--n 10] [--since YEAR] [--sort relevance|cites]   find candidates (OpenAlex)
    researchtool.py meta    <arXiv id | DOI | "title">          merged metadata: arXiv + Crossref + OpenAlex
    researchtool.py cites   <arXiv id | DOI> [--n 10] [--since YEAR]   most-cited works citing it
    researchtool.py page    <url> [--grep REGEX] [--links REGEX]   fetch a page as a browser; title, GitHub links, matching links
    researchtool.py venue-url "<title>" <CVPR2024|ICCV2023|WACV2024>   the paper's CVF Open Access page
    researchtool.py github  <owner/repo> [--paper "<title>"] [--paper <arXiv id>] [--page <project page>]
                                                                repo exists? README names the paper? page links the repo?
    researchtool.py bibtex  <venue page URL> [DOI] [arXiv id]   first link that shows BibTeX
    researchtool.py download <venue page URL | PDF URL | arXiv id>... --year Y --title T --venue V [--dir DIR | --downloads]
                             [--code URL] [--page URL]          save the first open PDF as "Y. T (V).pdf" in .research/pdfs/
                                                                (--dir: a folder the user named; --downloads: their Downloads folder)
                                                                plus "Y. T (V).txt": citation, links, BibTeX + source, abstract;
                                                                then rebuilds index.txt and references.bib in that folder
                                                                (never overwrites files of those names it didn't write)
    researchtool.py index [--dir DIR | --downloads]             rebuild index.txt + references.bib from the per-paper .txt
                                                                files (a .txt counts only with its .pdf beside it)
    researchtool.py fulltext <arXiv id> [--out FILE]            arXiv HTML -> plain text file + outline

Output is compact plain text. Errors print one "ERROR: ..." line and exit 1.
Optional env: OPENALEX_API_KEY, SEMANTIC_SCHOLAR_API_KEY (not required).
"""
import argparse
import html
import http.client
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
# New-style ids (1706.03762, not the "2729.2023" inside a DOI) and old-style ids (hep-th/9901001).
ARXIV_ID = re.compile(r"(?<!\d)(?<!\d\.)(\d{4}\.\d{4,5}"
                      r"|(?<![\w-])(?:astro-ph|cond-mat|gr-qc|hep-(?:ex|lat|ph|th)|math-ph|nlin|nucl-(?:ex|th)"
                      r"|physics|quant-ph|math|cs|q-bio|q-fin|stat)(?:\.[A-Z]{2})?/\d{7})(v\d+)?(?!\d)")
DOI = re.compile(r"(10\.\d{4,9}/[^\s\"<>]+)")


def arxiv_of(ref, version=False):
    """The arXiv id in ref — a bare id, an arxiv.org URL, 'arXiv:<id>' or an arXiv DOI; None for other DOIs / URLs."""
    ref = (ref or "").strip()
    m = ARXIV_ID.search(ref)
    if m and (ARXIV_ID.fullmatch(ref) or "arxiv" in ref.lower()):
        return m.group(0) if version else m.group(1)
    return None


def die(msg):
    print("ERROR: " + " ".join(str(msg).split()))
    sys.exit(1)


def safe_url(url):
    """Percent-encode non-ASCII / unsafe characters (and IDNA-encode the host) so urllib can send the URL."""
    p = urllib.parse.urlsplit(url.strip())
    host = p.netloc
    try:
        host.encode("ascii")
    except UnicodeError:
        host = host.encode("idna").decode("ascii")
    q = urllib.parse.quote
    return urllib.parse.urlunsplit((p.scheme, host, q(p.path, safe="/%:@!$&'()*+,;=~"),
                                    q(p.query, safe="=&%/:?@!$'()*+,;~"), q(p.fragment, safe="%/?:@!$&'()*+,;=~")))


def fetch(url, browser=False, accept=None, retries=2):
    """(HTTP status, text). Status 0 means no response; the text then holds the reason."""
    headers = {"User-Agent": UA_BROWSER if browser else UA_TOOL}
    if accept:
        headers["Accept"] = accept
    try:
        req = urllib.request.Request(safe_url(url), headers=headers)
    except (ValueError, UnicodeError) as e:
        return 0, "bad URL %r (%s)" % (url, e)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                time.sleep(3 * (attempt + 1))
                continue
            return e.code, ""
        except (ValueError, UnicodeError) as e:
            return 0, "bad URL %r (%s)" % (url, e)
        except (http.client.HTTPException, OSError) as e:  # URLError, timeouts, resets, truncated reads
            if attempt < retries:
                time.sleep(2)
                continue
            return 0, str(e) or type(e).__name__
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
    cell = lambda s: re.sub(r"\s*\|\s*", " / ", str(s))  # '|' is the column separator
    return "{y} | {v} | {c} cites | {t} | doi:{d} | arXiv:{a} | {oid}".format(
        y=w.get("publication_year") or "?", v=cell(loc.get("display_name") or "?"),
        c=w.get("cited_by_count", "?"), t=cell(w.get("title") or w.get("display_name") or "?"),
        d=doi or "-", a=arx or "-", oid=(w.get("id") or "").rsplit("/", 1)[-1])


def is_preprint(w):
    src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
    doi = (w.get("doi") or "").lower()
    return "arxiv" in src.lower() or "10.48550" in doi or w.get("type") == "preprint"


def oa_authors(w):
    return [((x or {}).get("author") or {}).get("display_name") or "" for x in (w or {}).get("authorships") or []]


def surname(name):
    toks = [t for t in (name or "").replace(",", " ").split() if not re.fullmatch(r"(jr|sr|ii|iii|iv)\.?", t, re.I)]
    return norm(toks[-1]) if toks else ""


def same_people(ref_authors, cand_authors, ref_year=None, cand_year=None):
    """Is a same-title candidate the paper we mean? Its authors must include our first author's surname,
    and it can't be dated well before the reference. With no reference authors there's nothing to check."""
    if ref_year and cand_year and int(cand_year) < int(ref_year) - 1:
        return False
    s = surname(ref_authors[0]) if ref_authors else ""
    if not s:
        return True
    return any(s in norm(c) for c in cand_authors)


def year_of(arx):
    y = (arx or {}).get("published", "")[:4]
    return int(y) if y.isdigit() else None


def published_work(title, authors=None, year=None):
    """OpenAlex work with this exact title (and, when known, the same first author), preferring the
    published version over the arXiv record. Without authors to check, the most-cited one."""
    res = openalex("works", search=title, **{"per-page": 8})
    same = [w for w in (res or {}).get("results", []) if norm(w.get("title")) == norm(title)
            and same_people(authors, oa_authors(w), year, w.get("publication_year"))]
    if not same:
        return None
    if authors:
        return max(same, key=lambda w: (not is_preprint(w), w.get("cited_by_count") or 0))
    return max(same, key=lambda w: w.get("cited_by_count") or 0)


def openalex_doi(doi):
    return fetch_json("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi))


def openalex_for_arxiv(arx, aid):
    """The published OpenAlex work for an arXiv paper; the arXiv DOI record when no same-author match exists."""
    if arx and arx.get("doi"):
        w = openalex_doi(arx["doi"])
        if w:
            return w
    if arx:
        w = published_work(arx["title"], arx["authors"], year_of(arx))
        if w:
            return w
    return openalex_doi("10.48550/arXiv." + re.sub(r"v\d+$", "", aid))


def resolve_openalex(ref):
    """OpenAlex work for an arXiv id, DOI or title — the published version when one exists."""
    ref = ref.strip()
    aid = arxiv_of(ref)
    m = DOI.search(ref)
    if m and not aid:
        return openalex_doi(m.group(1))
    if aid:
        return openalex_for_arxiv(arxiv_entry(aid), aid)
    arx = arxiv_entry(title=ref)
    if arx and norm(arx["title"]) == norm(ref):
        return openalex_for_arxiv(arx, arx["id"])
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
        q = "search_query=" + urllib.parse.quote('ti:"%s"' % title.replace('"', " ")) + "&max_results=1"
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
    params = {"search": a.query, "per-page": a.n,
              "sort": "cited_by_count:desc" if a.sort == "cites" else "relevance_score:desc"}
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
    aid = arxiv_of(ref)
    m_doi = None if aid else DOI.search(ref)

    # 1. Find the title, whatever the input was (a DOI Crossref lacks, e.g. DataCite: OpenAlex)
    arx = arxiv_entry(aid) if aid else None
    cr = crossref(doi=m_doi.group(1)) if m_doi else None
    w_doi = openalex_doi(m_doi.group(1)) if m_doi and not cr else None
    title = ((arx or {}).get("title") or (cr or {}).get("title") or (w_doi or {}).get("title")
             or (None if m_doi else ref))
    if not title:
        die("no record found for: " + ref)
    # 2. arXiv record by title when the input wasn't an arXiv id
    if not arx:
        arx = arxiv_entry(title=title)
        if arx and norm(arx["title"]) != norm(title):
            arx = None  # title search hit a different paper
    # 3. The published OpenAlex work (same first author), then its DOI for Crossref
    if m_doi:
        w = w_doi or openalex_doi(m_doi.group(1))
    elif arx:
        w = openalex_for_arxiv(arx, arx["id"])
    else:
        w = published_work(title)
    if w and norm(w.get("title")) != norm(title):
        w = None
    ref_authors = (arx or {}).get("authors") or (cr or {}).get("authors") or oa_authors(w)
    ref_year = year_of(arx)
    pub_doi = (m_doi.group(1) if m_doi else None) or (arx or {}).get("doi") or None
    if not pub_doi and w and not is_preprint(w):
        pub_doi = (w.get("doi") or "").replace("https://doi.org/", "") or None
    if not cr and pub_doi:
        cr = crossref(doi=pub_doi)
    if not cr:
        cr = crossref(title=title)
        if cr and (norm(cr["title"]) != norm(title)
                   or not same_people(ref_authors, cr["authors"], ref_year, cr["year"])):
            cr = None  # same title, different paper
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


def check_regex(flag, pattern):
    try:
        re.compile(pattern)
    except re.error as e:
        die("bad %s regex %r: %s" % (flag, pattern, e))


def cmd_page(a):
    for flag, pat in (("--links", a.links), ("--grep", a.grep)):
        if pat:
            check_regex(flag, pat)
    status, body = fetch(a.url, browser=True)
    if status == 0:
        die("could not fetch %s: %s" % (a.url, body or "no response"))
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
    parts = [p for p in re.sub(r"^(https?://)?(www\.)?github\.com/", "", a.repo.strip(), flags=re.I).split("/") if p]
    if len(parts) < 2:
        die("expected owner/repo or a github.com repo URL: " + a.repo)
    repo = parts[0] + "/" + re.sub(r"\.git$", "", parts[1])  # drops /tree/main, /blob/..., .git
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
        else:
            hits = []
            for key in a.paper:
                aid = arxiv_of(key)
                if aid and aid in readme:
                    hits.append("arXiv id")
                elif not aid and norm(key) and norm(key) in norm(readme):
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
        aid = arxiv_of(ref) if "arxiv.org" in ref else None
        if aid:
            yield "https://arxiv.org/bibtex/" + aid
        return
    aid = arxiv_of(ref)
    if aid:
        yield "https://arxiv.org/bibtex/" + aid
        return
    m = DOI.search(ref)
    if m:
        yield "https://api.crossref.org/works/%s/transform/application/x-bibtex" % m.group(1)


def bibtex_entry(body):
    """The first BibTeX entry in a .bib file or an HTML page (CVF / PMLR show it in a block), braces balanced."""
    text = html.unescape(re.sub(r"<br\s*/?>", "\n", body, flags=re.I))
    m = BIB.search(text)
    if not m:
        return None
    depth, i = 0, m.end() - 1
    for j in range(i, len(text)):
        depth += {"{": 1, "}": -1}.get(text[j], 0)
        if depth == 0:
            entry = re.sub(r"<[^>]+>", "", text[m.start():j + 1]).strip()
            if "\n" not in entry:
                entry = bibtex_unfold(entry)
            return "\n".join(l.rstrip() for l in entry.splitlines() if l.strip())
    return None


def bibtex_unfold(entry):
    """One-line BibTeX (Crossref) -> one field per line: break after each top-level comma."""
    out, depth = [], 0
    for ch in entry:
        depth += {"{": 1, "}": -1}.get(ch, 0)
        out.append(ch)
        if ch == "," and depth == 1:
            out.append("\n   ")
    s = "".join(out)
    return re.sub(r"\s*\}$", "\n}", s)


def find_bibtex(refs):
    """(url, source kind, entry) for the first ref that serves BibTeX — venue page, DOI, arXiv id, in the order given."""
    tried = []
    for ref in refs:
        for url in bibtex_candidates(ref):
            status, body = fetch(url, browser=True)
            entry = bibtex_entry(body) if status == 200 else None
            if entry:
                kind = ("venue" if any(s in url for s in ("thecvf", "mlr.press", "neurips.cc"))
                        else "Crossref (DOI)" if "crossref" in url else "arXiv")
                return url, kind, entry, tried
            tried.append("%s (HTTP %s)" % (url, status))
    return None, None, None, tried


def cmd_bibtex(a):
    """Try refs in the given order (venue page, DOI, arXiv id); print the first URL that serves BibTeX."""
    url, kind, entry, tried = find_bibtex(a.refs)
    if not url:
        die("no BibTeX link verified. Tried: " + ("; ".join(tried) or "nothing usable in the refs given"))
    print("bibtex: %s · source: %s" % (url, kind))
    print(entry)


def downloads_dir():
    """The user's Downloads folder, including a relocated one on Windows."""
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
                path = os.path.expandvars(winreg.QueryValueEx(k, "{374DE290-123F-4565-9164-39C4925E467B}")[0])
                if os.path.isdir(path):
                    return path
        except OSError:
            pass
    xdg = os.path.join(os.path.expanduser("~"), ".config", "user-dirs.dirs")
    if os.path.isfile(xdg):
        m = re.search(r'XDG_DOWNLOAD_DIR="([^"]+)"', open(xdg, encoding="utf-8").read())
        if m:
            path = os.path.expandvars(m.group(1).replace("$HOME", os.path.expanduser("~")))
            if os.path.isdir(path):
                return path
    return os.path.join(os.path.expanduser("~"), "Downloads")


def _clean(s):
    s = re.sub(r"\s*:\s*", " - ", str(s))
    s = re.sub(r'[<>"/\\|?*\x00-\x1f]', "", s)
    return re.sub(r"\s+", " ", s).strip()


def paper_filename(year, title, venue, limit=120):
    """'<year>. <title> (<venue>)' valid on Windows / macOS / Linux; a long title is cut, keeping year and venue."""
    head, tail, t = "%s. " % _clean(year), " (%s)" % _clean(venue), _clean(title)
    room = max(10, limit - len(head) - len(tail))
    if len(t) > room:
        t = t[:room].rstrip(" .-")
    return (head + t + tail).rstrip(" .")


def fetch_bytes(url):
    try:
        req = urllib.request.Request(safe_url(url), headers={"User-Agent": UA_BROWSER})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except (ValueError, UnicodeError, http.client.HTTPException, OSError):
        return 0, b""


def pdf_candidates(ref):
    """Open PDF URLs for one reference, best first: the venue's own PDF, then arXiv."""
    ref = ref.strip()
    aid = arxiv_of(ref)
    if aid:
        yield "https://arxiv.org/pdf/" + aid
        return
    d = DOI.search(ref)
    if d and not ref.startswith("http"):
        ref = "https://doi.org/" + d.group(1)  # open publishers expose citation_pdf_url on the landing page
    if not ref.startswith("http"):
        return
    if ref.lower().split("?")[0].endswith(".pdf"):
        yield ref
        return
    status, body = fetch(ref, browser=True)
    if status != 200:
        return
    for pat in (r'<meta[^>]+name="citation_pdf_url"[^>]+content="([^"]+)"',
                r'<meta[^>]+content="([^"]+)"[^>]+name="citation_pdf_url"'):
        mm = re.search(pat, body, re.I)
        if mm:
            yield urllib.parse.urljoin(ref, html.unescape(mm.group(1)))
            return
    for href in re.findall(r'href="([^"]+\.pdf)"', body, re.I):
        if "supplement" not in href.lower():
            yield urllib.parse.urljoin(ref, html.unescape(href))
            return


def cmd_download(a):
    """Save the first open PDF among the sources as '<year>. <title> (<venue>).pdf'."""
    # Default: .research/pdfs/ in the project (the current directory). --dir / --downloads only when the user names a place.
    folder = downloads_dir() if a.downloads else os.path.expanduser(a.dir) if a.dir else os.path.join(".research", "pdfs")
    folder = os.path.abspath(os.path.normpath(folder))
    os.makedirs(folder, exist_ok=True)
    # keep the full path under ~240 chars (Windows MAX_PATH is 260)
    name = paper_filename(a.year, a.title, a.venue, min(120, 240 - len(folder) - len(os.sep) - 4)) + ".pdf"
    path = os.path.join(folder, name)
    if os.path.exists(path):
        print("exists, skipped: " + path)
        if not os.path.exists(os.path.splitext(path)[0] + ".txt"):
            write_paper_meta(path, a, None)
        return
    tried = []
    for ref in a.sources:
        for url in pdf_candidates(ref):
            status, data = fetch_bytes(url)
            if status == 200 and data[:5] == b"%PDF-":
                with open(path, "wb") as f:
                    f.write(data)
                print("saved: %s · %.1f MB · from %s" % (path, len(data) / 1e6, url))
                write_paper_meta(path, a, url)
                return
            tried.append("%s (%s)" % (url, "not a PDF" if status == 200 else "HTTP %s" % status))
    die("no open PDF found — the paper may be paywalled. Tried: " + ("; ".join(tried) or "no PDF link in the sources given"))


def citation_who(authors):
    """'Kerbl et al.' — one author: 'Kerbl'; two: 'Kerbl and Kopanas' (same rule as /research-list-paper)."""
    last = [n.split()[-1] for n in authors if n.split()]
    return last[0] if len(last) == 1 else " and ".join(last) if len(last) == 2 else last[0] + " et al." if last else "?"


def citation_short(authors, venue, year):
    return "%s, %s %s" % (citation_who(authors), venue, year)


def citation_slide(authors, title, venue, year):
    """Slide-ready, as in /research-list-paper: 'Kerbl et al., <Title> (SIGGRAPH 2023)'."""
    return "%s, %s (%s %s)" % (citation_who(authors), title, venue, year)


def write_paper_meta(pdf_path, a, pdf_url):
    """'<same name>.txt' next to the PDF: citation, links, BibTeX with its source, abstract — for finding it again later.
    Missing pieces are written as '-' rather than failing the download."""
    src = [s.strip() for s in a.sources]
    arx_id = next((arxiv_of(s) for s in src if arxiv_of(s)), None)
    doi = next((DOI.search(s).group(1) for s in src
                if DOI.search(s) and not arxiv_of(s) and "10.48550" not in s), None)
    page = next((s for s in src if s.startswith("http") and not re.search(r"arxiv\.org|doi\.org", s)
                 and not s.lower().split("?")[0].endswith(".pdf")), None)
    arx = arxiv_entry(arx_id) if arx_id else arxiv_entry(title=a.title)
    if arx and norm(arx["title"]) != norm(a.title):
        arx = None
    arx_id = arx_id or (arx or {}).get("id")
    if arx_id:
        arx_id = re.sub(r"v\d+$", "", arx_id)
    doi = doi or (arx or {}).get("doi") or None
    cr = crossref(doi=doi) if doi else None
    authors = (cr or {}).get("authors") or (arx or {}).get("authors") or []
    bib_url, bib_kind, bib, _ = find_bibtex([r for r in (page, doi, arx_id) if r])

    links = [("Venue page", page), ("Project page", a.page), ("DOI", doi and "https://doi.org/" + doi),
             ("arXiv", arx_id and "https://arxiv.org/abs/" + arx_id), ("Code", a.code), ("PDF source", pdf_url)]
    out = [a.title, ", ".join(authors) or "-", "%s %s" % (a.venue, a.year), "",
           "== Citation ==",
           "Slide: " + citation_slide(authors, a.title, a.venue, a.year),
           "Short: " + citation_short(authors, a.venue, a.year),
           "Full:  %s. %s. %s, %s." % (", ".join(authors) or "?", a.title, a.venue, a.year), "",
           "== Links =="]
    out += ["%-13s %s" % (k + ":", v) for k, v in links if v]
    out += ["", "== BibTeX ==", "Source: %s — %s" % (bib_kind, bib_url) if bib else "Source: - (no BibTeX found)", bib or "-"]
    if arx and arx.get("abstract"):
        out += ["", "== Abstract (arXiv) ==", arx["abstract"]]
    out += ["", "Saved: %s · %s" % (time.strftime("%Y-%m-%d"), os.path.basename(pdf_path))]
    meta_path = os.path.splitext(pdf_path)[0] + ".txt"
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("meta: %s · bibtex from %s · %d authors" % (meta_path, bib_kind or "nowhere", len(authors)))
    rebuild_indexes(os.path.dirname(pdf_path))


INDEX, BIBFILE = "index.txt", "references.bib"


def read_paper_meta(path):
    """Parse a '<paper>.txt' written by write_paper_meta; None for any other .txt."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    if "== Citation ==" not in lines:
        return None
    sec, d = None, {"title": lines[0] if lines else "", "links": {}, "bib": []}
    for l in lines[3:]:
        m = re.fullmatch(r"== (.+?) ==", l)
        if m:
            sec = m.group(1)
        elif l.startswith("Saved:"):
            sec = None
        elif sec == "Citation" and l.startswith(("Slide:", "Short:")):
            d[l[:5].lower()] = l[6:].strip()
        elif sec == "Links" and ":" in l:
            k, v = l.split(":", 1)
            d["links"][k.strip()] = v.strip()
        elif sec == "BibTeX" and l.strip() not in ("", "-") and not l.startswith("Source:"):
            d["bib"].append(l)
    return d


def rebuild_indexes(folder):
    """index.txt (one line per paper) and references.bib (every BibTeX entry), rebuilt from the per-paper .txt files.
    The .txt files are the record; these two are generated — don't edit them by hand."""
    papers = []
    for f in sorted(os.listdir(folder)):
        # a paper record is '<name>.txt' with '<name>.pdf' beside it and a Citation section; other .txt files are ignored
        if f.endswith(".txt") and f != INDEX and os.path.isfile(os.path.join(folder, f[:-4] + ".pdf")):
            d = read_paper_meta(os.path.join(folder, f))
            if d:
                papers.append((f, d))
    if not papers:  # e.g. the last paper was deleted: drop the stale generated files
        gone = [n for n in (INDEX, BIBFILE) if is_generated(os.path.join(folder, n))]
        for n in gone:
            os.remove(os.path.join(folder, n))
        print("index: no paper records in %s%s" % (folder, " · removed " + ", ".join(gone) if gone else ""))
        return
    head = GEN_MARK + " from the per-paper .txt files — don't edit; re-run `researchtool.py index`."
    rows = [head, ""]
    bib = ["% " + head, ""]
    for f, d in papers:
        ln = d["links"]
        link = ln.get("Venue page") or ln.get("DOI") or ln.get("arXiv") or "-"
        cite = d.get("slide") or "%s, %s" % (d.get("short", "?"), d["title"])  # .txt files from before the Slide line
        rows.append("%s · %s" % (cite, link))
        rows.append("    " + os.path.splitext(f)[0] + ".pdf")
        if d["bib"]:
            bib += ["% " + os.path.splitext(f)[0]] + d["bib"] + [""]
    wrote = [n for n, text in ((INDEX, "\n".join(rows) + "\n"), (BIBFILE, "\n".join(bib).rstrip() + "\n"))
             if write_generated(os.path.join(folder, n), text)]
    if INDEX in wrote:
        print("index: %s · %d papers%s" % (os.path.join(folder, INDEX), len(papers),
                                           " (+ %s)" % BIBFILE if BIBFILE in wrote else ""))
    elif wrote:
        print("bib: %s · %d papers" % (os.path.join(folder, BIBFILE), len(papers)))


GEN_MARK = "Generated by researchtool.py"


def is_generated(path):
    """True if path exists and was written by rebuild_indexes (its first line carries the marker)."""
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8", errors="replace") as fh:
        return GEN_MARK in fh.readline()


def write_generated(path, text):
    """Write a generated file, but never overwrite a file of the same name that someone else wrote."""
    if os.path.exists(path) and not is_generated(path):
        print("WARNING: %s exists and was not generated by researchtool.py — left unchanged" % path)
        return False
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return True


def cmd_index(a):
    folder = downloads_dir() if a.downloads else os.path.expanduser(a.dir) if a.dir else os.path.join(".research", "pdfs")
    if not os.path.isdir(folder):
        die("no such folder: " + folder)
    rebuild_indexes(os.path.abspath(folder))


def cmd_fulltext(a):
    aid = arxiv_of(a.ref, version=True)
    if not aid:
        die("fulltext needs an arXiv id; for a local PDF read the file directly.")
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
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--n", type=int, default=10); s.add_argument("--since", type=int)
    s.add_argument("--sort", choices=("relevance", "cites"), default="relevance", help="cites: most-cited first")
    s = sub.add_parser("meta"); s.add_argument("ref")
    s = sub.add_parser("cites"); s.add_argument("ref"); s.add_argument("--n", type=int, default=10); s.add_argument("--since", type=int)
    s = sub.add_parser("page"); s.add_argument("url"); s.add_argument("--grep"); s.add_argument("--links", help="regex on link href or text")
    s = sub.add_parser("venue-url"); s.add_argument("title"); s.add_argument("conf", help="e.g. CVPR2024, ICCV2023")
    s = sub.add_parser("github"); s.add_argument("repo"); s.add_argument("--paper", action="append", default=[], help="title or arXiv id; repeatable"); s.add_argument("--page", help="project / venue page that should link the repo")
    s = sub.add_parser("bibtex"); s.add_argument("refs", nargs="+")
    s = sub.add_parser("download"); s.add_argument("sources", nargs="+", help="venue page URL, PDF URL, or arXiv id — best first")
    s.add_argument("--year", required=True); s.add_argument("--title", required=True); s.add_argument("--venue", required=True)
    g = s.add_mutually_exclusive_group(); g.add_argument("--dir"); g.add_argument("--downloads", action="store_true")
    s.add_argument("--code", help="verified official code repo, for the .txt"); s.add_argument("--page", help="verified project page, for the .txt")
    s = sub.add_parser("index")
    g = s.add_mutually_exclusive_group(); g.add_argument("--dir"); g.add_argument("--downloads", action="store_true")
    s = sub.add_parser("fulltext"); s.add_argument("ref"); s.add_argument("--out")
    a = ap.parse_args()
    try:
        {"search": cmd_search, "meta": cmd_meta, "cites": cmd_cites, "page": cmd_page, "venue-url": cmd_venue_url,
         "github": cmd_github, "bibtex": cmd_bibtex, "download": cmd_download, "index": cmd_index,
         "fulltext": cmd_fulltext}[a.cmd](a)
    except KeyboardInterrupt:
        die("interrupted")
    except Exception as e:  # anything unforeseen: one ERROR line, not a traceback
        die("%s: %s" % (type(e).__name__, e))


if __name__ == "__main__":
    main()
