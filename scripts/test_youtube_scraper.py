import time
import sys
import random
from pathlib import Path
import concurrent.futures

# ensure project root is on sys.path so `scraper` package is importable
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from scraper.youtube_scraper import get_youtube_views

TEST_URLS = [
    "https://www.youtube.com/watch?v=BLBKUI7kyMM",
    "https://www.youtube.com/watch?v=oJy1ot-CKmA",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
]

TIMEOUT_SECONDS = 40

def fetch_with_timeout(url: str, timeout: int = TIMEOUT_SECONDS):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(get_youtube_views, url)
        try:
            return fut.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            fut.cancel()
            raise TimeoutError(f"fetch timeout after {timeout}s")


if __name__ == "__main__":
    for url in TEST_URLS:
        print("---")
        print("Testing:", url)
        try:
            v = fetch_with_timeout(url)
            print("Result:", v)
        except Exception as e:
            print("Exception:", repr(e))
        # keep some delay to avoid bursts
        time.sleep(4 + random.uniform(0, 2))
    print("Done.")
