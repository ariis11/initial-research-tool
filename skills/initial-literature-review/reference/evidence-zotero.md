# Zotero AI Tools: Test Results

---

## 1. What we tested, and how

| Tool | How far we tested |
|---|---|
| **Zotero MCP** | **Full hands-on test** — installed, indexed 586 items, ran searches, imports, citation lookups |
| **LLM for Zotero** | **Full hands-on test** — installed, ran the figure-reading test on a real diagram |
| **Beaver** | **Full hands-on test** — installed, ran the cross-vocabulary test, verified its citations |
| Other three | **Compatibility checked** — downloaded each `.xpi`, read its `manifest.json` |

**Why the compatibility check mattered:** Zotero 10 came out on 17 August. Our 12 September note said the plugins hadn't kept up. That was based on reading their **READMEs**. Zotero doesn't read READMEs — it enforces `manifest.json`. So we opened the real file in each one.

---

## 2. Does it work on Zotero 10?

| Tool | Latest release | Date | Zotero 10 | Risk of breaking on the next version |
|---|---|---|---|---|
| **LLM for Zotero** | v3.9.7 | 15 Sep | ✅ | **Lowest** — declares support up to `9999.*`, so no version gate at all |
| **Beaver** | v0.25.0-beta.2 | 15 Sep | ✅ | Low — capped at `10.0.*`, but ships constantly |
| **PapersGPT** | v1.5.0 | 11 Sep | ✅ | Low — capped at `10.*` |
| **Zotero-GPT** | 3.1.4 | 1 May | ✅ | **Medium** — capped at `10.*`, but 4 months quiet |
| **SeerAI** | 1.9.4 | 3 Jul | ❌ | Blocked — capped at Zotero `9.*` |
| **Aria** | v0.7.5 | Oct 2024 | ❌ | Blocked — capped at Zotero `7.*` |
| **Zotero MCP** | 0.12.4 | 15 Sep | ✅ | **None** — not a plugin, so Zotero versions don't apply |

**Four of six plugins work.** Our earlier "the ecosystem hasn't kept up" claim was wrong.

> **Lesson: check `manifest.json`, not the README.** Nobody updates their README.

---

## 3. What each tool can do

Capabilities as documented by each tool, regardless of what we tested.

| | Zotero MCP | LLM for Zotero | Beaver | PapersGPT | Zotero-GPT | SeerAI |
|---|---|---|---|---|---|---|
| Search your library | ✅ semantic + keyword | ✅ | ✅ | ✅ | ✅ | ✅ |
| Chat with a PDF | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Read figures / diagrams** | — | ✅ | — | — | — | — |
| Compare across papers | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| **Search outside your library** | — | web search | ✅ **240M works** | — | — | ✅ **11 databases inc. IACR** |
| Write highlights/notes into Zotero | ✅ | ✅ | ✅ | — | — | ✅ |
| **Import by DOI / BibTeX / ISBN** | ✅ | — | ✅ suggests | — | — | ✅ |
| Auto-find free PDFs | ✅ | — | — | — | — | — |
| Edit tags / metadata in bulk | ✅ | ✅ | ✅ | — | — | ✅ |
| Structured extraction to tables | — | — | — | — | — | ✅ |
| Systematic-review workflow | — | — | — | — | — | ✅ PRISMA |
| Runs fully offline | ✅ | ✅ optional | ❌ cloud | ✅ | ❌ | ✅ optional |
| Works without an API key | ✅ | ✅ via WebChat | ✅ free tier | — | — | — |
| Cost | Free | Free + your key | Free tier / $10–20 mo | Free + your key | Free + your key | Free + your key |

**Worth knowing about each:**

- **Zotero MCP** — not a plugin; a program that serves your library to Claude Code or the command line. Also: read specific PDF pages, extract annotations, find duplicates, export bibliographies, report which items lack PDFs.
- **LLM for Zotero** — quick-action buttons for Summarize / Key Points / Methodology / Limitations / **Diagram**. Runs on your API key, a local model, or by relaying through a logged-in ChatGPT/Gemini tab.
- **Beaver** — three interfaces (sidebar, corner card, full window). Answers become real Zotero highlights. Offers to import papers it finds.
- **PapersGPT** — bundles open-weight models for genuinely offline use; batch "AutoPilot" processing.
- **Zotero-GPT** — the basics only, OpenAI-only. Most popular, least maintained.
- **SeerAI** — by far the biggest feature list, and the only one that searches **IACR ePrint**. Blocked on Zotero 10.

---

## 4. What we tested, and what happened

**Zotero MCP** — imported by DOI and by BibTeX file (batch, into a collection, tagged), and it chased down free PDFs automatically through Unpaywall → arXiv → Semantic Scholar → PubMed Central. Indexed 586 items in 17 seconds. Semantic search found the right papers where keyword search failed completely.
❌ **Forward citations always return zero** — tested on papers with 728, 1,307 and 290 citations. Minor bugs: arXiv IDs rejected, `setup` can't find its own program.

**LLM for Zotero** — asked to "explain this figure", it answered entirely from the body text and looked convincing. Asked what was *written in each box* and *which way the arrows point*, it returned correct labels, a whole section the text never mentions, and a colour. Checked against the figure: correct.
❌ **It cannot count** — said 33 boxes, corrected to 29, neither matching its own list.
→ **It really reads figures. Trust the labels, never the numbers.**

**Beaver** — asked in pure agent language about revoking an AI agent's authority, it split the question in two by itself and searched the older security literature as well. Reached capability-systems work; **did not reach cryptography**. Asked again naming accumulators and anonymous credentials, it found Camenisch–Lysyanskaya 2002, ALLOSAUR, Baldimtsi and more, went outside the library for papers we don't have, and mapped each onto agent authority. **Citations spot-checked: all real, one wrong year.** Its highlights persist in Zotero and are editable and deletable after Beaver is closed.
→ **It crosses between fields, but only if you name where to look.**

---

## 5. Decision

| Tool | Decision | Why |
|---|---|---|
| **Zotero MCP** | ✅ **Use** | Gets papers *into* Zotero fastest — DOI, BibTeX batches, and it finds the free PDF for you. Semantic search actually works. Free, fully local, nothing leaves your machine. Read-only unless you grant otherwise. Not a plugin, so a Zotero update can't break it |
| **LLM for Zotero** | ✅ **Use** | The only one that reads diagrams, and our papers are full of them. Also solid for normal PDF chat, with grounded citations you can click back to. Works without an API key. No version cap, so lowest risk of dying |
| **Beaver** | ✅ **Use** | Best reasoning across several papers. Reaches literature you don't own (240M works) and suggests imports. Its highlights are real Zotero annotations that survive the tool. ⚠️ **Only tool where your content leaves your machine** |
| **Better BibTeX** | ✅ **Keep as standard** | Not AI. Stable citation keys are what hold the whole pipeline together — everything else is optional, this isn't |
| **PapersGPT** | ⬜ Skip | Its one advantage is offline use, and Zotero MCP is already fully local |
| **Zotero-GPT** | ⬜ Skip | Does less than the others, OpenAI-only, thinly maintained |
| **SeerAI** | ❌ Can't use | Blocked on Zotero 10. The loss is its IACR search — but searching IACR directly already works |

**In short:** Zotero MCP to get papers in and find them again · LLM for Zotero when the meaning is in a diagram · Beaver to reason across papers and reach work you don't have.

---

## 6. Things worth knowing

**"Explain this" is the wrong question.** LLM for Zotero answered it convincingly from the body text without looking at the figure. Only a question the text couldn't answer forced it to look. **When testing any AI tool, ask something only that tool could answer.**

**Check a few citations every time.** Beaver produced nine cryptography papers with references. Four checked: all real, one wrong year. Good result — but it took two minutes, and the risk is a confident reference to a paper that doesn't exist.

**Beaver sends your content to its servers.** Frontend open source, backend closed. Its policy says no training on your data without opt-in — a policy, not a guarantee. Fine for published papers; decide consciously before anything unpublished goes near it.

**WebChat works but isn't a group recommendation.** It avoids API keys by relaying through a logged-in ChatGPT tab, but needs a browser extension that isn't in the Chrome Web Store and must be loaded in developer mode. No review, no auto-updates, breaks when ChatGPT changes. Use an API key instead.

**Zotero MCP's permissions are well designed.** Writing is off by default. Turning it on opens a dialog *inside Zotero* offering one-time or reusable access. Revoking works. Deletes go to the Trash, not oblivion. **A tool you can grant narrow, revocable access to is safer to depend on than one needing standing credentials.**

**On tools that may stop being maintained** — the question isn't "is it maintained", it's **"what breaks when it stops?"** If the output lives in Zotero and Git, a dead tool costs you a workflow, not your work. Our storage design already ensures that.

| Tier | Meaning |
|---|---|
| **Standard** | The group depends on it — needs active maintenance and open output (Zotero, Better BibTeX, Git) |
| **Recommended** | Individuals use it; output lands in the standard format (Zotero MCP, LLM for Zotero, Beaver) |
| **Opportunistic** | Use while it works, never depend on it — one maintainer or a stale release (SeerAI) |

If we do standardise on something: pin the version, keep the installer, and make sure the output is readable without the tool.

**Installing Zotero MCP:**
- Package is **`zotero-mcp-server`** — a different, smaller project is called `zotero-mcp`
- First turn on Zotero → Settings → Advanced → *"Allow other applications on this computer to communicate with Zotero"*
- You don't need `uv`; a plain Python venv works
- Semantic search needs **~1.5 GB** extra and isn't installed by default
