import argparse
import sys
from remoteok.config import REMOTEOK_URL, HEADERS, MHTML_PATH

from remoteok.scrape import fetch_requests, fetch_playwright
from remoteok.extract import extract_html
from remoteok.parse import parse_jobs
from remoteok.clean import clean
from remoteok.store import store
from remoteok.config import MHTML_PATH, DB_URL


def run_pipeline(use_playwright: bool):
    print("🚀 Starting RemoteOK pipeline…")

    # 1. SCRAPE
    if use_playwright:
        print("📡 Using Playwright scraper…")
        html = fetch_playwright()  # already returns rendered HTML
        print(f"📁 Snapshot saved to {MHTML_PATH}")
        print("🔍 Using rendered HTML from Playwright (no extraction needed).")
    else:
        print("🌐 Using Requests scraper…")
        html = fetch_requests()
        print("🔍 Fetched static HTML.")

    # 2. PARSE
    print("📦 Parsing jobs…")
    records = parse_jobs(html)
    print(f"  Found {len(records)} raw job rows")

    # 3. CLEAN
    print("🧹 Cleaning…")
    df = clean(records)
    print(f"  {len(df)} jobs after dedup/clean")

    # Show preview
    preview_cols = ["title", "company", "location", "salary_min", "salary_max", "tags_str"]
    print(df[preview_cols].head(10).to_string())

    # 4. STORE
    print(f"\n💾 Storing to Postgres ({DB_URL})…")
    store(df, DB_URL)

    print("🎉 Pipeline completed successfully!")


def main():
    parser = argparse.ArgumentParser(description="RemoteOK Scraper CLI")
    parser.add_argument(
        "--playwright",
        action="store_true",
        help="Use Playwright instead of Requests"
    )

    args = parser.parse_args()

    try:
        run_pipeline(use_playwright=args.playwright)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
