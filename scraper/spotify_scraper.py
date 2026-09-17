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

    def parse_count_string(s: str) -> int | None:
        if not s:
            return None
        s = s.strip()
        s_lower = s.lower()

        # Handle suffixes like 1.2M, 3.4k
        m = re.match(r"^([\d.,]+)\s*([kmb])$", s_lower)
        if m:
            num = m.group(1).replace(",", "")
            try:
                val = float(num)
            except Exception:
                return None
            mult = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(m.group(2), 1)
            return int(val * mult)

        # Plain formatted number like 1,234,567 or 1.234.567
        m2 = re.match(r"^[\d][\d,\.\s]*[\d]$", s)
        if m2:
            digits = re.sub(r"[^0-9]", "", s)
            try:
                return int(digits)
            except Exception:
                return None

        return None

    # First: common data-testid variants
    m5 = re.search(r'data-testid\s*=\s*"playcount"[^>]*>([\d,\.\sKMkmBb]+)<', html)
    if not m5:
        m5 = re.search(r'data-testid\s*=\s*"play-count"[^>]*>([\d,\.\sKMkmBb]+)<', html)
    if m5:
        return parse_count_string(m5.group(1))

    # JSON-like fields
    m3 = re.search(r'"play_count"\s*:\s*([0-9]+)', html)
    if m3:
        try:
            return int(m3.group(1))
        except Exception:
            return None

    m2 = re.search(r'"playcount"\s*:\s*"?([\d]+)"?', html)
    if m2:
        try:
            return int(m2.group(1))
        except Exception:
            return None

    # aria-label or text containing 'plays' or localized 'پخش'
    m4 = re.search(r'([\d][\d,\.\s]*\d)\s*(?:plays|play|پخش)', html, re.IGNORECASE)
    if m4:
        digits = re.sub(r"[^0-9]", "", m4.group(1))
        try:
            return int(digits)
        except Exception:
            return None

    # Fallback: any standalone number that looks like a play count
    m6 = re.search(r'([\d][\d,\.\s]*\d)', html)
    if m6:
        digits = re.sub(r"[^0-9]", "", m6.group(1))
        try:
            return int(digits)
        except Exception:
            return None

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
