# RemoteOK Scraper

Small project that pulls job listings from a saved [RemoteOK](https://remoteok.com) page,
cleans them up with pandas, and stores them in PostgreSQL.

## Contents

| File | Purpose |
|---|---|
| `notebook.ipynb` | Original exploratory notebook — scraping with `requests`/`playwright`, then parsing with BeautifulSoup. Good for seeing the thought process step by step. |
| `parse_remoteok.py` | Cleaned-up script version of the notebook. Reads a saved `.mhtml` snapshot, parses it, cleans the data, and upserts it into Postgres. |
| `remoteok_complete.mhtml` | Saved snapshot of the RemoteOK homepage (input data for the script). |
| `remoteok_homepage.png` | Screenshot of the page for reference. |
| `requirements.txt` | Python dependencies. |

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install   # only needed if you want to re-scrape live, see notebook
```

Set your database connection string (defaults to a local Postgres instance):

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/hiring"
```

## Usage

```bash
python3 parse_remoteok.py
```

This will:
1. Extract the HTML payload from `remoteok_complete.mhtml`.
2. Parse each job row into a record (title, company, location, salary, tags, etc.).
3. Clean the records into a pandas DataFrame (parse salary ranges, strip emoji, dedupe).
4. Upsert everything into a `remoteok_jobs` table in Postgres.

## Learning Exercise: Modularize the Project

Right now the code lives in two places that don't talk to each other:

- `notebook.ipynb` has the **live-fetching** code — a plain `requests` GET, and a fuller
  `playwright` version that launches a real browser, waits for the page to render, and saves
  it as `remoteok_complete.mhtml`.
- `parse_remoteok.py` has the **offline processing** code — it only ever reads the `.mhtml`
  file already saved to disk; it never fetches anything itself.

That's fine for exploring, but it makes the code harder to test, reuse, and reason about as it
grows. Both files already split cleanly into stages (look at the `── N. ──` comment banners in
`parse_remoteok.py`, and the separate cells in the notebook), which makes this a good project
to practice modularizing.

### Goal

Turn both files into one small package, e.g.:

```
remoteok/
├── __init__.py
├── config.py     # MHTML_PATH, DB_URL, HEADERS, target URL, any constants
├── scrape.py      # fetch_requests(), fetch_playwright() — the notebook's live-fetch code
├── extract.py      # extract_html() — pull HTML out of a saved .mhtml file
├── parse.py         # parse_jobs()
├── clean.py           # clean(), parse_salary(), strip_emoji()
├── store.py            # store()
└── __main__.py          # CLI entry point wiring the stages together
```

### Suggested steps

1. **Create the package folder** with an empty `__init__.py` so it can be imported as
   `remoteok`.
2. **Move config first.** Put `MHTML_PATH`, `DB_URL`, the RemoteOK `url`, and the `HEADERS`
   dict from the notebook into `config.py`. Everything else imports from here instead of
   hardcoding values.
3. **Pull the scraper out of the notebook.** This is the part that's currently *not*
   modularized at all — it's just loose cells. Move the `requests.get(...)` call into a
   `fetch_requests(url)` function, and the `async_playwright()` block into a
   `fetch_playwright(url)` (or `async def`) function, both in `scrape.py`. Decide what each
   should return (raw HTML string) and what it should save (the `.mhtml` snapshot), rather than
   printing/inspecting values inline like the notebook does.
4. **One function (or related group), one module.** Move `extract_html` into `extract.py`,
   `parse_jobs` into `parse.py`, `clean` (plus its nested helpers `parse_salary` and
   `strip_emoji`) into `clean.py`, and `store` into `store.py`.
5. **Fix imports.** Each module should only import what it needs (e.g. `clean.py` needs
   `pandas` and `re`, but not `psycopg2`; `scrape.py` needs `requests`/`playwright`, but not
   `psycopg2` or `bs4`). `store.py` should be the only module that imports `psycopg2`.
6. **Rebuild the entry point.** In `__main__.py`, wire the stages together end-to-end: scrape
   (or reuse an existing `.mhtml`) → extract → parse → clean → store. `python3 -m remoteok`
   should be able to do everything the notebook + script currently do combined.
7. **Add a CLI flag (stretch goal).** Something like `--source live` vs `--source mhtml` to
   choose between `scrape.fetch_playwright()` and `extract.extract_html(MHTML_PATH)`, so the
   same pipeline works whether or not you have a fresh page to scrape.
8. **Write one test per module (stretch goal).** For example, test `clean.parse_salary` against
   inputs like `"60k - 90k"`, `"120k+"`, and `None` — no database or network required, since
   pure functions are the easiest payoff of modularizing. `scrape.py` and `store.py` are harder
   to unit test since they hit the network/DB — that's a good discussion point on why those
   often get integration tests instead.

### Why this is worth doing

- **Testability** — `clean()` and `parse_salary()` are pure functions once separated; you can
  unit test them without touching Postgres, the filesystem, or the network.
- **Reuse** — `parse_jobs()` works on HTML from *either* `scrape.py` or `extract.py`, without
  duplicating code — right now that reuse is only implicit (copy-pasted between the notebook
  and the script).
- **Clarity** — each module has one job, so a reader can find "where does the browser get
  launched?" or "where does salary parsing happen?" without scanning a notebook and a 240-line
  script side by side.

Once you're done, `python3 -m remoteok` (run from the project root) should be able to reproduce
both what the notebook does (fetch live, save an `.mhtml`) and what `parse_remoteok.py` does
today (parse an existing `.mhtml` into Postgres).
