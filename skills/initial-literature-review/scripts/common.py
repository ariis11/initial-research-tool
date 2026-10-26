"""Shared helpers for the initial-literature-review scripts.

Deliberately stdlib-only for HTTP so the scripts run anywhere Python 3.12+ does.
Everything here is deterministic: no model calls, no judgement.
"""
from __future__ import annotations

import csv, json, os, random, re, sys, time, unicodedata
import urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path



def _load_env_file() -> None:
    """Read KEY=VALUE lines from ~/.ilr-env (or $ILR_ENV_FILE) into os.environ.

    Keys and the contact address live in one private file outside any
    repository, so nobody has to remember to `source` it before a run. A value
    already set in the real environment always wins.
    """
    path = Path(os.environ.get("ILR_ENV_FILE") or Path.home() / ".ilr-env").expanduser()
    if not path.is_file():
        return
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        ln = re.sub(r"^export\s+", "", ln)
        k, sep, v = ln.partition("=")
        k, v = k.strip(), v.strip()
        if v[:1] in ("'", '"'):
            v = v[1:].split(v[0], 1)[0]
        else:
            v = re.split(r"(?:^|\s+)#", v, 1)[0].strip()   # inline comment
        if sep and k and v and k not in os.environ:
            os.environ[k] = v


_load_env_file()

# Identify ourselves to the polite pools. Each user sets their OWN address:
# OpenAlex, Crossref and Unpaywall attribute every request to it, and a shared
# default would put one person's name on everyone's traffic.
MAILTO = (os.environ.get("ILR_MAILTO") or "").strip()
UA = f"initial-literature-review/0.2 (mailto:{MAILTO})" if MAILTO else "initial-literature-review/0.2"


# Licensed access is per institution. The name is only used in messages; the
# match words are checked against the RIPE registry entry for your outward IP
# to tell whether you are on the institution's network (or its VPN).
INSTITUTION = (os.environ.get("ILR_INSTITUTION") or "your institution").strip()
INSTITUTION_MATCH = [w.strip().lower() for w in
                     (os.environ.get("ILR_INSTITUTION_MATCH") or "").split(",") if w.strip()]


def require_mailto() -> None:
    if not MAILTO:
        raise SystemExit("ILR_MAILTO is not set. Put your own email in ~/.ilr-env:\n"
                         "    ILR_MAILTO=you@example.org\n"
                         "(see reference/setup.md). OpenAlex, Crossref and Unpaywall "
                         "require a contact address.")


def papers_dir(thread: Path | None, override: Path | None = None) -> Path:
    """Where the per-paper analysis files live.

    --papers wins, then $ILR_PAPERS, then the workspace convention
    <workspace>/threads/<thread>  ->  <workspace>/papers.
    """
    if override:
        return override
    if os.environ.get("ILR_PAPERS"):
        return Path(os.environ["ILR_PAPERS"]).expanduser()
    if thread:
        return thread.resolve().parent.parent / "papers"
    return Path("papers")


def thread_block(thread: Path | None, name: str) -> str | None:
    """The body of a fenced ```<name> block in thread.md, or None.

    thread.md is where everything topic-specific lives -- queries, relevance
    terms, extra extraction fields -- so the scripts themselves stay generic.
    """
    if not thread:
        return None
    f = thread / "thread.md"
    if not f.exists():
        return None
    m = re.search(rf"```{re.escape(name)}\n(.*?)```", f.read_text(encoding="utf-8"), re.S)
    return m.group(1) if m else None

# A source may tell us to wait hours. Honouring that blindly turns an overnight
# run into an overnight sleep -- measured 23 September, when OpenAlex returned
# Retry-After: 9679 and the run sat idle for 3h19m having written nothing.
# We cap the wait, and if a source keeps refusing we drop it for the rest of
# the run and say so, rather than blocking every other source behind it.
MAX_BACKOFF = 90.0
HOST_COOLDOWN = 0.34          # default: ~3 req/s, inside the polite pools

# Some sources publish a specific limit. Honour it rather than discovering it
# through 429s -- and because applying for an API key means declaring that we
# do. Semantic Scholar's introductory limit is 1 request per second; arXiv asks
# for one request every three seconds.
HOST_LIMITS = {
    "api.semanticscholar.org": 1.05,
    "export.arxiv.org": 3.0,
}
_last_call: dict[str, float] = {}
_dead_hosts: dict[str, str] = {}


class HostUnavailable(Exception):
    """A source refused us persistently; skip it and carry on."""

STOPWORDS = {
    "a","an","and","are","as","at","be","by","for","from","has","in","is","it",
    "its","of","on","or","that","the","to","with","via","using","towards","toward",
}

# ─────────────────────────────── HTTP ────────────────────────────────────────

class HttpError(Exception):
    def __init__(self, status, url, body=""):
        super().__init__(f"HTTP {status} for {url}")
        self.status, self.url, self.body = status, url, body


# A key is attached by HOST, so every caller gets it without knowing it exists.
# Keys live in ~/.ilr-env (chmod 600, gitignored) and are read from the
# environment; they are never written to a log, a run file or the CSV.
AUTH_ENV = {
    "api.semanticscholar.org": ("x-api-key", "S2_API_KEY"),
}


def auth_headers(host: str) -> dict:
    """-> the auth header for this host, or {} when no key is configured.

    Absence is normal: Semantic Scholar works without a key on the shared
    public pool, just less reliably. Never raise here -- a missing key must
    degrade to the anonymous path, not kill a run.
    """
    pair = AUTH_ENV.get(host)
    if not pair:
        return {}
    header, var = pair
    val = (os.environ.get(var) or "").strip()
    return {header: val} if val else {}


def has_key(host: str) -> bool:
    """For a caller that wants to SAY whether it is authenticated."""
    return bool(auth_headers(host))


def get_json(url: str, params: dict | None = None, *, tries: int = 5,
             timeout: int = 60, headers: dict | None = None):
    """GET returning parsed JSON, with backoff on 429 and 5xx.

    Free scholarly APIs push back hard when scripted -- arXiv blocked us for
    hours and Semantic Scholar cut us off after three queries during the
    September testing. Backoff is not optional politeness here, it is the
    difference between a working script and a blocked IP.
    """
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    require_mailto()
    host = host_of(url)
    if host in _dead_hosts:
        raise HostUnavailable(f"{host} skipped for this run: {_dead_hosts[host]}")
    hdrs = {"User-Agent": UA, "Accept": "application/json"}
    hdrs.update(auth_headers(host))
    if headers:
        hdrs.update(headers)
    delay = 2.0
    for attempt in range(tries):
        _throttle(host)
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                asked = float(e.headers.get("Retry-After") or delay)
                wait = min(asked, MAX_BACKOFF)
                note = f" (asked {asked:.0f}s, capped)" if asked > wait else ""
                log(f"  {e.code} from {host} — waiting {wait:.0f}s{note} "
                    f"(attempt {attempt + 1}/{tries})")
                time.sleep(wait + random.uniform(0, 1))
                delay = min(delay * 2, MAX_BACKOFF)
                continue
            if e.code in (429, 503):
                _dead_hosts[host] = f"HTTP {e.code} after {tries} attempts"
                raise HostUnavailable(f"{host}: HTTP {e.code}, dropped for this run") from None
            raise HttpError(e.code, url, body) from None
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < tries - 1:
                time.sleep(delay); delay = min(delay * 2, 60); continue
            raise HttpError(0, url, str(e)) from None
    raise HttpError(0, url, "retries exhausted")


def get_text(url: str, params: dict | None = None, *, tries: int = 4, timeout: int = 60) -> str:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    require_mailto()
    host = host_of(url)
    if host in _dead_hosts:
        raise HostUnavailable(f"{host} skipped for this run: {_dead_hosts[host]}")
    delay = 2.0
    for attempt in range(tries):
        _throttle(host)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                asked = float(e.headers.get("Retry-After") or delay)
                time.sleep(min(asked, MAX_BACKOFF) + random.uniform(0, 1))
                delay = min(delay * 2, MAX_BACKOFF); continue
            if e.code in (429, 503):
                _dead_hosts[host] = f"HTTP {e.code} after {tries} attempts"
                raise HostUnavailable(f"{host}: HTTP {e.code}, dropped for this run") from None
            raise HttpError(e.code, url) from None
        except (urllib.error.URLError, TimeoutError):
            if attempt < tries - 1:
                time.sleep(delay); delay = min(delay * 2, 60); continue
            raise HttpError(0, url) from None
    raise HttpError(0, url, "retries exhausted")


def _throttle(host: str) -> None:
    """Keep a minimum gap between calls to the same host."""
    cooldown = HOST_LIMITS.get(host, HOST_COOLDOWN)
    last = _last_call.get(host)
    if last is not None:
        gap = cooldown - (time.monotonic() - last)
        if gap > 0:
            time.sleep(gap)
    _last_call[host] = time.monotonic()


def dead_hosts() -> dict[str, str]:
    return dict(_dead_hosts)


def revive_hosts() -> list[str]:
    """Give refused hosts another chance. A source that is merely flaky should
    not be lost for a whole run because of one bad minute."""
    revived = sorted(_dead_hosts)
    _dead_hosts.clear()
    return revived


def host_of(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc
    except Exception:
        return url[:40]


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)

# ───────────────────────── normalisation ─────────────────────────────────────

def norm_doi(doi: str | None) -> str:
    """Return a normalised DOI, or "" if the string is not one.

    The validity check is not decoration. Without it an arXiv ID like
    2604.23280 passes through as a "DOI", and every provider is then asked for
    DOI:2604.23280 and answers 404 -- which looks exactly like "this paper has
    no citations" rather than like a bug. That cost a whole backward-expansion
    run on 23 September.
    """
    if not doi:
        return ""
    d = doi.strip().lower()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d)
    d = re.sub(r"^doi:\s*", "", d)
    d = d.strip()
    return d if re.match(r"^10\.\d{4,9}/\S+$", d) else ""


def norm_arxiv(a: str | None) -> str:
    """Strip the version suffix so 2509.13597v2 and 2509.13597 are one paper."""
    if not a:
        return ""
    s = a.strip().lower()
    s = re.sub(r"^(https?://)?arxiv\.org/(abs|pdf)/", "", s)
    s = re.sub(r"^arxiv:", "", s)
    s = re.sub(r"\.pdf$", "", s)
    s = re.sub(r"v\d+$", "", s)
    s = s.strip()
    # Same reasoning as norm_doi: return "" rather than a plausible-looking
    # string, so a DOI never gets queried as an arXiv ID.
    return s if re.match(r"^(\d{4}\.\d{4,5}|[a-z-]+(\.[A-Za-z]{2})?/\d{7})$", s) else ""


def ascii_fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def title_slug(title: str) -> str:
    """Lowercase, punctuation and stopwords stripped -- the fallback match key."""
    t = ascii_fold(title or "").lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    words = [w for w in t.split() if w and w not in STOPWORDS]
    return " ".join(words)


def surname(author: str) -> str:
    """Last name from either 'Omid Mir' or 'Mir, Omid'."""
    a = ascii_fold(author or "").strip()
    if not a:
        return ""
    if "," in a:
        a = a.split(",")[0]
    else:
        a = a.split()[-1] if a.split() else ""
    return re.sub(r"[^A-Za-z]", "", a).lower()


def title_keyword(title: str) -> str:
    """The distinctive word for the citation key: longest non-stopword."""
    words = [w for w in title_slug(title).split() if len(w) > 3]
    if not words:
        return "untitled"
    return max(words, key=len)[:14]


def make_bibkey(authors, year, title, taken: set[str] | None = None) -> str:
    """firstauthor + year + keyword, e.g. mir2023delegatable.

    Ours, generated here, before Zotero has seen anything. Nothing downstream
    is ever allowed to invent a different one -- see reference/design.md.
    """
    a = surname(authors[0]) if authors else "anon"
    y = str(year or "nd")
    base = f"{a or 'anon'}{y}{title_keyword(title)}"
    base = re.sub(r"[^a-z0-9]", "", base.lower()) or "unknown"
    if taken is None or base not in taken:
        return base
    for suffix in "abcdefghijklmnopqrstuvwxyz":
        if (cand := base + suffix) not in taken:
            return cand
    return f"{base}{len(taken)}"

# ───────────────────────────── the CSV ───────────────────────────────────────

FIELDS = [
    "bibkey", "title", "authors", "year", "venue", "venue_type",
    "doi", "arxiv", "url", "abstract",
    "sources", "n_sources", "found_by", "versions",
    "band", "reason", "screened_by", "screened_at",
    "zotero_key", "first_seen",
]


def in_scope(rows: list[dict], tier: str = "A") -> list[dict]:
    """The rows that get ingested, fetched and read.

    A tiered thread (tier.py has run) means one tier; an untiered thread means
    every accepted row, bands 1 and 2. Filtering on tier alone made every PDF
    script silently find nothing on a thread that was never tiered.
    """
    if any((r.get("tier") or "").strip() for r in rows):
        return [r for r in rows if r.get("tier") == tier]
    return [r for r in rows if r.get("band") in ("1", "2")]


def blank_row() -> dict:
    return {f: "" for f in FIELDS}


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [{**blank_row(), **r} for r in csv.DictReader(fh)]


def write_rows(path: Path, rows: list[dict]) -> None:
    """Write the CSV, keeping columns this module has never heard of.

    FIELDS is the schema this pipeline owns, but later stages add their own
    columns -- tier.py adds tier/tier_reason/tiered_by. Writing FIELDS with
    extrasaction="ignore" silently deleted them: on 4 October an ingest run
    wiped 4,329 tier judgements, and the only symptom was a filter quietly
    matching nothing. Extra columns are preserved in first-seen order.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    extra: list[str] = []
    for r in rows:
        for k in r:
            if k not in FIELDS and k not in extra:
                extra.append(k)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS + extra, extrasaction="ignore")
        w.writeheader()
        base = blank_row()
        for r in rows:
            w.writerow({**base, **{k: "" for k in extra}, **r})
    tmp.replace(path)


def join_list(values) -> str:
    """Multi-values live in one cell as 'a; b; c', deduped, order preserved."""
    out, seen = [], set()
    for v in values:
        for part in (str(v).split(";") if v else []):
            p = part.strip()
            if p and p not in seen:
                seen.add(p); out.append(p)
    return "; ".join(out)


def split_list(cell: str) -> list[str]:
    return [p.strip() for p in (cell or "").split(";") if p.strip()]

# ───────────────────────── run bookkeeping ───────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_run(thread_dir: Path, script: str, payload: dict) -> Path:
    """One JSON per run: what ran, with which parameters, and what came back.

    This is what makes a run repeatable and what status.py reads. Plain files,
    git-diffable, no hidden database.
    """
    runs = thread_dir / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    path = runs / f"{stamp}-{script}.json"
    path.write_text(json.dumps({"script": script, "at": now_iso(), **payload},
                               indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def append_query_log(thread_dir: Path, entries: list[dict]) -> None:
    """Every search, verbatim, with its search mode.

    The mode field is not decoration: the same OpenAlex query returns 134 hits
    through the website (title+abstract) and 8,133 through the API (which also
    searches full text). Without it, 'we searched OpenAlex for X' is not a
    reproducible statement.
    """
    path = thread_dir / "queries.md"
    new = not path.exists()
    with path.open("a", encoding="utf-8") as fh:
        if new:
            fh.write("# Query log\n\n*Append-only. Every search that was run, "
                     "exactly as it was run.*\n")
        fh.write(f"\n## {now_iso()}\n\n")
        fh.write("| source | mode | query | available | taken | truncated |\n"
                 "|---|---|---|---|---|---|\n")
        for e in entries:
            q = str(e.get("query", "")).replace("|", "\\|")
            av = e.get("available")
            av = f"{av:,}" if isinstance(av, int) else ("—" if av is None else str(av))
            taken = e.get("taken", e.get("hits", 0))
            trunc = "yes" if e.get("truncated") else ""
            note = f" {e['error'][:40]}" if e.get("error") else ""
            fh.write(f"| {e.get('source','')} | {e.get('mode','')} | `{q}` "
                     f"| {av} | {taken}{note} | {trunc} |\n")
