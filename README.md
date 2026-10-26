# Initial research tool

A Claude Code skill for the **first pass over an unfamiliar research area**: from "we should look into X" to a defensible map of the field. It gathers from several scholarly sources, screens in bands with a human audit, puts the accepted papers into Zotero, extracts one analysis file per paper with every claim backed by a quote checked against the PDF, and builds the synthesis from them.

The method, and the evidence behind it, is in [`skills/initial-literature-review/reference/method.md`](skills/initial-literature-review/reference/method.md). In short: across nine search tools and five real queries, **90% of papers were returned by exactly one tool**. Searching with one tool in one vocabulary misses most of a field. This tool exists to fix that, and to leave an audit trail behind.

## Install

In Claude Code:

```
/plugin marketplace add ariis11/initial-research-tool
/plugin install initial-literature-review@initial-research-tool
```

If the repository is private, you need read access to it on GitHub first. To update later: `/plugin marketplace update initial-research-tool`.

**Without the plugin system:** clone the repository and copy or symlink `skills/initial-literature-review` into `~/.claude/skills/`.

## Set up, once

Follow [`reference/setup.md`](skills/initial-literature-review/reference/setup.md), about 30 minutes: Python 3.12+ with PyYAML, Zotero with its local API on, `zotero-cli`, and a private `~/.ilr-env` holding **your own** email. API keys (Semantic Scholar, Scopus, Web of Science) are optional, and the guide says how to get each one and what it adds. Then ask Claude to run the access check.

## How it works

[`reference/workflow.md`](skills/initial-literature-review/reference/workflow.md) walks through the whole process, from an idea to queries, sources, screening, Zotero, extraction and synthesis, and shows where every result is saved.

## Use

Ask Claude something like *"start a literature review thread on X"* or *"where is my thread on X?"*. The skill walks through the stages and stops at five gates where you decide:

| Gate | You |
|---|---|
| A | approve the question, criteria and queries before anything is searched |
| B | audit a random sample of the screening decisions |
| C | fetch the licensed PDFs in a browser |
| D | check that a sample of quotes actually support their claims |
| E | shape the synthesis until it says what you think |

Your work lives in your own workspace (`research/threads/<name>/`, `research/papers/`), not in this repository. Everything there is plain text and CSV, so put it under git.

Every script is also a plain command-line tool and runs without Claude. See [`scripts/README.md`](skills/initial-literature-review/scripts/README.md).

## Layout

```
.claude-plugin/              plugin + marketplace manifests
skills/initial-literature-review/
├── SKILL.md                 what Claude follows
├── reference/               workflow (start here), setup, method, manual, sources, design, evidence
├── templates/               thread.md skeleton, extraction template and examples
└── scripts/                 one CLI per step (stdlib Python + PyYAML)
```

## Maintenance

One person owns the tool each term: checks that it still works after Zotero updates and that the extraction schema is being filled consistently. Without an owner it quietly rots. Run `python3 skills/initial-literature-review/scripts/selftest.py` after any change.
