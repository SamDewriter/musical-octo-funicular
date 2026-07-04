
import re
import pandas as pd
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
