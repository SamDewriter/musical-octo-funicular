"""
Parse remoteok_complete.mhtml → clean DataFrame → store in PostgreSQL.

Usage:
    python3 parse_remoteok.py

Set DATABASE_URL env var or edit DB_URL below before running.
"""

import email
import quopri
import re
import os
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup

# ── Config ──────────────────────────────────────────────────────────────────
MHTML_PATH = "/Users/apple/hiring/remoteok_complete.mhtml"
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hiring")


# ── 1. Extract HTML from MHTML ───────────────────────────────────────────────
def extract_html(path: str) -> str:
    with open(path, "rb") as f:
        msg = email.message_from_bytes(f.read())

    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=False)  # raw string (still QP-encoded)
            if isinstance(payload, str):
                payload = payload.encode("latin-1")
            decoded = quopri.decodestring(payload)
            return decoded.decode("utf-8", errors="replace")

    raise ValueError("No text/html part found in MHTML")


# ── 2. Parse jobs with BeautifulSoup ─────────────────────────────────────────
def parse_jobs(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")

    # Each job is a <tr> with id="job-XXXXX"
    job_rows = soup.find_all("tr", id=re.compile(r"^job-\d+$"))

    records = []
    for row in job_rows:
        job_id = row.get("data-id", "").strip()
        slug = row.get("data-slug", "").strip()
        epoch = row.get("data-epoch", "").strip()
        apply_path = row.get("data-href", "").strip()

        # Title
        title_tag = row.find(itemprop="title")
        title = title_tag.get_text(strip=True) if title_tag else None

        # Company
        company_tag = row.find(itemprop="name")
        company = company_tag.get_text(strip=True) if company_tag else None

        # Location — strip emoji prefix if present
        loc_tag = row.find("div", class_="location")
        location = loc_tag.get_text(strip=True) if loc_tag else None

        # Salary
        sal_tag = row.find("div", class_="salary")
        salary_raw = sal_tag.get_text(strip=True) if sal_tag else None

        # Tags
        tag_divs = row.find_all("div", class_=re.compile(r"\btag\b"))
        tags = [t.get_text(strip=True) for t in tag_divs if t.get_text(strip=True)]

        # Posted datetime
        time_tag = row.find("time")
        posted_at = time_tag.get("datetime") if time_tag else None

        records.append(
            {
                "job_id": job_id,
                "slug": slug,
                "title": title,
                "company": company,
                "location": location,
                "salary_raw": salary_raw,
                "tags": tags,
                "posted_at": posted_at,
                "epoch": int(epoch) if epoch.isdigit() else None,
                "apply_url": f"https://remoteok.com{apply_path}" if apply_path else None,
            }
        )

    return records


# ── 3. Clean with pandas ──────────────────────────────────────────────────────
def clean(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)

    # Drop rows with no title (ads / dividers that matched the selector)
    df = df[df["title"].notna() & (df["title"] != "")].copy()

    # Parse salary into min/max integers (USD)
    def parse_salary(s):
        if not isinstance(s, str):
            return None, None
        s = s.replace(",", "").replace("$", "").replace("💰", "").strip()
        # e.g. "60k - 90k"  or  "120k+"
        nums = re.findall(r"(\d+(?:\.\d+)?)\s*k?", s, re.IGNORECASE)
        multipliers = [1000 if "k" in tok.lower() else 1
                       for tok in re.findall(r"(\d+(?:\.\d+)?k?)", s, re.IGNORECASE)]
        values = []
        for n, m in zip(nums, multipliers):
            try:
                values.append(int(float(n) * m))
            except ValueError:
                pass
        # Re-check if original had "k"
        k_flags = [bool(re.search(r"\d+k", tok, re.IGNORECASE))
                   for tok in re.findall(r"\d+\.?\d*k?", s, re.IGNORECASE)]
        values = []
        for tok in re.findall(r"\d+\.?\d*k?", s, re.IGNORECASE):
            num = float(re.search(r"[\d.]+", tok).group())
            if "k" in tok.lower():
                num *= 1000
            values.append(int(num))
        if len(values) == 0:
            return None, None
        if len(values) == 1:
            return values[0], values[0]
        return values[0], values[1]

    df[["salary_min", "salary_max"]] = df["salary_raw"].apply(
        lambda s: pd.Series(parse_salary(s))
    )

    # Clean location — strip leading emoji/whitespace
    def strip_emoji(s):
        if not isinstance(s, str):
            return s
        return re.sub(r"^[\U00010000-\U0010ffff\s]+", "", s).strip()

    df["location"] = df["location"].apply(strip_emoji)

    # posted_at → datetime
    df["posted_at"] = pd.to_datetime(df["posted_at"], utc=True, errors="coerce")

    # tags list → pipe-separated string for easy SQL storage
    df["tags_str"] = df["tags"].apply(lambda t: "|".join(t) if isinstance(t, list) else "")

    # Deduplicate (same job_id may appear as sticky + normal)
    df = df.drop_duplicates(subset="job_id", keep="first").reset_index(drop=True)

    return df[[
        "job_id", "slug", "title", "company", "location",
        "salary_raw", "salary_min", "salary_max",
        "tags_str", "posted_at", "epoch", "apply_url",
    ]]


# ── 4. Store in PostgreSQL ────────────────────────────────────────────────────
def store(df: pd.DataFrame, db_url: str) -> None:
    import psycopg2
    from psycopg2.extras import execute_values

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS remoteok_jobs (
            job_id      TEXT PRIMARY KEY,
            slug        TEXT,
            title       TEXT,
            company     TEXT,
            location    TEXT,
            salary_raw  TEXT,
            salary_min  INTEGER,
            salary_max  INTEGER,
            tags        TEXT,
            posted_at   TIMESTAMPTZ,
            epoch       BIGINT,
            apply_url   TEXT,
            scraped_at  TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    conn.commit()

    rows = [
        (
            r.job_id, r.slug, r.title, r.company, r.location,
            r.salary_raw,
            int(r.salary_min) if pd.notna(r.salary_min) else None,
            int(r.salary_max) if pd.notna(r.salary_max) else None,
            r.tags_str, r.posted_at, r.epoch, r.apply_url,
        )
        for r in df.itertuples()
    ]

    execute_values(
        cur,
        """
        INSERT INTO remoteok_jobs
            (job_id, slug, title, company, location, salary_raw,
             salary_min, salary_max, tags, posted_at, epoch, apply_url)
        VALUES %s
        ON CONFLICT (job_id) DO UPDATE SET
            title      = EXCLUDED.title,
            company    = EXCLUDED.company,
            location   = EXCLUDED.location,
            salary_raw = EXCLUDED.salary_raw,
            salary_min = EXCLUDED.salary_min,
            salary_max = EXCLUDED.salary_max,
            tags       = EXCLUDED.tags,
            posted_at  = EXCLUDED.posted_at,
            apply_url  = EXCLUDED.apply_url,
            scraped_at = NOW();
        """,
        rows,
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f"Upserted {len(rows)} rows into remoteok_jobs.")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Extracting HTML from MHTML…")
    html = extract_html(MHTML_PATH)

    print("Parsing jobs…")
    records = parse_jobs(html)
    print(f"  Found {len(records)} raw job rows")

    print("Cleaning…")
    df = clean(records)
    print(f"  {len(df)} jobs after dedup/clean")
    print(df[["title", "company", "location", "salary_min", "salary_max", "tags_str"]].head(10).to_string())

    print(f"\nStoring to Postgres ({DB_URL})…")
    store(df, DB_URL)
