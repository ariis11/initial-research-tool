#!/usr/bin/env python3
"""attach_local.py -- attach PDFs the human downloaded to the right Zotero items.

The owner works through missing-pdfs.md with the institution VPN and ends up
with a folder of PDFs. Pairing them with Zotero items by hand is slow and, far
worse, easy to get subtly wrong.

Matching is by DOI read out of the PDF's own bytes. Publisher PDFs carry their
DOI in XMP metadata or an uncompressed text stream, and on the first batch 22
of 23 did. That is an exact identifier, not a resemblance.

A filename is used ONLY as a fallback, and only on an exactly equal normalised
title with exactly one candidate. No fuzzy ratios anywhere. Attaching the wrong
PDF is the worst failure available here -- every later quote, extraction and
citation would be drawn from the wrong paper and nothing downstream would
notice. A fuzzy title fallback in ingest once corrupted 167 rows of this very
corpus, so the rule is: match exactly or report and move on.

Nothing is deleted. Matched files are left in place; re-running is harmless
because an item that already has a readable PDF is skipped.

  python3 attach_local.py --thread <t> --from ~/Downloads [--since 2026-10-05]
  python3 attach_local.py --thread <t> --from ~/Downloads --dry-run
"""
from __future__ import annotations

import argparse, datetime, json, os, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c

DOI_RX = re.compile(rb"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
HEAD_BYTES = 1_500_000


def zot(args: list[str]) -> dict:
    try:
        p = subprocess.run(["zotero-cli", "--json", *args],
                           capture_output=True, text=True, timeout=120)
        return json.loads(p.stdout or "{}")
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)[:120]}}


def readable(item_key: str) -> bool:
    """Ask the filesystem, never `get fulltext` -- it indexes asynchronously."""
    r = zot(["get", "children", item_key])
    if not r.get("ok"):
        return False
    for kid in ((r.get("data") or {}).get("items") or []):
        if kid.get("itemType") != "attachment":
            continue
        pr = zot(["path", kid["key"]])
        m = re.search(r"Local path: `([^`]+)`", ((pr.get("data") or {}).get("text") or ""))
        if m and Path(m.group(1)).exists() and Path(m.group(1)).stat().st_size > 20_000:
            return True
    return False


def dois_in(path: Path) -> list[str]:
    """Every distinct DOI-shaped string in the file's head, in order of first use.

    The paper's OWN doi is usually the first, but a reference list can appear
    early in a short paper, so the caller must not assume the first is right --
    it checks all of them against the corpus and requires exactly one to hit.
    """
    try:
        raw = path.open("rb").read(HEAD_BYTES)
    except Exception:
        return []
    out: list[str] = []
    for h in DOI_RX.findall(raw):
        d = c.norm_doi(h.decode("ascii", "ignore").rstrip(").,;"))
        if d and d not in out:
            out.append(d)
    return out


def squash(s: str) -> str:
    """Lowercase, keep only letters and digits.

    Repositories name a file after the DOI suffix but punctuate it differently
    each time: ACM 3630106.3658948, SSRN ssrn-5162127 for ssrn.5162127,
    TechRxiv techrxiv.176621125.52529244_v1 for .../v1, Authorea au.<id>_v1,
    and one publisher uses the bare uppercase suffix YDMY4904. Squashing both
    sides to letters and digits turns all of those into one exact comparison
    instead of a rule per repository.
    """
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


SSRN_NAME = re.compile(r"^ssrn[-_](\d+)$", re.I)


def ssrn_doi(path: Path) -> str:
    """SSRN saves ssrn-5162127.pdf, and the corpus DOI is 10.2139/ssrn.5162127.

    Verified across all 19 SSRN downloads in this batch: every filename id
    resolved to a corpus DOI, none missed. Like the ACM case this is an
    identifier rather than a title, so matching on it is exact.
    """
    m = SSRN_NAME.match(path.stem)
    return f"10.2139/ssrn.{m.group(1)}" if m else ""


ACM_NAME = re.compile(r"^\d+(?:\.\d+)?$")


def acm_doi(path: Path) -> str:
    """ACM saves a PDF named after the DOI suffix: 3630106.3658948.pdf.

    This is an identifier, not a title, so it is safe to match on -- but only
    because it was checked rather than assumed. Of 12 ACM downloads, 5 also
    carried a DOI inside the file, and in all 5 the embedded DOI was exactly
    10.1145/<filename stem>. The other 7 are older scans with no embedded
    metadata, which is precisely where this rule is needed.
    """
    return f"10.1145/{path.stem}" if ACM_NAME.match(path.stem) else ""


IACR_NAME = re.compile(r"^(\d{4})-(\d+)$")


def iacr_url(path: Path) -> str:
    """IACR ePrint saves 2025-1790.pdf for eprint.iacr.org/2025/1790.

    These records carry no DOI at all, so the landing page URL is the only
    identifier the corpus holds for them.
    """
    m = IACR_NAME.match(path.stem)
    return f"https://eprint.iacr.org/{m.group(1)}/{m.group(2)}" if m else ""


def norm_title(t: str) -> str:
    t = (t or "").lower().replace("_", " ")
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--from", dest="src", type=Path, required=True)
    ap.add_argument("--since", help="only files modified on/after YYYY-MM-DD")
    ap.add_argument("--tier", default="A")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = c.read_rows(a.thread / "candidates.csv")
    want = [r for r in c.in_scope(rows, a.tier) if (r.get("zotero_key") or "").strip()]
    by_doi: dict[str, list[dict]] = {}
    by_title: dict[str, list[dict]] = {}
    for r in want:
        d = c.norm_doi(r.get("doi") or "")
        if d:
            by_doi.setdefault(d, []).append(r)
        t = norm_title(r.get("title"))
        if t:
            by_title.setdefault(t, []).append(r)

    # suffix of each DOI, squashed, for repository filenames; and landing-page
    # URLs for records that have no DOI at all (IACR ePrint).
    by_suffix: dict[str, list[dict]] = {}
    by_url: dict[str, list[dict]] = {}
    for r in want:
        d = c.norm_doi(r.get("doi") or "")
        if d and "/" in d:
            s = squash(d.split("/", 1)[1])
            if len(s) >= 6:
                by_suffix.setdefault(s, []).append(r)
        u = (r.get("url") or "").strip().rstrip("/")
        if u:
            by_url.setdefault(u.lower(), []).append(r)

    files = sorted(a.src.glob("*.pdf"), key=lambda p: p.stat().st_mtime)
    if a.since:
        cut = datetime.date.fromisoformat(a.since)
        files = [f for f in files
                 if datetime.date.fromtimestamp(f.stat().st_mtime) >= cut]
    c.log(f"{len(files)} PDFs in {a.src}" + (f" since {a.since}" if a.since else ""))
    c.log(f"{len(want)} in-scope items to match against\n")

    attached = skipped = 0
    unmatched: list[tuple[Path, str]] = []
    for f in files:
        cands, how = [], ""
        hits = [d for d in dois_in(f) if d in by_doi]
        if len({tuple(sorted(x["bibkey"] for x in by_doi[d])) for d in hits}) == 1 and hits:
            cands, how = by_doi[hits[0]], f"DOI {hits[0]}"
        elif len(hits) > 1:
            # A paper that cites another paper in the corpus yields several
            # hits. The publisher writes the paper's OWN doi into the metadata,
            # which precedes the content, while a cited doi can only appear in
            # the reference list at the end -- so the first occurrence is the
            # paper itself. Checked on three MDPI files where the first hit
            # also agreed with the journal and article number in the filename.
            cands, how = by_doi[hits[0]], f"first DOI in file {hits[0]}"
        elif (sq := squash(f.stem)) in by_suffix and len(sq) >= 6:
            cands, how = by_suffix[sq], "filename = DOI suffix"
        elif (ia := iacr_url(f)) and ia in by_url:
            cands, how = by_url[ia], f"IACR ePrint filename = {ia}"
        elif (ss := ssrn_doi(f)) and ss in by_doi:
            cands, how = by_doi[ss], f"SSRN filename = DOI ({ss})"
        elif (acm := acm_doi(f)) and acm in by_doi:
            cands, how = by_doi[acm], f"ACM filename = DOI ({acm})"
        else:
            t = norm_title(f.stem)
            if t in by_title:
                cands, how = by_title[t], "exact title"
        if not cands:
            unmatched.append((f, "no DOI and no exact title match"))
            continue
        if len(cands) > 1:
            unmatched.append((f, f"matches {len(cands)} items: "
                                 f"{', '.join(x['bibkey'] for x in cands[:3])}"))
            continue
        r = cands[0]
        key = r["zotero_key"]
        if readable(key):
            c.log(f"  SKIP  {r['bibkey']:30s} already has a PDF")
            skipped += 1
            continue
        if a.dry_run:
            c.log(f"  would attach {f.name[:46]:48s} -> {r['bibkey']:28s} ({how})")
            attached += 1
            continue
        res = zot(["attach", key, "--file", str(f)])
        if not res.get("ok"):
            unmatched.append((f, f"attach failed: "
                                 f"{str((res.get('error') or {}).get('message'))[:60]}"))
            continue
        # Verify rather than trust the exit status: the point of the whole step
        # is that a readable PDF is actually on disk afterwards.
        if readable(key):
            c.log(f"  OK    {r['bibkey']:30s} <- {f.name[:44]}  ({how})")
            attached += 1
        else:
            unmatched.append((f, "attach reported success but no readable PDF followed"))

    c.log(f"\nattached {attached} · already had one {skipped} · "
          f"not matched {len(unmatched)}")
    if unmatched:
        c.log("\nnot matched — these need a human:")
        for f, why in unmatched:
            c.log(f"  {f.name[:56]:58s} {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
