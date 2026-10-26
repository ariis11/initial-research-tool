#!/usr/bin/env python3
"""missing_pdfs.py -- the list a human works through, grouped by where to go.

fetch_pdfs.py takes everything the open repositories will give. What is left
needs a licence, and the owner fetches it through the institution VPN. A flat
table of DOIs is a bad way to do that: the same publisher is visited over and
over, and nothing says which link actually opens the PDF.

So this groups what remains BY PUBLISHER, resolved from the DOI prefix, and
gives a direct link per paper. One login, one site, one batch.

Truth comes from the filesystem, never from `get fulltext` -- Zotero indexes
asynchronously and the index lies for minutes after an attachment lands. That
mistake once overstated coverage by seven points.

  python3 missing_pdfs.py --thread <t>
"""
from __future__ import annotations

import argparse, collections, json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c

# DOI prefix -> (publisher, route, note). The route is what the owner should DO,
# because grouping by publisher alone still leaves them deciding each time
# whether to start the VPN, and clicking links that cannot work.
#   open = free, a browser is enough
#   vpn  = licensed, needs the institution network
#   ill  = verified not licensed, interlibrary loan, do not click
PREFIX = {
    "10.1109": ("IEEE Xplore", "vpn", ""),
    "10.1007": ("Springer / LNCS", "vpn", "run holdings.py to check against the library's subscription list"),
    "10.1016": ("Elsevier ScienceDirect", "vpn", ""),
    "10.1145": ("ACM Digital Library", "vpn", ""),
    "10.1002": ("Wiley", "vpn", ""),
    "10.1049": ("IET", "vpn", ""),
    "10.1080": ("Taylor & Francis", "vpn", ""),
    "10.1017": ("Cambridge", "vpn", ""),
    "10.1093": ("Oxford", "vpn", ""),
    "10.1117": ("SPIE", "vpn", ""),
    "10.4018": ("IGI Global", "vpn", ""),
    "10.1142": ("World Scientific", "vpn", ""),
    "10.1201": ("CRC / Taylor & Francis", "vpn", ""),
    "10.1063": ("AIP", "vpn", ""),
    # Free, but every one of these answers a script with HTTP 403. That is bot
    # protection and it is left alone, so they cost a browser click each.
    "10.3390": ("MDPI", "open", "open access, but answers scripts with 403"),
    "10.2139": ("SSRN", "open", "free, but needs a browser"),
    "10.36227": ("TechRxiv", "open", ""),
    "10.22541": ("Authorea", "open", ""),
    "10.20944": ("Preprints.org", "open", ""),
    "10.21236": ("DTIC", "open", ""),
    "10.48550": ("arXiv", "open", ""),
    # Checked 8 of these: none held a PDF. The deposits are .zip, .docx, .html
    # or .md and two records are withdrawn (410), so the fetcher was right to
    # skip them and the .docx is often the paper itself.
    "10.1155": ("Hindawi", "open", ""),
    "10.12688": ("F1000 / Open Research Europe", "open", ""),
    "10.31235": ("SocArXiv", "open", ""),
    "10.14293": ("ScienceOpen", "open", ""),
    "10.5281": ("Zenodo", "open", "often no PDF -- the deposit is .zip/.docx/.html, some records withdrawn"),
}


def zot(args: list[str]) -> dict:
    try:
        p = subprocess.run(["zotero-cli", "--json", *args],
                           capture_output=True, text=True, timeout=60)
        return json.loads(p.stdout or "{}")
    except Exception:
        return {}


def readable(item_key: str) -> bool:
    """Ask the filesystem whether a real PDF is attached. See the docstring."""
    r = zot(["get", "children", item_key])
    if not r.get("ok"):
        return False
    for kid in ((r.get("data") or {}).get("items") or []):
        if kid.get("itemType") != "attachment":
            continue
        pr = zot(["path", kid["key"]])
        txt = ((pr.get("data") or {}).get("text") or "")
        m = re.search(r"Local path: `([^`]+)`", txt)
        if m and Path(m.group(1)).exists() and Path(m.group(1)).stat().st_size > 20_000:
            return True
    return False


_OA_CACHE: dict[str, bool] = {}


def oa_status(r: dict) -> bool:
    """Is this free, according to Unpaywall? Cached, and never fatal.

    Used only for publishers the prefix table does not know. A lookup failure
    returns False, which routes the paper to the VPN list -- the safe side,
    since a wasted login costs less than telling the owner something is free
    when it is not.
    """
    import os
    doi = c.norm_doi(r.get("doi") or "")
    if not doi:
        return False
    if doi not in _OA_CACHE:
        try:
            d = c.get_json(f"https://api.unpaywall.org/v2/{doi}",
                           {"email": c.MAILTO}, tries=2)
            _OA_CACHE[doi] = bool((d or {}).get("is_oa"))
        except Exception:
            _OA_CACHE[doi] = False
    return _OA_CACHE[doi]


def link(r: dict) -> str:
    doi = (r.get("doi") or "").strip()
    ax = (r.get("arxiv") or "").strip()
    if ax:
        return f"https://arxiv.org/abs/{ax}"
    if doi.startswith("10.48550/arxiv."):
        return f"https://arxiv.org/abs/{doi.split('arxiv.',1)[1]}"
    if m := re.match(r"10\.5281/zenodo\.(\d+)", doi):
        return f"https://zenodo.org/records/{m.group(1)}"
    if doi:
        return f"https://doi.org/{doi}"
    return (r.get("url") or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--tier", default="A")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()

    rows = c.read_rows(a.thread / "candidates.csv")
    want = [r for r in c.in_scope(rows, a.tier) if (r.get("zotero_key") or "").strip()]
    c.log(f"checking {len(want)} in-scope items for a readable PDF…")

    missing = []
    for i, r in enumerate(want, 1):
        if not readable(r["zotero_key"]):
            missing.append(r)
        if i % 100 == 0:
            c.log(f"  {i}/{len(want)} · missing so far {len(missing)}")

    have = len(want) - len(missing)

    # Papers already PROVEN unreachable are routed to interlibrary loan instead
    # of being left in a list the owner would click through and fail on. The
    # proof is holdings.py checking each Springer ISBN against the library's own
    # subscription list, so this is not a guess.
    unavailable: set[str] = set()
    prov = a.thread / "springer-access.md"
    if prov.exists():
        blk = re.search(r"## Not available.*?(?=\n## |\Z)", prov.read_text(), re.S)
        if blk:
            unavailable = set(re.findall(r"^\| `([^`]+)`", blk.group(0), re.M))
    c.log(f"verified unavailable (-> ILL): {len(unavailable)}")

    groups = collections.defaultdict(list)
    for r in missing:
        doi = (r.get("doi") or "").strip()
        pre = doi.split("/", 1)[0] if doi else ""
        if pre in PREFIX:
            pub, route, note = PREFIX[pre]
        else:
            # An unrecognised prefix is usually a small or new open-access
            # journal, and guessing "needs the VPN" sends the owner through a
            # login for something that was free. So ask Unpaywall instead of
            # assuming -- 11 of 17 unknown prefixes turned out to be gold OA.
            is_oa = oa_status(r)
            pub = "Open access (small publishers)" if is_oa else "Other / unidentified"
            route = "open" if is_oa else "vpn"
            note = ("Unpaywall confirms open access" if is_oa
                    else "publisher not identified, Unpaywall sees no open copy")
        if r["bibkey"] in unavailable:
            pub, route, note = pub, "ill", f"{c.INSTITUTION} does not subscribe -- checked against the ISBN list"
        groups[(route, pub, note)].append(r)

    L: list[str] = []
    def say(s: str = "") -> None:
        L.append(s)

    ROUTE = {
        "open": ("A. Open in a browser — NO VPN NEEDED",
                 "Free. Some sites answer scripts with 403, so the machine cannot "
                 "fetch them, but a click works for you."),
        "vpn": (f"B. Via the {c.INSTITUTION} VPN",
                f"Licensed. Connect to the {c.INSTITUTION} network, then open the link."),
        "ill": ("C. DO NOT TRY — request via interlibrary loan",
                f"Checked against the {c.INSTITUTION} subscription ISBN list: the library "
                "does not hold these. The link will show 'Log in via institution' and "
                "clicking is pointless."),
    }
    counts = {k: sum(len(v) for (rt, _, _), v in groups.items() if rt == k)
              for k in ("open", "vpn", "ill")}

    say("# Missing PDFs — full list with links")
    say()
    say(f"*Generated {c.now_iso()}.*")
    say()
    say(f"- In-scope papers in Zotero: **{len(want)}**")
    if want:
        say(f"- with a readable PDF: **{have}** ({have/len(want):.0%})")
    say(f"- **missing: {len(missing)}**")
    say()
    say("| what to do | n |")
    say("|---|---:|")
    say(f"| A. Browser, no VPN | **{counts['open']}** |")
    say(f"| B. Via {c.INSTITUTION} VPN | **{counts['vpn']}** |")
    say(f"| C. Request via interlibrary loan | **{counts['ill']}** |")
    say()
    say("**To attach:** download into `~/Downloads`, then tell me — I match them "
        "automatically on the DOI inside the PDF.")
    say()
    for route in ("open", "vpn", "ill"):
        title, blurb = ROUTE[route]
        sub = [(k, v) for k, v in groups.items() if k[0] == route]
        if not sub:
            continue
        say(f"# {title} — {counts[route]}")
        say()
        say(blurb)
        say()
        for (_, pub, note), items in sorted(sub, key=lambda kv: -len(kv[1])):
            say(f"## {pub} — {len(items)}")
            say()
            if note:
                say(f"*{note}*")
                say()
            say("| key | year | title | link |")
            say("|---|---|---|---|")
            for r in sorted(items, key=lambda x: (x.get("year") or "")):
                tt = (r.get("title") or "").replace("|", "\\|")[:70]
                u = link(r)
                say(f"| `{r['bibkey']}` | {r.get('year','')} | {tt} | "
                    f"{'[open](' + u + ')' if u else '—'} |")
            say()

    out = a.out or (a.thread / "missing-pdfs.md")
    out.write_text("\n".join(L) + "\n")
    c.log(f"{have}/{len(want)} have a PDF · {len(missing)} missing → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
