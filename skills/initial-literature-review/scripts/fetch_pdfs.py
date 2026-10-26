#!/usr/bin/env python3
"""fetch_pdfs.py -- retrieve the PDFs that are free but did not attach.

Zotero's add-by-identifier only fetches a PDF when it can find one easily, and
for several open repositories it cannot. Measured on the agent-identity thread:
of 183 items missing a readable PDF, **123 (67%) were freely available anyway**
-- 100 on Zenodo, 16 SSRN, 5 arXiv, 3 IACR ePrint. Only 42 genuinely needed a
subscription. So the biggest single win is not licensed access, it is asking
the open repositories properly.

Sources handled, all through public APIs or published URL patterns:
  Zenodo         api/records/<id>  ->  the PDF in its file list
  arXiv          arxiv.org/pdf/<id>
  IACR ePrint    eprint.iacr.org/<year>/<num>.pdf
  Unpaywall      api.unpaywall.org -> a legal open-access copy of a paywalled
                 paper. Measured: 33% of the licensed items in this thread have
                 one, usually an author or repository version.
  arXiv by title fallback -- many IEEE and ACM papers have an arXiv preprint
                 that Unpaywall does not link.

NOT handled, on purpose:
  SSRN           needs an interactive session; Gate C work
  IEEE/ACM/Springer/Elsevier  licensed -- use LibKey Nomad or the Zotero
                 Connector in a browser. We do not drive a paywall with
                 someone's credentials from a script.

  python3 fetch_pdfs.py --thread <thread>            # fetch and attach
  python3 fetch_pdfs.py --thread <thread> --dry-run  # report only
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c

PDF_MAGIC = b"%PDF"


def zot(args, timeout=180) -> dict:
    p = subprocess.run(["zotero-cli", "--json", *args], capture_output=True,
                       text=True, timeout=timeout)
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": {"message": (p.stderr or p.stdout)[:200]}}


def readable(item_key: str) -> bool:
    """Does this item have a real PDF file attached?

    Do NOT ask `get fulltext` -- Zotero indexes attachments asynchronously, so
    a PDF attached a second ago returns only its metadata header. Using that as
    the test made every run re-download the same files and report them as
    still missing. Ask the filesystem instead: the attachment either exists or
    it does not.
    """
    r = zot(["get", "children", item_key])
    if not r.get("ok"):
        return False
    for kid in ((r.get("data") or {}).get("items") or []):
        if kid.get("itemType") != "attachment":
            continue
        pr = zot(["path", kid["key"]])
        txt = ((pr.get("data") or {}).get("text") or "")
        if "application/pdf" not in txt:
            continue
        m = re.search(r"Local path: `([^`]+)`", txt)
        if m and Path(m.group(1)).exists() and Path(m.group(1)).stat().st_size > 20_000:
            return True
    return False


def zenodo_pdf(doi: str) -> str | None:
    rid = doi.rsplit(".", 1)[-1]
    try:
        d = c.get_json(f"https://zenodo.org/api/records/{rid}")
    except Exception:
        return None
    files = d.get("files") or []
    # Prefer a declared PDF; fall back to anything whose name hints at one,
    # because Zenodo filenames are not reliably suffixed.
    for f in files:
        if (f.get("mimetype") or "").lower() == "application/pdf":
            return (f.get("links") or {}).get("self")
    for f in files:
        k = (f.get("key") or "").lower()
        if k.endswith(".pdf") or "pdf" in k:
            return (f.get("links") or {}).get("self")
    return None


SKIPPED_VERSIONS: dict[str, int] = {}


def unpaywall_pdf(doi: str, allow_accepted: bool) -> str | None:
    """A legal open-access copy -- but only the right VERSION of the paper.

    Unpaywall labels each copy: publishedVersion (the version of record),
    acceptedVersion (peer-reviewed author manuscript) or submittedVersion
    (a preprint). Attaching a preprint of a paper that was later published is
    wrong for a literature review: you would read one text and cite another,
    and the two can differ in exactly the claims you quote.

    Default: version of record only. --allow-accepted additionally permits the
    peer-reviewed accepted manuscript, which is the same content as the
    published paper but not the publisher's typeset copy.
    """
    try:
        d = c.get_json(f"https://api.unpaywall.org/v2/{doi}",
                       {"email": c.MAILTO}, tries=2)
    except Exception:            # HttpError, HostUnavailable, timeouts -- all
        return None              # just mean "no answer", never "stop the run"
    wanted = {"publishedVersion"} | ({"acceptedVersion"} if allow_accepted else set())
    for loc in [d.get("best_oa_location")] + (d.get("oa_locations") or []):
        if not loc:
            continue
        ver = loc.get("version") or "unknown"
        u = loc.get("url_for_pdf") or ""
        if not u:
            continue
        if ver in wanted:
            return u
        SKIPPED_VERSIONS[ver] = SKIPPED_VERSIONS.get(ver, 0) + 1
    return None


# arxiv_by_title() was removed on 3 October. Its whole purpose was finding an
# arXiv preprint of a paper published elsewhere -- which is precisely the thing
# we must not attach. Where arXiv IS the venue of record, the direct arXiv path
# below already handles it.


def candidate_urls(row: dict, allow_accepted: bool) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    doi = (row.get("doi") or "").lower()
    if doi.startswith("10.5281/zenodo."):
        if u := zenodo_pdf(doi):
            out.append(("zenodo", u))
    arx = row.get("arxiv") or ""
    if not arx and doi.startswith("10.48550/arxiv."):
        arx = doi.split("arxiv.", 1)[1]
    if arx:
        out.append(("arxiv", f"https://arxiv.org/pdf/{arx}"))
    if m := re.search(r"eprint\.iacr\.org/(\d{4})/(\d+)", row.get("url") or ""):
        out.append(("eprint", f"https://eprint.iacr.org/{m.group(1)}/{m.group(2)}.pdf"))
    if doi and not out:
        if u := unpaywall_pdf(doi, allow_accepted):
            out.append(("unpaywall", u))
    return out


def download(url: str, dest: Path) -> bool:
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": c.UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
    except Exception:
        return False
    if not data.startswith(PDF_MAGIC) or len(data) < 20_000:
        return False            # an error page, or a stub
    dest.write_bytes(data)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--sleep", type=float, default=0.5)
    ap.add_argument("--allow-accepted", action="store_true",
                    help="also accept the peer-reviewed accepted manuscript, "
                         "not only the publisher's version of record")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = c.read_rows(a.thread / "candidates.csv")
    todo = [r for r in rows if r.get("band") in ("1", "2") and r.get("zotero_key")]
    c.log(f"checking {len(todo)} ingested papers for a readable PDF…")

    missing = [r for r in todo if not readable(r["zotero_key"])]
    c.log(f"{len(missing)} without one\n")
    deferred: list[dict] = []
    if a.limit:
        # Anything we do not attempt is still missing. Leaving it out of
        # pdf-status.md would quietly shrink the Gate C list and hide work.
        missing, deferred = missing[:a.limit], missing[a.limit:]

    tmp = Path(tempfile.mkdtemp(prefix="ilr-pdf-"))
    got, none_found, attach_failed, by_source = 0, 0, 0, {}
    # A URL that did not yield a PDF is NOT the same as having no source: an
    # open-access link very often points at a landing page. Those links are
    # still useful to a human, so carry them into the manual list instead of
    # dropping them silently -- which is what made the totals not add up.
    download_failed = would_try = 0
    still: list[dict] = []

    for i, r in enumerate(missing, 1):
        try:
            urls = candidate_urls(r, a.allow_accepted)
        except Exception as e:
            c.log(f"  [{i}/{len(missing)}] lookup failed {r['bibkey']}: {type(e).__name__}")
            urls = []
        if not urls:
            none_found += 1; still.append(r); continue
        done = False
        for src, url in urls:
            if a.dry_run:
                c.log(f"  [{i}/{len(missing)}] would try {src}: {r['bibkey']}")
                by_source[src] = by_source.get(src, 0) + 1
                would_try += 1
                done = True
                break
            f = tmp / f"{r['bibkey']}.pdf"
            if not download(url, f):
                continue
            res = zot(["attach", r["zotero_key"], "--file", str(f),
                       "--filename", f"{r['bibkey']}.pdf"])
            if res.get("ok"):
                got += 1
                by_source[src] = by_source.get(src, 0) + 1
                c.log(f"  [{i}/{len(missing)}] {r['bibkey']:30s} <- {src}")
                done = True
                break
            attach_failed += 1
        if not done:
            if urls:
                download_failed += 1
                r["_links"] = "; ".join(u for _, u in urls)
            still.append(r)
        time.sleep(a.sleep)

    verb = f"would attach {would_try}" if a.dry_run else f"attached {got}"
    c.log(f"\n{verb} · no free source {none_found} · "
          f"link found but not a PDF {download_failed} · attach failed {attach_failed}")
    assert got + would_try + none_found + download_failed + attach_failed == len(missing), \
        "the counts must account for every paper"
    for s, n in sorted(by_source.items(), key=lambda x: -x[1]):
        c.log(f"  {s:10s} {n}")
    if SKIPPED_VERSIONS:
        c.log("\nopen copies REFUSED because of their version:")
        for v, n in sorted(SKIPPED_VERSIONS.items(), key=lambda x: -x[1]):
            c.log(f"  {v:20s} {n}")
        if "acceptedVersion" in SKIPPED_VERSIONS and not a.allow_accepted:
            c.log("  (acceptedVersion is peer-reviewed, just not typeset --")
            c.log("   rerun with --allow-accepted to take those too)")
    if a.dry_run:
        c.log("(dry run — nothing attached)")
        return 0

    write_remaining(a.thread, still + deferred)
    c.write_run(a.thread, "fetch-pdfs", {"checked": len(todo), "missing": len(missing),
                                         "attached": got, "by_source": by_source,
                                         "no_free_source": none_found,
                                         "attach_failed": attach_failed,
                                         "download_failed": download_failed,
                                         "still_missing": len(still) + len(deferred),
                                         "not_attempted_this_run": len(deferred)})
    c.log(f"Gate C remainder: {a.thread / 'pdf-status.md'}")
    return 0


def write_remaining(thread: Path, still: list[dict]) -> None:
    def kind(r):
        d = (r.get("doi") or "").lower()
        if "ssrn" in (r.get("venue") or "").lower() or d.startswith("10.2139"):
            return "SSRN — needs an interactive session"
        if d.startswith("10.1109"): return "IEEE — licensed, use LibKey/Connector"
        if d.startswith("10.1145"): return "ACM — licensed, use LibKey/Connector"
        if d.startswith(("10.1007", "10.1016", "10.1002", "10.3390")):
            return "Springer/Elsevier/Wiley/MDPI — licensed"
        if not r.get("doi") and not r.get("arxiv"): return "no identifier"
        return "other"
    groups: dict[str, list[dict]] = {}
    for r in still:
        groups.setdefault(kind(r), []).append(r)
    L = ["# PDF status — Gate C", "",
         f"*Regenerated {c.now_iso()} after fetch_pdfs.py. What remains needs a",
         "browser, a login, or a licence — none of which a script should drive.*", "",
         f"- still missing: **{len(still)}**", ""]
    for g, items in sorted(groups.items(), key=lambda x: -len(x[1])):
        L += [f"## {g} ({len(items)})", "", "| citation key | year | title | id |", "|---|---|---|---|"]
        for r in items:
            oa = f" · [OA kopija]({r['_links'].split(';')[0].strip()})" if r.get("_links") else ""
            L.append(f"| `{r['bibkey']}` | {r.get('year','')} | "
                     f"{(r.get('title') or '')[:70].replace('|','\\|')} | "
                     f"{r.get('doi') or r.get('arxiv') or '—'}{oa} |")
        L.append("")
    (thread / "pdf-status.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
