"""
اسکرپینگ تعداد Streams اسپاتیفای.
توجه: صفحه عمومی open.spotify.com/track/... محتوای اصلی را با JavaScript
رندر می‌کند، به همین دلیل با requests ساده کار نمی‌کند و از Selenium
(headless Chrome) استفاده می‌شود.

پیش‌نیاز: نصب Google Chrome + chromedriver روی سرور
    pip install selenium webdriver-manager
"""
import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .selenium_utils import build_driver


def extract_spotify_play_count(html: str) -> int | None:
    """HTML صفحهٔ عمومی اسپاتیفای را parse می‌کند و تعداد play count را برمی‌گرداند."""
    if not html:
        return None

    match = re.search(r'data-testid="playcount"[^>]*>([\d,.]+)<', html)
    if match:
        return int(re.sub(r"[.,]", "", match.group(1)))

    match2 = re.search(r'"playcount"\s*:\s*"?([\d]+)"?', html)
    if match2:
        return int(match2.group(1))

    return None


def get_spotify_streams(url: str) -> int | None:
    if not url:
        return None
    driver = None
    try:
        driver = build_driver()
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)

        return extract_spotify_play_count(driver.page_source)
    except Exception as e:
        print(f"[spotify_scraper] error fetching {url}: {e}")
        return None
    finally:
        if driver:
            driver.quit()
