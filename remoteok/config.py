import os
from dotenv import load_dotenv
REMOTEOK_URL = "https://remoteok.com/"
HEADERS = {"User-Agent": "Mozilla/5.0"}



# RemoteOK homepage URL
REMOTEOK_URL = "https://remoteok.com/"

# Headers used for both requests and Playwright
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

MHTML_PATH = "remoteok_complete.mhtml"

# Database connection string
load_dotenv()
DB_URL =(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)