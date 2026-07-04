import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# ── 4. Store in PostgreSQL ────────────────────────────────────────────────────
def store(df: pd.DataFrame, db_url: str) -> None:
   
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


