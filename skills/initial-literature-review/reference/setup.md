# Setup, once per person

About 30 minutes, plus waiting for API keys to be approved. You can start with **no keys at all**: steps 1–4 are enough for a first thread, and keys only add sources or lift rate limits.

Written for macOS. Linux works the same way with your package manager in place of Homebrew. Windows is untested.

## Checklist

- [ ] 1. Python 3.12+ with PyYAML
- [ ] 2. Zotero desktop, local API switched on
- [ ] 3. `zotero-cli` installed and allowed to write
- [ ] 4. `~/.ilr-env` with your email
- [ ] 5. API keys you want (optional)
- [ ] 6. The plugin installed in Claude Code
- [ ] 7. `check_access.py` says OK

---

## 1. Python 3.12 or newer, with PyYAML

macOS ships Python 3.9, which is **too old**. Check:

```bash
python3 --version
```

If it says less than 3.12, install a current one with [Homebrew](https://brew.sh):

```bash
brew install python
```

Open a **new** terminal and check `python3 --version` again. If it still says 3.9, Homebrew is not first on your PATH: run `eval "$(/opt/homebrew/bin/brew shellenv)"`, and add that line to `~/.zprofile` so it sticks.

Then add PyYAML, which three scripts use to read analysis files:

```bash
python3 -m pip install --user --break-system-packages pyyaml
```

(`--break-system-packages` is needed because Homebrew's Python refuses plain `pip install`. With `--user`, the package goes into your home folder and Homebrew's own files are left alone.) Check it:

```bash
python3 -c "import yaml; print('ok')"
```

## 2. Zotero desktop, with the local API on

1. Install the current Zotero from [zotero.org/download](https://www.zotero.org/download). Sign in if you use Zotero sync or a group library.
2. In Zotero: **Settings → Advanced → "Allow other applications on this computer to communicate with Zotero"**, ticked. The scripts talk to the running desktop app through this. No Zotero web API key is needed.
3. Keep Zotero open whenever the scripts add papers, attach PDFs or read full text.

## 3. `zotero-cli`

It ships in the `zotero-mcp-server` package. Install it with `uv`, which keeps it in its own environment:

```bash
brew install uv
uv tool install zotero-mcp-server
```

(`pipx install zotero-mcp-server` works too.) If `zotero-cli` is then "command not found", run `uv tool update-shell` and open a new terminal.

**Switch on local mode, once.** This tells `zotero-cli` to talk to the Zotero app on your machine rather than the zotero.org web API:

```bash
zotero-mcp setup --no-claude --skip-semantic-search
```

It writes `~/.config/zotero-mcp/config.json` with `ZOTERO_LOCAL=true`. Also add `ZOTERO_LOCAL=true` to `~/.ilr-env` (step 4); the scripts pass it on to `zotero-cli`.

Check that it reaches Zotero:

```bash
zotero-cli config          # should show ZOTERO_LOCAL=true
zotero-cli library list    # should list "My Library" and any group libraries
```

If `zotero-cli config` does not show `ZOTERO_LOCAL=true`, run the setup command again. If the library list fails, Zotero isn't running or the step-2 setting is off.

**Allow writes, once.** Run the command below and click **Always Allow** in the dialog that appears in Zotero. Until you do, every write is refused and papers can't be added.

```bash
zotero-mcp authorize-local
```

**Choose the library.** Papers go into whichever library `zotero-cli` points at: **your personal My Library by default, and that is the standard choice** unless the group agrees on a shared group library. Each thread gets its own collection there, named after the thread folder. To use a group library instead:

```bash
zotero-cli library switch --library-type group --library-id <id>
```

The group's id is in `zotero-cli library list`. Writing to group libraries has not been tested yet, so try a small ingest (`ingest.py --limit 5`) first.

Better BibTeX is optional. Nothing depends on it, because `bib.py` writes the bibliography itself.

## 4. Your private settings file, `~/.ilr-env`

Every script reads this file on start, so you never export anything by hand. It lives in your home folder, **never in a repository**, and only you can read it:

```bash
touch ~/.ilr-env && chmod 600 ~/.ilr-env
open -e ~/.ilr-env
```

Paste this in and fill in what applies. Lines you leave empty are ignored.

```bash
# ── Required ─────────────────────────────────────────────────────────
# YOUR email. OpenAlex, Crossref and Unpaywall require a contact address
# and attribute your requests to it. Scripts refuse to search without it.
ILR_MAILTO=

# Zotero: talk to the desktop app (step 3)
ZOTERO_LOCAL=true

# ── Institution (for access checks and the missing-PDF list) ─────────
ILR_INSTITUTION=VU
# Words in your institution network's registry entry. For Vilnius University:
ILR_INSTITUTION_MATCH=vilnius,uni-vilnius,litnet

# ── Optional API keys (step 5) ───────────────────────────────────────
S2_API_KEY=
ELSEVIER_API_KEY=
ELSEVIER_INSTTOKEN=
WOS_STARTER_API_KEY=
WOS_STARTER_RPS=1
IEEE_API_KEY=

# ── Optional: where analysis files live, if not <workspace>/papers ───
# ILR_PAPERS=/path/to/research/papers
```

To keep the file somewhere else, set `ILR_ENV_FILE=/path/to/file` in your shell. A variable set in your shell always wins over the file.

**Never paste a key into a chat with Claude, a commit or a shared document.** Type it into this file yourself. The scripts read keys from the environment and never write them to logs, run records or CSVs.

## 5. API keys

All optional. Without any key the tool searches OpenAlex, Semantic Scholar (at a lower rate), arXiv and IACR ePrint, and fetches open PDFs.

| Key | What it adds | Without it | Cost |
|---|---|---|---|
| `S2_API_KEY` | Semantic Scholar at a dependable rate; more citation edges in `expand.py`; bulk abstracts | works, but shares a public pool and hits rate limits on big runs | free |
| `ELSEVIER_API_KEY` | **Scopus** as a search source; Scopus abstracts; venue metrics (CiteScore, SJR, SNIP) in `venue_quality.py` | no Scopus; no venue quartiles | free key; access through your institution's subscription |
| `ELSEVIER_INSTTOKEN` | Scopus from outside the institution network | Scopus works only on campus or VPN | issued to the institution |
| `WOS_STARTER_API_KEY` | **Web of Science** as a source (add `wos` to the thread's `sources` block alongside the others); checks which journals are WoS-indexed | no WoS | free trial plan; institutional plan via the library |
| `IEEE_API_KEY` | only checked by `check_access.py`; no script searches IEEE with it yet | nothing lost | free |

**How to get each one:**

**Semantic Scholar (`S2_API_KEY`)**
1. Go to [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api) and use the API key request form.
2. Describe the use honestly: academic literature review, a few thousand requests per run, one request per second. The scripts already respect that rate.
3. The key arrives by email, usually within days. An institutional email helps.

**Elsevier / Scopus (`ELSEVIER_API_KEY`)**
1. Go to [dev.elsevier.com](https://dev.elsevier.com), sign in with an Elsevier account (create one with your institution email), and choose **I want an API key**.
2. Give it a label, and leave the website field blank or put your department page. Accept the non-commercial terms.
3. The key works only when your requests come from the institution's network, so run on campus or on the VPN. `check_access.py` shows whether you're inside.
4. `ELSEVIER_INSTTOKEN` is only for working off campus without the VPN. Elsevier issues it to the institution, so ask the library. Most people don't need it.
5. Quotas are generous: Scopus Search around 20,000 requests a week, abstract retrieval around 10,000.

**Web of Science Starter (`WOS_STARTER_API_KEY`)**
1. Go to [developer.clarivate.com](https://developer.clarivate.com), register, open **Web of Science Starter API** and subscribe to a plan.
2. The free trial plan allows about 50 requests a day: enough to try it, not for a full thread. The **Institutional Member** plan (about 5,000 a day) needs the institution's WoS subscription, so ask the library.
3. On the institutional plan, also set `WOS_STARTER_RPS=5`.

**IEEE Xplore (`IEEE_API_KEY`):** optional. Register at [developer.ieee.org](https://developer.ieee.org).

**No key needed:** OpenAlex, Crossref, arXiv, IACR ePrint, Unpaywall and Zenodo. They only need `ILR_MAILTO`. DBLP and Google Scholar have no usable API and are searched by hand.

## 6. Install the plugin

In Claude Code:

```
/plugin marketplace add ariis11/initial-research-tool
/plugin install initial-literature-review@initial-research-tool
```

Restart Claude Code so it picks up the skill. To update later: `/plugin marketplace update initial-research-tool`.

## 7. Check it

Ask Claude: *"run the literature review access check"*. Or find the scripts folder and run it yourself:

```bash
S="$(dirname "$(find ~/.claude -path '*initial-literature-review/SKILL.md' | head -1)")/scripts"
python3 "$S/check_access.py"
python3 "$S/selftest.py" --offline
```

`check_access.py` prints one line per item. You want **OK** on Python, PyYAML, `ILR_MAILTO`, the open sources and Zotero, and **OK** on any key you set. A FAIL on "ScienceDirect (optional)" is harmless. It does not test Zotero *writes*: the first `ingest.py --limit 1` does that, and fails clearly if step 3's `authorize-local` was skipped. Run it once on the institution network or VPN and once off it: the difference is your licensed access.

## 8. A workspace

The scripts work on plain folders. One workspace holds any number of threads and one shared folder of analysis files:

```
research/
├── threads/<thread-name>/   one folder per review
├── papers/                  one analysis file per paper, shared by all threads
└── library.bib              generated
```

Put it in any folder you like, ideally under git. To start, ask Claude *"start a literature review thread on <topic> in ./research"*. `workflow.md` explains every step from there.
