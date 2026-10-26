#!/usr/bin/env python3
"""check_access.py -- what can this machine actually reach right now?

Reports which sources answer, and whether licensed ones recognise the
institution. Run it on the institution VPN and off it: the difference IS the
entitlement.

Secrets are read from ~/.ilr-env (chmod 600), which every script loads by
itself, and are never printed. Never paste a key into a chat, a commit, or a
file inside a repository.

  python3 check_access.py
"""
from __future__ import annotations
import json, os, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import common as c

OK, NO, WARN = "  OK  ", " FAIL ", " WARN "


def probe(label, url, headers=None, expect_json=True, note=""):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": c.UA, **(headers or {})})
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read()          # must read it all; a 4 KB slice of JSON
            if expect_json:           # is not JSON, which looked like a failure
                json.loads(body.decode("utf-8", "replace"))
            print(f"{OK}{label:34s} HTTP {r.status} {note}")
            return True
    except urllib.error.HTTPError as e:
        hint = {401: "key missing or wrong", 403: f"no entitlement (try the {c.INSTITUTION} VPN)",
                429: "rate limited"}.get(e.code, "")
        print(f"{NO}{label:34s} HTTP {e.code} {hint} {note}")
    except Exception as e:
        print(f"{NO}{label:34s} {type(e).__name__} {note}")
    return False


def main() -> int:
    print("\n— this machine —")
    py = sys.version_info
    print(f"{OK if py >= (3, 12) else NO}Python {py.major}.{py.minor:<27d}"
          f"{'' if py >= (3, 12) else 'need 3.12 or newer -- see setup.md step 1'}")
    try:
        import yaml  # noqa: F401
        print(f"{OK}PyYAML")
    except ImportError:
        print(f"{NO}PyYAML                           missing -- see setup.md step 1")

    print("\n— configuration —")
    print(f"{OK if c.MAILTO else NO}ILR_MAILTO                       "
          f"{c.MAILTO or 'NOT SET -- every other script will refuse to run'}")
    print(f"{OK if c.INSTITUTION_MATCH else WARN}ILR_INSTITUTION                  "
          f"{c.INSTITUTION}" + ("" if c.INSTITUTION_MATCH else
                                "  (ILR_INSTITUTION_MATCH not set: network check skipped)"))

    print("\n— open sources (should always work) —")
    probe("OpenAlex", f"https://api.openalex.org/works?per-page=1&mailto={c.MAILTO}")
    probe("Crossref", f"https://api.crossref.org/works?rows=1&mailto={c.MAILTO}")
    probe("Semantic Scholar",
          "https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1")
    probe("arXiv", "http://export.arxiv.org/api/query?search_query=all:test&max_results=1",
          expect_json=False)
    probe("IACR ePrint", "https://eprint.iacr.org/search?q=test", expect_json=False)
    probe("Zenodo", "https://zenodo.org/api/records/?size=1")

    print("\n— licensed / keyed —")
    els = os.environ.get("ELSEVIER_API_KEY")
    if not els:
        print(f"{WARN}Elsevier/Scopus                  ELSEVIER_API_KEY not set")
    else:
        h = {"X-ELS-APIKey": els, "Accept": "application/json"}
        if tok := os.environ.get("ELSEVIER_INSTTOKEN"):
            h["X-ELS-Insttoken"] = tok
        probe("Scopus Search API",
              "https://api.elsevier.com/content/search/scopus?query=TITLE(agent)&count=1",
              headers=h, note=f"(needs a {c.INSTITUTION} IP or insttoken)")
        probe("ScienceDirect Search (optional)",
              "https://api.elsevier.com/content/search/sciencedirect?query=agent&count=1",
              headers=h, note="(not used by the scripts; FAIL here is harmless)")

    if wos := (os.environ.get("WOS_STARTER_API_KEY") or os.environ.get("WOS_API_KEY")):
        probe("Web of Science Starter",
              "https://api.clarivate.com/apis/wos-starter/v1/documents?q=TS=(agent)&limit=1",
              headers={"X-ApiKey": wos})
    else:
        print(f"{WARN}Web of Science                   WOS_STARTER_API_KEY not set")

    if ieee := os.environ.get("IEEE_API_KEY"):
        probe("IEEE Xplore",
              f"https://ieeexploreapi.ieee.org/api/v1/search/articles?apikey={ieee}&max_records=1&querytext=agent")
    else:
        print(f"{WARN}IEEE Xplore                      IEEE_API_KEY not set (optional)")

    print(f"\n— are we inside the {c.INSTITUTION} network? —")
    try:
        req = urllib.request.Request("https://api.ipify.org?format=json",
                                     headers={"User-Agent": c.UA})
        ip = json.load(urllib.request.urlopen(req, timeout=15)).get("ip", "?")
        # Don't make the reader guess whether an address is the university's.
        # Ask the registry.
        owner = ""
        try:
            r2 = urllib.request.Request(f"https://rdap.db.ripe.net/ip/{ip}",
                                        headers={"User-Agent": c.UA})
            d2 = json.load(urllib.request.urlopen(r2, timeout=20))
            owner = (d2.get("name") or "") + " " + " ".join(
                " ".join(x.get("description", [])) for x in (d2.get("remarks") or [])[:2])
        except Exception:
            pass
        inside = any(k in owner.lower() for k in c.INSTITUTION_MATCH)
        print(f"{OK if inside else WARN}outward IP {ip:<18s} {owner.strip()[:46]}")
        if not c.INSTITUTION_MATCH:
            print("        set ILR_INSTITUTION_MATCH to check whether this is your institution")
        else:
            print("        inside the institution network" if inside else
                  "        NOT an institution address -- licensed sources will refuse you")
    except Exception:
        print(f"{WARN}could not determine outward IP")

    print("\n— Zotero —")
    import shutil, subprocess
    if not shutil.which("zotero-cli"):
        print(f"{NO}zotero-cli not installed           see setup.md step 3")
        return 0
    if (os.environ.get("ZOTERO_LOCAL") or "").lower() not in ("true", "1", "yes"):
        cfg = subprocess.run(["zotero-cli", "config"], capture_output=True, text=True, timeout=60)
        if "ZOTERO_LOCAL=true" not in cfg.stdout:
            print(f"{NO}zotero-cli is not in local mode   see setup.md step 3 (ZOTERO_LOCAL)")
    p = subprocess.run(["zotero-cli", "--json", "get", "recent", "--limit", "1"],
                       capture_output=True, text=True, timeout=60)
    try:
        print(f"{OK}Zotero reachable (reads)" if json.loads(p.stdout).get("ok") else f"{NO}Zotero")
    except Exception:
        print(f"{NO}Zotero not reachable              is the desktop app running, with "
              "'Allow other applications' on?")
    lib = subprocess.run(["zotero-cli", "library", "list"], capture_output=True, text=True, timeout=60)
    first = next((ln.replace("*", "").strip("- ") for ln in lib.stdout.splitlines() if "libraryID" in ln or "**" in ln), "")
    if first:
        print(f"        papers will go to the current library; libraries: {first[:60]}")
    print("        writes are not tested here: ingest.py --limit 1 --dry-run, then --limit 1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
