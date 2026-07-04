import requests
from playwright.sync_api import sync_playwright
from remoteok.config import REMOTEOK_URL, HEADERS, MHTML_PATH


# step 3: Fetch the page using requests
def fetch_requests(url: str = REMOTEOK_URL) -> str:
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        print(f"Status: {response.status_code}")
        return response.text
    except Exception as e:
        print(f"Error fetching page: {e}")
        return ""
  #step 4: Fetch the page using Playwright and save as MHTML     
 
def fetch_playwright(url: str = REMOTEOK_URL, path: str = MHTML_PATH) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=HEADERS["User-Agent"])
        page = context.new_page()

        print("Connecting to RemoteOK…")
        page.goto(url, wait_until="domcontentloaded")

        # Scroll to bottom to load all jobs
        previous_height = page.evaluate("document.body.scrollHeight")
        while True:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == previous_height:
                break
            previous_height = new_height

        # Capture MHTML snapshot
        cdp = context.new_cdp_session(page)
        snapshot = cdp.send("Page.captureSnapshot", {"format": "mhtml"})
        mhtml_content = snapshot["data"]

        with open(path, "w", encoding="utf-8") as f:
            f.write(mhtml_content)
        print(f"📁 Snapshot saved to {path}")

        # ALSO save rendered HTML for parsing
        html = page.content()
        html_path = path.replace(".mhtml", ".html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"🧾 Rendered HTML saved to {html_path}")

        context.close()
        browser.close()

        return html
