# Setup, once per person

About twenty minutes. Afterwards, run `check_access.py` (step 6); it says what works and what does not.

## 1. Python and PyYAML

Python 3.11 or newer. The scripts use only the standard library, except that `bib.py`, `index.py` and `extract_check.py` read YAML frontmatter:

```bash
python3 -m pip install --user pyyaml
```

## 2. Zotero and the Zotero command line

1. Install the current **Zotero** desktop app and keep the desktop app running while the scripts work.
2. Install the command line that `ingest.py`, `fetch_pdfs.py` and `extract_prep.py` call, `zotero-cli`. It ships in the `zotero-mcp-server` package:

   ```bash
   uv tool install zotero-mcp-server
   ```

   (or `pipx install zotero-mcp-server`). Check it with `zotero-cli config`.
3. **Authorise local writes, once:** run `zotero-mcp authorize-local` and choose **Always Allow** in the Zotero dialog. Until you do, every write is refused and `ingest.py` cannot add anything.
4. Pick the library. `zotero-cli library` lists and switches libraries. Use a group library if the team shares one, otherwise your personal one.

Better BibTeX is optional. Nothing here depends on it, because `bib.py` writes the bibliography with our own citation keys.

## 3. Your private settings file: `~/.ilr-env`

Every script reads this file on start, so nothing has to be exported by hand. It lives in your home folder, **never inside a repository**, and only you can read it:

```bash
touch ~/.ilr-env && chmod 600 ~/.ilr-env
```

Then put in it whatever applies to you:

```bash
# Required. YOUR email: OpenAlex, Crossref and Unpaywall attribute requests to it.
ILR_MAILTO=you@example.org

# Your institution, for access checks and the missing-PDF list.
ILR_INSTITUTION=VU
# Words that appear in your institution network's RIPE registry entry, comma-separated.
# For Vilnius University: vilnius,uni-vilnius,litnet
ILR_INSTITUTION_MATCH=vilnius,uni-vilnius,litnet

# Optional keys. Each one adds a source or lifts a rate limit.
S2_API_KEY=            # Semantic Scholar, free: https://www.semanticscholar.org/product/api
ELSEVIER_API_KEY=      # Scopus search, abstracts, venue metrics: https://dev.elsevier.com
ELSEVIER_INSTTOKEN=    # only if Elsevier issued one, for use off the campus network
WOS_STARTER_API_KEY=   # Web of Science Starter API: https://developer.clarivate.com
WOS_STARTER_RPS=1      # 5 on the Institutional plan
IEEE_API_KEY=          # optional

# Optional. Where analysis files live, if not <workspace>/papers.
# ILR_PAPERS=/path/to/papers
```

To keep the file elsewhere, set `ILR_ENV_FILE=/path/to/file`. A variable already set in your shell always wins over the file.

**Never paste a key into a chat, a commit or a file in a repository.** Scripts read keys from the environment and never write them to logs, run records or CSVs.

## 4. A workspace

The scripts work on plain folders. One workspace holds any number of threads and one shared folder of analysis files, because a paper read once serves every thread that touches it:

```
research/
├── threads/
│   └── <thread-name>/      thread.md, candidates.csv, queries.md, runs/ ...
├── papers/                 <bibkey>.md, one per paper, plus _index.csv
└── library.bib             written by bib.py
```

Put it under git. Everything in it is text, and a thread's history is the audit trail. Start a thread by copying `templates/thread.md` from the skill into `research/threads/<thread-name>/thread.md`, or ask Claude to start one.

## 5. Browser helpers, for Gate C

- **LibKey Nomad** and **Unpaywall**: one click from a paywall to a licensed or free copy.
- **Zotero Connector**: saves a page *with* its PDF when you are signed in.

Licensed PDFs are always fetched by you, in a browser. No script logs in to a publisher.

## 6. Check it

```bash
python3 <skill>/scripts/check_access.py
python3 <skill>/scripts/selftest.py --offline
```

`<skill>` is the skill's folder. Claude knows where it is: ask it to run the access check. Run `check_access.py` once on the institution network or VPN and once off it; the difference is your licensed access.
