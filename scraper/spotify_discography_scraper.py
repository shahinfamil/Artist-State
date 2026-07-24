# -*- coding: utf-8 -*-
"""
استخراج دیسکوگرافی (آلبوم‌ها و ترک‌ها) یک آرتیست مستقیماً از صفحه‌ی عمومی
open.spotify.com با اسکرپینگ — بدون نیاز به Client ID/Secret یا ساخت اپ در
پنل دولوپر اسپاتیفای.

این روش جایگزین Spotify Web API است، برای زمانی که ساخت اپ جدید در پنل
دولوپر اسپاتیفای مسدود/غیرفعال باشد (مشکلی که از ابتدای ۲۰۲۶ برای بسیاری
از کاربران رخ داده). چون ساختار HTML/کلاس‌های اسپاتیفای ممکن است در آینده
تغییر کند، این اسکرپر چند سلکتور پشتیبان دارد؛ اگر در آینده دیگر کار نکرد،
باید سلکتورهای CSS داخل این فایل را با بازرسی صفحه (DevTools) به‌روزرسانی
کنید.
"""
import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .selenium_utils import build_driver


def _scroll_to_load(driver, rounds=8, pause=1.1):
    """صفحات اسپاتیفای دیسکوگرافی را به‌صورت lazy-load نشان می‌دهند؛
    با اسکرول تدریجی همه‌ی آیتم‌ها را وادار به بارگذاری می‌کنیم."""
    last_height = 0
    for _ in range(rounds):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        height = driver.execute_script("return document.body.scrollHeight")
        if height == last_height:
            break
        last_height = height


def get_artist_info(artist_url: str) -> dict:
    """نام و تصویر آرتیست را از صفحه‌ی عمومی او می‌خواند — برای زمانی که
    هنوز هیچ آرتیستی در دیتابیس ثبت نشده باشد."""
    driver = None
    info = {"name": "", "avatar_url": ""}
    try:
        driver = build_driver()
        driver.get(artist_url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)

        try:
            h1 = driver.find_element(By.CSS_SELECTOR, "h1")
            info["name"] = h1.text.strip()
        except Exception:
            pass

        try:
            img = driver.find_element(By.CSS_SELECTOR, 'img[src*="i.scdn.co"]')
            info["avatar_url"] = img.get_attribute("src") or ""
        except Exception:
            pass

        return info
    except Exception as e:
        print(f"[spotify_discography] error fetching artist info {artist_url}: {e}")
        return info
    finally:
        if driver:
            driver.quit()


def get_artist_albums(artist_url: str) -> list:
    """لیست آلبوم‌ها/سینگل‌های یک آرتیست را از صفحه‌ی عمومی او می‌خواند.
    خروجی: [{"title", "album_url", "cover_url"}, ...]
    """
    driver = None
    albums = []
    try:
        driver = build_driver()
        driver.get(artist_url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)
        _scroll_to_load(driver)

        anchors = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/album/"]')
        seen = set()
        for a in anchors:
            href = a.get_attribute("href")
            if not href or href in seen:
                continue

            title = (a.get_attribute("aria-label") or a.text or "").strip()
            if not title:
                continue
            seen.add(href)

            cover_url = ""
            try:
                img = a.find_element(By.TAG_NAME, "img")
                cover_url = img.get_attribute("src") or ""
            except Exception:
                # گاهی تصویر داخل خود لینک نیست بلکه در یک div والد مشترک است
                try:
                    parent = a.find_element(By.XPATH, "./ancestor::div[2]")
                    img = parent.find_element(By.TAG_NAME, "img")
                    cover_url = img.get_attribute("src") or ""
                except Exception:
                    cover_url = ""

            albums.append({"title": title, "album_url": href, "cover_url": cover_url})

        return albums
    except Exception as e:
        print(f"[spotify_discography] error fetching artist albums {artist_url}: {e}")
        return albums
    finally:
        if driver:
            driver.quit()


def get_album_tracks(album_url: str) -> dict:
    """عنوان، کاور، سال انتشار و لیست ترک‌های یک آلبوم را از صفحه‌ی آن
    می‌خواند. خروجی: {"title", "cover_url", "release_year", "tracks": [...]}
    هر ترک: {"title", "track_url", "duration"}
    """
    driver = None
    result = {"title": "", "cover_url": "", "release_year": None, "tracks": []}
    try:
        driver = build_driver()
        driver.get(album_url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)
        _scroll_to_load(driver, rounds=4)

        page_source = driver.page_source

        # عنوان آلبوم
        for selector in ['[data-testid="entityTitle"] h1', "h1"]:
            try:
                title_el = driver.find_element(By.CSS_SELECTOR, selector)
                if title_el.text.strip():
                    result["title"] = title_el.text.strip()
                    break
            except Exception:
                continue

        # کاور آلبوم
        try:
            cover_el = driver.find_element(By.CSS_SELECTOR, 'img[src*="i.scdn.co"]')
            result["cover_url"] = cover_el.get_attribute("src") or ""
        except Exception:
            pass

        # سال انتشار - جستجوی یک عدد چهاررقمی شبیه سال در ابتدای صفحه
        year_match = re.search(r"(19|20)\d{2}", page_source[:25000])
        if year_match:
            result["release_year"] = int(year_match.group(0))

        # ردیف‌های ترک
        rows = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tracklist-row"]')
        for row in rows:
            track_url, track_title = "", ""
            try:
                link = row.find_element(By.CSS_SELECTOR, 'a[href*="/track/"]')
                track_url = link.get_attribute("href") or ""
                track_title = (link.get_attribute("aria-label") or link.text or "").strip()
            except Exception:
                pass

            if not track_title:
                continue

            duration = ""
            duration_match = re.search(r"\b([0-5]?\d:[0-5]\d)\b", row.text)
            if duration_match:
                duration = duration_match.group(1)

            result["tracks"].append({
                "title": track_title,
                "track_url": track_url,
                "duration": duration,
            })

        return result
    except Exception as e:
        print(f"[spotify_discography] error fetching album tracks {album_url}: {e}")
        return result
    finally:
        if driver:
            driver.quit()
