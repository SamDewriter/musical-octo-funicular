import logging
from remoteok.scrape import fetch_playwright
from remoteok.parse import parse_jobs
from remoteok.clean import clean
from remoteok.store import store
import os

from dotenv import load_dotenv
load_dotenv()
db_url = os.getenv("DB_URL")

# ---------------------------------------------------
# Logging setup
# ---------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    handlers=[
        logging.FileHandler("logs/pipeline.log", mode="a"),
        logging.StreamHandler()
    ]
)

# ---------------------------------------------------
# Pipeline Orchestration
# ---------------------------------------------------
def run_pipeline(job_title: str | None = None):
    logging.info("🚀 Pipeline started")

    try:
        # 1. Scrape
        logging.info("🔍 Fetching jobs from RemoteOK…")
        raw_html = fetch_playwright()

        # 2. Parse
        logging.info(
            "📦 Parsing job listings..."
            + (f" (filtered by title: {job_title})" if job_title else " (all jobs)")
        )
        jobs = parse_jobs(raw_html, job_title=job_title)

        # 3. Clean
        logging.info(f"🧼 Cleaning {len(jobs)} jobs…")
        cleaned_jobs = clean(jobs)

        # 4. Store
        logging.info("💾 Storing results in PostgreSQL…")
        store(cleaned_jobs, db_url=db_url)

        logging.info("🎉 Pipeline executed successfully!")

    except Exception as e:
        logging.error(f"❌ Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    run_pipeline()
