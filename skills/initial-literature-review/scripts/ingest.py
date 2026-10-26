#!/usr/bin/env python3
"""ingest.py -- put the accepted papers into Zotero and pin our citation key.

For every accepted row: add it to Zotero, write OUR citation key onto the
item, tag it by thread, and record whether a PDF actually attached.

On the citation key, because it is the part that surprises people: Zotero
holds an 8-character ITEM key (3QNXCRIJ) which is internal plumbing, and it
does NOT hold a citation key. Any bibliography exported from Zotero gets a key
invented at export time -- verified on 23 September, `get bibtex` returned
`Mir2023_3QNXCRIJ` even for an item whose citation key was pinned. So we write
our key on for visibility and searchability in the Zotero UI, we record the
bibkey <-> zotero_key pair, and `bib.py` writes the bibliography itself.
Never export the bibliography from Zotero.

Writes require authorisation once: `zotero-mcp authorize-local`, then
"Always Allow" in the Zotero dialog.

  python3 ingest.py --thread research/threads/my-topic
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c

ACCEPTED = {"1", "2"}
ITEM_KEY = re.compile(r"Item key: `([A-Z0-9]{8})`")
ALSO_KEY = re.compile(r"`([A-Z0-9]{8})`")


def zot(args: list[str], timeout: int = 120) -> dict:
    p = subprocess.run(["zotero-cli", "--json", *args], capture_output=True,
                       text=True, timeout=timeout)
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": {"message": (p.stderr or p.stdout)[:300]}}


SOFT_FAIL = ("not found on crossref", "could not be fetched", "no metadata")


def _attempt(args: list[str]) -> tuple[str | None, str, bool]:
    """Returns (item key, note, soft_failed).

    `add doi` answers ok:true even when it could not resolve the DOI -- it just
    says so in the text. Zenodo and arXiv DOIs are registered with DataCite, not
    Crossref, so this is the common case rather than an edge case, and treating
    ok:true as success silently loses the item. Measured 30 September: 167 of
    389 rows were affected before this was caught.
    """
    r = zot(args)
    if not r.get("ok"):
        return None, str((r.get("error") or {}).get("message", "failed"))[:140], True
    text = (r.get("data") or {}).get("text", "")
    m = ITEM_KEY.search(text) or ALSO_KEY.search(text)
    if m:
        return m.group(1), ("already in library" if "Already in library" in text
                            else "added"), False
    low = text.lower()
    return None, text.strip()[:120] or "no item key in reply", any(s in low for s in SOFT_FAIL) or True


def join_collection(key: str, collection: str) -> bool:
    """Put an EXISTING item into the collection.

    `add` only files a newly created item. When the item is already in the
    library it returns the key and silently ignores --collection, so a rebuilt
    collection stays empty while the CSV fills up with keys that look right.
    Seen on 4 October after the collection was emptied but the library kept
    every item.
    """
    r = zot(["collections", "manage", "--item-keys", key, "--add-to", collection])
    return bool(r.get("ok"))


def add_item(row: dict, collection: str, tags: str, attach: str) -> tuple[str | None, str]:
    """Add by the best identifier available, trying alternatives on soft failure.

    Never guesses. If no attempt yields an item key the row is reported as a
    failure, because a wrong bibkey <-> zotero_key pair is worse than a missing
    one: it silently points every downstream step at the wrong paper.
    """
    base = ["--collection", collection, "--tags", tags,
            "--if-exists", "file", "--create-collections", "--attach-mode", attach]
    attempts: list[list[str]] = []
    doi = (row.get("doi") or "").lower()
    urls: list[str] = []

    # A doi.org URL is routed back to the Crossref lookup, so DataCite DOIs have
    # to be turned into their NATIVE landing pages or they can never resolve.
    if m := re.match(r"10\.5281/zenodo\.(\d+)", doi):
        urls.append(f"https://zenodo.org/records/{m.group(1)}")
    if m := re.match(r"10\.48550/arxiv\.(.+)", doi):
        urls.append(f"https://arxiv.org/abs/{m.group(1)}")
    if row.get("arxiv"):
        urls.append(f"https://arxiv.org/abs/{row['arxiv']}")

    if doi and not doi.startswith(("10.5281/", "10.48550/")):
        attempts.append(["add", "doi", doi, *base])       # Crossref-registered
    for u in urls:
        attempts.append(["add", "url", u, *base])
    if doi and not urls:
        attempts.append(["add", "url", f"https://doi.org/{doi}", *base])
    ru = row.get("url") or ""
    if ru and ru not in urls and not ru.startswith("https://doi.org/"):
        attempts.append(["add", "url", ru, *base])
    if not attempts:
        return None, "no identifier"
    last = "no identifier"
    for args in attempts:
        key, note, soft = _attempt(args)
        if key:
            return key, note
        last = note
    return None, last

    # unreachable; kept for clarity of the original single-attempt shape
    if False:
        pass


def pin_key(item_key: str, bibkey: str) -> bool:
    r = zot(["batch", "--item-keys", item_key, "--set",
             json.dumps({"Citation Key": bibkey})])
    return bool(r.get("ok"))


def has_pdf(item_key: str) -> bool:
    """The test that matters is whether the text is readable, not whether an
    attachment row exists -- a linked URL counts as a child but cannot be read."""
    r = zot(["get", "children", item_key])
    if not r.get("ok"):
        return False
    kids = (r.get("data") or {}).get("items", [])
    if not any(k.get("itemType") == "attachment" for k in kids):
        return False
    t = zot(["get", "fulltext", item_key], timeout=180)
    return bool(t.get("ok")) and len((t.get("data") or {}).get("text") or "") > 500


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--collection", help="Zotero collection (default: thread folder name)")
    ap.add_argument("--attach-mode", default="auto", choices=["auto", "none", "required"])
    ap.add_argument("--limit", type=int, help="stop after N items (for a trial run)")
    ap.add_argument("--sleep", type=float, default=0.5, help="pause between items")
    ap.add_argument("--tier", default="A",
                    help="which tier to ingest when the thread has been tiered (default: A)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    thread_name = a.thread.resolve().name
    collection = a.collection or thread_name
    path = a.thread / "candidates.csv"
    rows = c.read_rows(path)
    todo = [r for r in rows if r.get("band") in ACCEPTED and not r.get("zotero_key")]
    # A thread that has been tiered ingests only the review proper. Tier B is
    # background: it is cited from the CSV when needed, never read in full, and
    # putting it in Zotero would bury the review in its own ancestry.
    if any(r.get("tier") for r in rows):
        todo = [r for r in todo if r.get("tier") == a.tier]
        c.log(f"thread is tiered — ingesting tier {a.tier} only")
    if not todo:
        c.log("nothing to ingest — no accepted rows without a Zotero key.")
        return 0
    if a.limit:
        todo = todo[:a.limit]

    c.log(f"{len(todo)} to ingest → collection '{collection}'")
    if a.dry_run:
        for r in todo[:15]:
            c.log(f"  {r['bibkey']:30s} {(r.get('doi') or r.get('arxiv') or 'NO ID'):34s} {r['title'][:44]}")
        c.log("(dry run — nothing written)")
        return 0

    tags = f"thread/{thread_name},status/to-read"
    added = pinned = with_pdf = 0
    failures, missing_pdf = [], []
    for i, r in enumerate(todo, 1):
        key, note = add_item(r, collection, tags, a.attach_mode)
        if not key:
            failures.append({"bibkey": r["bibkey"], "title": r["title"],
                             "doi": r.get("doi", ""), "error": note})
            c.log(f"  [{i}/{len(todo)}] FAIL {r['bibkey']}: {note}")
            continue
        r["zotero_key"] = key
        if note == "already in library":
            join_collection(key, collection)
        added += 1
        if pin_key(key, r["bibkey"]):
            pinned += 1
        if has_pdf(key):
            with_pdf += 1
        else:
            missing_pdf.append(r)
        c.log(f"  [{i}/{len(todo)}] {r['bibkey']:28s} {key}  {note}")
        # Checkpoint: Zotero has the item the moment add_item returns, so a run
        # that is interrupted must not leave the CSV claiming otherwise. The
        # same lesson cost a whole gather run earlier in this project.
        if i % 25 == 0:
            c.write_rows(path, rows)
        time.sleep(a.sleep)

    c.write_rows(path, rows)
    write_pdf_status(a.thread, todo, missing_pdf, failures)
    c.write_run(a.thread, "ingest", {"collection": collection, "attempted": len(todo),
                                     "added": added, "keys_pinned": pinned,
                                     "with_pdf": with_pdf,
                                     "missing_pdf": len(missing_pdf),
                                     "failures": failures})
    c.log(f"\nadded {added}/{len(todo)} · keys pinned {pinned} · with PDF {with_pdf} "
          f"· missing PDF {len(missing_pdf)} · failed {len(failures)}")
    c.log(f"Gate C: {a.thread / 'pdf-status.md'}")
    return 0


def write_pdf_status(thread: Path, attempted, missing, failures) -> None:
    lines = ["# PDF status — Gate C", "",
             f"*Generated {c.now_iso()}. This is the human step: the machine got what",
             "it could get for free, and what is listed below needs a browser, a login,",
             "or a licence.*", "",
             f"- attempted: **{len(attempted)}**",
             f"- missing a readable PDF: **{len(missing)}**",
             f"- failed to add at all: **{len(failures)}**", ""]
    if missing:
        lines += ["## Missing a readable PDF", "",
                  "Route, easiest first: an arXiv or IACR ePrint version if one exists · "
                  "LibKey Nomad or Unpaywall on the publisher page, then the Zotero "
                  "Connector to save it *with* the PDF · institutional licensed access · request it.",
                  "", "| citation key | year | title | DOI |", "|---|---|---|---|"]
        for r in missing:
            t = (r.get("title") or "").replace("|", "\\|")[:80]
            lines.append(f"| `{r['bibkey']}` | {r.get('year','')} | {t} | "
                         f"{r.get('doi','') or r.get('arxiv','')} |")
        lines.append("")
    if failures:
        lines += ["## Failed to add", "", "| citation key | error |", "|---|---|"]
        for f in failures:
            lines.append(f"| `{f['bibkey']}` | {f['error'][:90]} |")
        lines.append("")
    if not missing and not failures:
        lines.append("Everything attempted has a readable PDF. Nothing to do at this gate.")
    (thread / "pdf-status.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
