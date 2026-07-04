import re
from bs4 import BeautifulSoup


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
