#!/usr/bin/env python3
"""attach_downloads.py -- attach PDFs the owner downloaded by hand to the right Zotero items.

Added 11 October 2026. Licensed PDFs (IEEE, ACM, Springer via institutional access) can
only be fetched in a browser, by the owner. They land in ~/Downloads with
publisher file names -- IEEE uses the title with underscores. This matches each
PDF to an in-scope row (tier A, or accepted if untiered) that is still missing its full text and attaches it.

Matching is by title similarity (file name vs. candidates.csv title), never by
order or by guess: a pair below --min score is reported, not attached. Browser
duplicates ("name (1).pdf") are skipped. Dry run by default; --apply attaches.

  python3 attach_downloads.py --thread <t> --since "2026-10-11 16:00"
  python3 attach_downloads.py --thread <t> --since "2026-10-11 16:00" --apply
"""
from __future__ import annotations

import argparse, difflib, json, os, re, subprocess, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c

WS = re.compile(r"[^a-z0-9]+")


def norm(s: str) -> str:
    return WS.sub(" ", c.ascii_fold(s).lower()).strip()


def pdf_title(p: Path) -> str:
    """A title for a PDF whose file name says nothing (Elsevier 1-s2.0-S…-main,
    MDPI electronics-15-02829). First the PDF's own metadata via Spotlight
    (macOS mdls); then, for Elsevier files, the PII resolved through the
    Elsevier API. Returns "" when neither works."""
    try:
        t = subprocess.run(["mdls", "-raw", "-name", "kMDItemTitle", str(p)],
                           capture_output=True, text=True, timeout=30).stdout.strip()
        if t and t != "(null)":
            return t
    except (OSError, subprocess.TimeoutExpired):
        pass
    m = re.match(r"1-s2\.0-(S[0-9X]+)-main", p.stem)
    if m and os.environ.get("ELSEVIER_API_KEY"):
        hdr = {"X-ELS-APIKey": os.environ["ELSEVIER_API_KEY"], "Accept": "application/json"}
        try:
            # The article endpoint is not entitled for us; Scopus search by PII is.
            r = c.get_json("https://api.elsevier.com/content/search/scopus",
                           {"query": f"PII({m.group(1)})", "field": "dc:title"},
                           headers=hdr, tries=2)
            e = ((r.get("search-results") or {}).get("entry") or [{}])[0]
            return e.get("dc:title") or ""
        except Exception:
            pass
    return ""


def has_pdf(key: str) -> bool:
    p = subprocess.run(["zotero-cli", "--json", "get", "fulltext", key],
                       capture_output=True, text=True, timeout=180)
    try:
        d = json.loads(p.stdout)
    except json.JSONDecodeError:
        return False
    return bool(d.get("ok")) and len((d.get("data") or {}).get("text") or "") > 500


def best_match(stem: str, todo: list, used: set):
    best, score = None, 0.0
    for r in todo:
        if r["bibkey"] in used:
            continue
        t = norm(r["title"])
        s = difflib.SequenceMatcher(None, stem, t[:len(stem) + 20]).ratio()
        if s > score:
            best, score = r, s
    return best, score


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--dir", type=Path, default=Path.home() / "Downloads")
    ap.add_argument("--since", required=True, help='only files modified after, "YYYY-MM-DD HH:MM"')
    ap.add_argument("--min", type=float, default=0.85, help="minimum title similarity")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    since = datetime.strptime(a.since, "%Y-%m-%d %H:%M").timestamp()
    pdfs = [p for p in a.dir.glob("*.pdf")
            if p.stat().st_mtime >= since and not re.search(r" \(\d+\)\.pdf$", p.name)]
    rows = [r for r in c.read_rows(a.thread / "candidates.csv")
            if r.get("zotero_key")]
    # only rows whose paper file was never written (= no full text at extraction time)
    papers = c.papers_dir(a.thread)
    todo = [r for r in rows if not (papers / f"{r['bibkey']}.md").exists()]
    c.log(f"{len(pdfs)} PDFs since {a.since} · {len(todo)} in-scope items still without full text")

    matched, unmatched, used = [], [], set()
    # ACM names files by the DOI suffix: 10.1145/3772363.3798851 -> 3772363.3798851.pdf
    # (techrxiv DOIs end ".../v1"; the file says "_v1")
    by_doi_suffix = {c.norm_doi(r.get("doi")).split("/", 1)[1].replace("/", "_"): r
                     for r in todo if "/" in c.norm_doi(r.get("doi"))}
    for p in sorted(pdfs):
        hit = by_doi_suffix.get(p.stem.lower())
        # SSRN names files ssrn-<abstract id>; the DOI is 10.2139/ssrn.<id>
        if not hit and (m := re.match(r"ssrn-(\d+)", p.stem)):
            hit = by_doi_suffix.get(f"ssrn.{m.group(1)}")
        if hit and hit["bibkey"] not in used:
            matched.append((p, hit, 1.0)); used.add(hit["bibkey"])
            continue
        stem = norm(p.stem.replace("_", " "))
        # Opaque publisher names: match on the PDF's own title instead.
        if re.match(r"^(1-s2\.0-|[A-Za-z]+-\d{2}-\d{5})", p.stem, re.I) or " - " in p.stem:
            stem = norm(pdf_title(p)) or stem
        best, score = best_match(stem, todo, used)
        # Any other opaque name (gqae018.pdf, journal codes): retry on the PDF's own title.
        if score < a.min:
            t = norm(pdf_title(p))
            if t and t != stem:
                b2, s2 = best_match(t, todo, used)
                if s2 > score:
                    best, score = b2, s2
        if best and score >= a.min:
            matched.append((p, best, score)); used.add(best["bibkey"])
        else:
            unmatched.append((p, best, score))

    for p, r, s in matched:
        c.log(f"  {s:.2f}  {r['bibkey']:30s} ← {p.name[:70]}")
    for p, r, s in unmatched:
        c.log(f"  NO MATCH ({s:.2f})  {p.name[:70]}" + (f"  [closest: {r['bibkey']}]" if r else ""))
    if not a.apply:
        c.log(f"\n{len(matched)} would attach, {len(unmatched)} unmatched (dry run — add --apply)")
        return 0

    ok, fail = 0, []
    for p, r, s in matched:
        res = subprocess.run(["zotero-cli", "--json", "attach", r["zotero_key"], "--file", str(p)],
                             capture_output=True, text=True, timeout=300)
        try:
            good = json.loads(res.stdout).get("ok")
        except json.JSONDecodeError:
            good = False
        if good:
            ok += 1
        else:
            fail.append(r["bibkey"])
    c.log(f"attached {ok}/{len(matched)}" + (f"; failed: {', '.join(fail)}" if fail else ""))
    c.write_run(a.thread, "attach_downloads", {"since": a.since, "pdfs": len(pdfs),
                "matched": len(matched), "attached": ok, "failed": fail,
                "unmatched": [p.name for p, _, _ in unmatched]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
