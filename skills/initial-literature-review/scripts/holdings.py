#!/usr/bin/env python3
"""holdings.py -- which of the missing PDFs is the university actually licensed for?

The owner was opening Springer links one at a time and could not tell why some
worked and some did not. The cause is not the VPN: Springer eBooks are licensed
as collections, and a library typically holds some years and not others.

A Springer book-chapter DOI contains the book's ISBN --

    10.1007/978-3-031-57916-5_25  ->  978-3-031-57916-5

-- and the library publishes the ISBNs it subscribes to. So entitlement can be
checked offline, against the library's own list, instead of by clicking and
guessing. Journals work the same way through ISSN.

One limit, stated because it changes how the output should be read: the list is
a snapshot and the subscription is "AutoHoldings", which keeps adding current
content. A book newer than the snapshot can be readable while absent here. So
"licensed" is reliable and "not listed" means *probably* not, most safely for
older material -- which is where the question actually bites.

  python3 holdings.py --thread <t> --ebooks <xlsx> [<xlsx> ...] [--stale-from 2024]

Any sheet layout works: every cell is tried as an ISBN. Run missing_pdfs.py
first (it writes missing-pdfs.md), then this, then missing_pdfs.py again so it
routes the verified-unavailable ones to interlibrary loan.
"""
from __future__ import annotations

import argparse, collections, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c
from xlsx_read import rows as xlsx_rows

# 10.1007/978-3-031-57916-5_25 and the old 10.1007/3-540-48749-2_13
ISBN_IN_DOI = re.compile(r"10\.1007/((?:97[89][-\d]{10,17}|\d[-\dX]{8,16}))_", re.I)


def digits(s: str) -> str:
    return re.sub(r"[^0-9X]", "", (s or "").upper())


def isbn13(s: str) -> str:
    """ISBN-10 -> ISBN-13 so an old DOI can match a modern list entry."""
    d = digits(s)
    if len(d) == 13:
        return d
    if len(d) != 10:
        return ""
    core = "978" + d[:9]
    chk = (10 - sum(int(x) * (3 if i % 2 else 1) for i, x in enumerate(core)) % 10) % 10
    return core + str(chk)


def load_isbns(paths: list[Path]) -> set[str]:
    out: set[str] = set()
    for p in paths:
        import zipfile
        sheets = [n for n in zipfile.ZipFile(p).namelist() if "worksheets/sheet" in n]
        for sh in sheets:
            for r in xlsx_rows(str(p), sh):
                for cell in r:
                    v = isbn13(cell)
                    if len(v) == 13:
                        out.add(v)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--ebooks", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--stale-from", type=int, default=int(c.now_iso()[:4]) - 2,
                    help="publication year from which 'not listed' is no longer "
                         "trusted, because the list snapshot predates it "
                         "(default: two years ago)")
    a = ap.parse_args()

    held = load_isbns(a.ebooks)
    c.log(f"ISBNs the library lists: {len(held)}")

    rows = c.read_rows(a.thread / "candidates.csv")
    tier_a = c.in_scope(rows)
    src = a.thread / "missing-pdfs.md"
    if not src.exists():
        c.log(f"no {src.name} -- run missing_pdfs.py first")
        return 2
    txt = src.read_text()
    missing = set(re.findall(r"^\| `([^`]+)`", txt, re.M))
    springer = [r for r in tier_a
                if r["bibkey"] in missing and (r.get("doi") or "").startswith("10.1007/")]

    # The snapshot is demonstrably stale for new books: a 2027 chapter the owner
    # CAN open is absent from it. So "not listed" is strong evidence for old
    # material and weak evidence for new, and the output must not pretend
    # otherwise. STALE_FROM is where the list stops being trustworthy.
    STALE_FROM = a.stale_from

    def year(r) -> int:
        v = (r.get("year") or "").strip()
        return int(v) if v.isdigit() else 0

    yes, no, maybe, odd = [], [], [], []
    for r in springer:
        m = ISBN_IN_DOI.search(r.get("doi") or "")
        if not m:
            odd.append(r)
            continue
        if isbn13(m.group(1)) in held:
            yes.append(r)
        elif year(r) >= STALE_FROM:
            maybe.append(r)
        else:
            no.append(r)

    L: list[str] = []
    def say(s: str = "") -> None:
        print(s); L.append(s)

    say(f"# Springer: what {c.INSTITUTION} actually holds")
    say()
    say(f"Checked against the library's own list ({len(held)} ISBNs). A Springer "
        f"chapter DOI contains the book's ISBN, so this is an exact check, not a guess.")
    say()
    say(f"- **{len(yes)}** — on the list, should open via the institution network")
    say(f"- **{len(maybe)}** — not listed, but newer than the list itself "
        f"(subscriptions keep adding content), so worth trying")
    say(f"- **{len(no)}** — not listed and old enough for that to be reliable: "
        f"not available")
    if odd:
        say(f"- {len(odd)} — no ISBN could be read from the DOI")
    say()
    for label, group in (("Should work — on the list", yes),
                         ("Try it yourself — the list is too old for these", maybe),
                         ("Not available — request via interlibrary loan", no)):
        if not group:
            continue
        say(f"## {label} — {len(group)}")
        say()
        say("| key | year | title |")
        say("|---|---|---|")
        for r in sorted(group, key=lambda x: (x.get("year") or "")):
            t = (r.get("title") or "").replace("|", "\\|")[:66]
            say(f"| `{r['bibkey']}` | {r.get('year','')} | {t} |")
        say()
    say("*Caveat: the list is a snapshot and the subscription keeps adding content, "
        "so a book newer than the snapshot can be available although absent here. "
        "\"Should work\" is reliable; \"not listed\" is most reliable for older items.*")

    out = a.out or (a.thread / "springer-access.md")
    out.write_text("\n".join(L) + "\n")
    c.log(f"\n→ {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
