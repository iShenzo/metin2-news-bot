# scraper.py

import re
import requests
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from config import CATEGORIES

def fetch_forum_listing(forum_url):
    """
    Liefert für jedes Forum-Board eine Liste von Threads als
      (thread_id, title, url, last_time)
    sortiert nach last_time desc. Unterstützt WCF5 und WBB4,
    überspringt Sticky-Threads, und fällt bei 0 Replies
    auf die Thread-Erstellungszeit zurück.
    """
    resp = requests.get(forum_url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    threads = []

    # --- WCF5-Layout erkennen ---
    if soup.select_one("ul.structItemContainer"):
        for li in soup.select("ul.structItemContainer li.structItem--thread"):
            if "structItem--sticky" in li.get("class", []):
                continue
            a = li.select_one("h3.structItem-title a.structItem-title--link")
            if not a:
                continue
            href  = a["href"]
            url   = urljoin(forum_url, href)
            title = a.get_text(strip=True)
            m = re.search(r"/thread/(\d+)", href)
            if not m:
                continue
            tid = int(m.group(1))

            time_el = li.select_one("div.structItem-cell--latest time.u-dt")
            if not time_el or not time_el.has_attr("datetime"):
                continue
            last_time = datetime.fromisoformat(time_el["datetime"])

            threads.append((tid, title, url, last_time))

    # --- WBB4-Layout erkennen ---
    elif soup.select_one("li.columnSubject"):
        for subj in soup.select("li.columnSubject"):
            # Sticky-Thread überspringen
            icon_li = subj.find_previous_sibling("li", class_="columnIcon")
            if icon_li and icon_li.select_one("span.wbbStickyIcon"):
                continue

            a = subj.select_one("h3 a.messageGroupLink.wbbTopicLink")
            if not a:
                continue
            href  = a["href"]
            url   = urljoin(forum_url, href)
            title = a.get_text(strip=True)
            tid   = int(a["data-thread-id"])

            # Versuch 1: Zeit des letzten Posts
            last_li   = subj.find_next_sibling("li", class_="columnLastPost")
            time_el   = last_li.select_one("time.datetime") if last_li else None

            # Fallback bei 0 Replies: Erstellungszeit im columnSubject
            if not time_el or not time_el.has_attr("datetime"):
                time_el = subj.select_one("li.messageGroupTime time.datetime")

            if not time_el or not time_el.has_attr("datetime"):
                continue
            last_time = datetime.fromisoformat(time_el["datetime"])

            threads.append((tid, title, url, last_time))

    else:
        # Unbekanntes Layout
        return []

    # Sortiere: neueste Threads zuerst
    threads.sort(key=lambda x: x[3], reverse=True)
    return threads

def fetch_latest_post(thread_url):
    """
    Holt den neuesten Post eines Threads (inkl. Paging), entfernt TOC
    und gibt (post_id, text, [images], post_time) zurück.
    """
    # 1) Erste Seite → max_page finden
    resp = requests.get(thread_url); resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    max_page = 1
    for a in soup.select('a[href*="pageNo="]'):
        m = re.search(r"pageNo=(\d+)", a["href"])
        if m and (p := int(m.group(1))) > max_page:
            max_page = p

    # 2) Letzte Seite laden
    last_url = thread_url.rstrip("/") + f"&pageNo={max_page}" if max_page>1 else thread_url
    resp = requests.get(last_url); resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # 3) Letzten Post selektieren
    posts = soup.select("article.wbbPost")
    if not posts:
        return None, "", [], None
    last = posts[-1]
    post_id = int(last["data-post-id"])

    # 4) post_time
    time_el = last.select_one("time.datetime")
    post_time = datetime.fromisoformat(time_el["datetime"]) if time_el else None

    # 5) Text + TOC-Entfernung
    msg = last.select_one("div.messageText")
    if msg:
        for toc in msg.select(".scTocTitle, .scTocListLevel-1, .scTocListLevel-2"):
            toc.decompose()
        text = msg.get_text(" ", strip=True)
    else:
        text = ""

    # 6) Bilder (max. 3)
    images = []
    if msg:
        for img in msg.select("img"):
            src = img.get("src")
            if src:
                images.append(src)
            if len(images) >= 3:
                break

    return post_id, text, images, post_time

def shorten(text, max_words=250, max_chars=1900):
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]) + "…"
    if len(text) > max_chars:
        text = text[:max_chars-1] + "…"
    return text

def send_to_discord(webhook_url, title, text, url, images):
    # Bild posten
    if images:
        try: requests.post(webhook_url, json={"content": images[0]}).raise_for_status()
        except: pass

    # Text posten
    excerpt = shorten(text)
    content = f"**{title}**\n\n{excerpt}\n\n↪️ {url}"
    if len(content) > 2000:
        content = content[:1999] + "…"
    try: requests.post(webhook_url, json={"content": content}).raise_for_status()
    except: pass

    # Trenner
    sep = "──────────────────────────────────────────────────"
    try: requests.post(webhook_url, json={"content": sep}).raise_for_status()
    except: pass
