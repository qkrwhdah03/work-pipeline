---
name: research-sources
description: Source and verification rules for the research pipeline — which venues count as trusted, how to judge arXiv-only papers, how to verify a paper's title, venue, year, links and code before citing it, and which lookup services to use. Read this before running /research-list-paper or /research-summary-paper. Not for general web research.
user-invocable: false
---

# Research Sources & Verification

The one rule that overrides everything else: **never present a paper, venue, year, link, code repo or number you have not confirmed from a fetched source.** A short, fully verified answer beats a long one with a single invented entry. If something can't be confirmed, leave it out or mark it plainly as unconfirmed — never fill the gap from memory.

## Trusted venues

Prefer peer-reviewed papers from established venues. Use this tiering to rank and filter.

| Tier | Area | Venues |
| --- | --- | --- |
| 1 | Computer vision | CVPR, ICCV, ECCV |
| 1 | Graphics | SIGGRAPH, SIGGRAPH Asia, ACM TOG (Transactions on Graphics) |
| 1 | Machine learning | NeurIPS, ICML, ICLR |
| 1 | Journals | IEEE TPAMI, IJCV, IEEE TVCG, JMLR |
| 2 | Vision / graphics | WACV, BMVC, 3DV, Eurographics, Computer Graphics Forum, IEEE TIP |
| 2 | ML / AI | AAAI, IJCAI, AISTATS, UAI, TMLR |
| 1 | Robotics | RSS, CoRL, ICRA, IEEE T-RO |
| 2 | Robotics | IROS, IEEE RA-L |

For topics outside these areas, use that field's flagship venues the same way (e.g. ACL / EMNLP / NAACL for NLP; CHI for HCI) and say which ones you treated as tier 1.

- **Workshop papers are not main-conference papers.** Label them `(workshop)`.
- **Findings / short / demo tracks** are labeled as such, not as the main venue.
- **An accepted paper is cited by its venue, not its arXiv ID.** Many papers appear on arXiv first; always check whether a later published version exists and cite that venue and year.
- **Journal papers presented at a conference** (e.g. ACM TOG papers presented at SIGGRAPH): cite the journal with volume and issue, and add the conference in parentheses only if you confirmed it — `ACM TOG 42(4) (SIGGRAPH 2023)`.

## arXiv-only papers

Include an arXiv-only paper only when there is a concrete reason to trust it, and **state the reason in the entry** (one short phrase). Acceptable reasons, strongest first:

1. **Adoption** — widely cited for its age, or clearly used as a baseline by later tier-1 papers.
2. **Authors** — senior authors with a track record of tier-1 papers in this area (check their publication list or citation profile), or a well-known research lab.
3. **Recency** — very recent (last ~6 months) work that already defines a direction, from authors meeting reason 2.

If none apply, leave it out. Never include an arXiv paper just because it matches the keywords.

## Influence

- Judge citations **relative to age**: 300 citations in one year beats 600 in eight.
- "Key paper" means one of: it introduced the problem setting or method family, it is the standard baseline others compare against, or it changed the direction of the field. Say which.
- Citation counts differ between services; when you show one, name the source (e.g. `~1.2k citations, OpenAlex`).

## Verifying a paper

Confirm from fetched sources — not from search-result snippets alone, and never from memory. URLs you build from a known pattern (e.g. a CVF Open Access URL) are fine **if fetching them confirms the paper**.

There are two levels:

**Full check — every paper that gets its own entry** (each paper in a list; the paper being analyzed).

| Field | Confirm on |
| --- | --- |
| Exact title, authors | the paper's own page (venue page, arXiv abs) |
| Venue + year | the venue's own record — proceedings page (CVF Open Access, PMLR, NeurIPS / ICLR virtual site, OpenReview decision), or the DOI record (Crossref). An arXiv `journal_ref` / comment or an OpenAlex venue counts only when a second source agrees. |
| Paper link | the link opens and shows this paper — or, if that site blocks automated access, you took the URL from an official record (venue site, DOI record) |
| Code link | see below |
| BibTeX link | a page that shows the BibTeX — the venue's paper page (CVF, PMLR) or a `.bib` / Crossref / arXiv BibTeX URL (`researchtool.py bibtex`); otherwise `—` |

**Light check — papers only mentioned in passing** (e.g. follow-up work in a "big picture" section): one metadata record (OpenAlex, Crossref, Semantic Scholar or arXiv) for title, venue and year is enough.

**Accessible link, in this order:** open-access venue page (CVF Open Access, OpenReview, PMLR, proceedings.neurips.cc) → arXiv abs page → DOI. Mark a DOI `(paywalled)` only if you confirmed it is.

**Code link** — only an **official** repository. It counts as official when it's linked from the paper, its project page or its arXiv abstract — or, if those can't be reached, when the repo is owned by an author or their lab **and** its README points back to this paper. Confirm the repo exists (GitHub API). Whether a README uses the word "official" doesn't decide anything — many official repos never say it. Write `—` when there is no official code. If you list a well-known unofficial implementation, mark it `(unofficial)`.

**Record what you couldn't confirm.** If a detail rests on a weaker source or couldn't be checked (a dead project page, a venue page behind a bot wall), say so in the output's source note rather than silently dropping or asserting it.

## Script

`scripts/researchtool.py` (Python 3, standard library only) does the lookups below and prints only what you need. Use it instead of writing requests by hand — run it as `python3 .claude/skills/research-sources/scripts/researchtool.py <command>` (on Windows: `python …` — there `python3` is usually a Microsoft Store stub that doesn't run).

| Command | Gives you |
| --- | --- |
| `search "<query>" [--n 10] [--since YEAR]` | candidates from OpenAlex, one line each: year · venue · citations · title · DOI · arXiv id |
| `meta <arXiv id \| DOI \| "title">` | arXiv (authors, comment, journal_ref), Crossref (venue, volume, year), OpenAlex (venue, citations, open-access URL), and the **exact** abstract — the same published record whichever id you start from |
| `cites <arXiv id \| DOI> [--n 10] [--since YEAR]` | the most-cited works citing it |
| `page <url> [--grep REGEX] [--links REGEX]` | fetches as a browser (gets past CVF's block): page title, CVF paper title, GitHub links on the page, matching lines / links |
| `venue-url "<title>" <CVPR2024 \| ICCV2023 \| WACV2024>` | the paper's CVF Open Access page, found from the conference listing — CVF URLs can't be guessed reliably |
| `github <owner/repo> --paper "<title>" --paper <arXiv id> [--page <project page>]` | repo exists, owner, stars, whether the README names the paper, and whether the project page links the repo |
| `bibtex <venue page URL> [DOI] [arXiv id]` | the first link that shows the BibTeX: venue page (CVF, PMLR, NeurIPS `.bib`) → Crossref by DOI → arXiv |
| `fulltext <arXiv id> [--out FILE]` | arXiv HTML → text file (equations kept) + outline with line numbers and table / figure captions |
| `download <venue page \| PDF URL \| DOI \| arXiv id>... --year Y --title T --venue V` | saves the first open PDF among the sources to the Downloads folder as `Y. T (V).pdf`; checks it is a real PDF; skips existing files |

It exits with one `ERROR: …` line when a lookup fails; then fall back to the services below or WebSearch / WebFetch.

## Lookup services

Use web search to discover candidates, then these to verify. The script already covers them; call them directly only when it can't. All work without a key; respect rate limits and back off on HTTP 429 instead of hammering.

| Service | Use for | Endpoint |
| --- | --- | --- |
| arXiv API | arXiv metadata, versions, comments like "Accepted to CVPR 2024" | `https://export.arxiv.org/api/query?search_query=ti:"<title>"` or `?id_list=<id>` |
| arXiv HTML | full text without PDF parsing | `https://arxiv.org/html/<id>` (not every paper has it) |
| Crossref | DOI, journal / proceedings, year | `https://api.crossref.org/works?query.bibliographic=<title>&rows=3` |
| OpenAlex | venue, year, citation count, open-access URL, citing works | `https://api.openalex.org/works?search=<title>&per-page=3` |
| Semantic Scholar | venue, citations, references, author profiles | `https://api.semanticscholar.org/graph/v1/paper/search?query=<title>&fields=title,venue,year,citationCount,externalIds,openAccessPdf` — often rate-limited without a key |
| Venue sites | final venue confirmation | `openaccess.thecvf.com`, `proceedings.mlr.press`, `proceedings.neurips.cc`, `iclr.cc/virtual/<year>/…`, `neurips.cc/virtual/<year>/…`, `openreview.net` |
| GitHub | confirm a code repo exists | `https://api.github.com/repos/<owner>/<repo>` |

**How to fetch** — many academic sites block automated clients:

- **CVF Open Access, ACM DL, IEEE Xplore** often return 403 to WebFetch. Use `curl -sL -A "Mozilla/5.0"` instead. ACM DL and IEEE may still refuse; fall back to the DOI record.
- **OpenReview** (site and API) is usually behind a bot challenge. Confirm ICLR / NeurIPS papers on the conference's virtual site (`iclr.cc/virtual/…`, `neurips.cc/virtual/…`), which also links the OpenReview forum.
- **Crossref** does not index ICLR or NeurIPS (no DOIs) — use the virtual sites or OpenAlex for those.
- **DBLP** is behind a bot challenge; don't rely on it.
- **Exact text** (abstracts, numbers): fetch with curl and parse the XML / HTML yourself. WebFetch returns a paraphrase, which is not good enough to quote or copy numbers from.

If the environment has `SEMANTIC_SCHOLAR_API_KEY` or `OPENALEX_API_KEY` set, pass it (`x-api-key` header / `api_key=` parameter). Never sign up for keys or send the user's email to any service on their behalf.

## Separating the paper from your judgment

Whenever you describe a paper, keep two voices apart:

- **What the paper says** — attributed: "The authors claim …", "Table 2 reports …". Numbers are copied exactly, with the table / figure / section they come from. Metric and benchmark names (PSNR, SSIM, …) stay as published.
- **Your assessment** — clearly labeled as yours. Criticism must point to something specific (a missing baseline, an untested assumption, a metric that doesn't measure the claim), not general doubt.
