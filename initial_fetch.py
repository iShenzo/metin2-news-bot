# initial_push.py

import sqlite3
from scraper import fetch_forum_listing, fetch_latest_post, send_to_discord
from config import CATEGORIES
import requests

DB = "news.db"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
      CREATE TABLE IF NOT EXISTS threads (
        category     TEXT    NOT NULL,
        thread_id    INTEGER NOT NULL,
        last_post_id INTEGER NOT NULL,
        PRIMARY KEY(category, thread_id)
      )
    """)
    conn.commit()
    return conn

def initial_push():
    conn = init_db()
    c    = conn.cursor()

    for cat in CATEGORIES:
        name    = cat["name"]
        webhook = cat["webhook_url"]

        # Single‑thread‑Fall (Wartungsarbeiten)
        if cat.get("single_thread"):
            url = cat["thread_url"]
            tid = int(url.rstrip("/").split("/")[-1].split("-")[0])

            try:
                post_id, text, images, post_time = fetch_latest_post(url)
            except requests.HTTPError as he:
                print(f"⚠️ [{name}] HTTPError beim Einlesen von {url}: {he}")
                continue
            except Exception as e:
                print(f"⚠️ [{name}] Fehler beim Einlesen von {url}: {e}")
                continue

            if not post_id:
                print(f"⚠️ [{name}] Kein Post gefunden im Wartungs‑Thread.")
                continue

            print(f"→ [{name}] Initial sende Post #{post_id}")
            send_to_discord(webhook, name, text, url, images)

            c.execute(
                "INSERT OR REPLACE INTO threads(category, thread_id, last_post_id) VALUES (?,?,?)",
                (name, tid, post_id)
            )
            conn.commit()

        # Normale Kategorien
        else:
            try:
                threads = fetch_forum_listing(cat["forum_url"])
            except requests.HTTPError as he:
                print(f"⚠️ [{name}] HTTPError beim Listing: {he}")
                continue
            except Exception as e:
                print(f"⚠️ [{name}] Fehler beim Listing: {e}")
                continue

            if not threads:
                print(f"⚠️ [{name}] Keine Threads im Listing.")
                continue

            # wir nehmen nur den neuesten Thread zum Initial-Push
            tid, title, url, _ = threads[0]

            try:
                post_id, text, images, post_time = fetch_latest_post(url)
            except requests.HTTPError as he:
                print(f"⚠️ [{name}] HTTPError beim Einlesen von Thread {tid}: {he}")
                continue
            except Exception as e:
                print(f"⚠️ [{name}] Fehler beim Einlesen von Thread {tid}: {e}")
                continue

            if not post_id:
                print(f"⚠️ [{name}] Thread {tid} hat keinen Post.")
                continue

            print(f"→ [{name}] Initial sende Thread “{title}” Post #{post_id}")
            send_to_discord(webhook, title, text, url, images)

            c.execute(
                "INSERT OR REPLACE INTO threads(category, thread_id, last_post_id) VALUES (?,?,?)",
                (name, tid, post_id)
            )
            conn.commit()

    conn.close()
    print("✅ initial_push abgeschlossen.")

if __name__ == "__main__":
    initial_push()
