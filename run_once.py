import sys
from datetime import datetime, timedelta, timezone
from scraper import fetch_forum_listing, fetch_latest_post, send_to_discord
from config import CATEGORIES
import sqlite3

DB = "news.db"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
      CREATE TABLE IF NOT EXISTS threads (
        category     TEXT,
        thread_id    INTEGER,
        last_post_id INTEGER,
        PRIMARY KEY(category, thread_id)
      )
    """)
    return conn

def run():
    now_utc = datetime.now(timezone.utc)
    cutoff  = now_utc - timedelta(hours=1)
    print(f"► Run once @ {now_utc.isoformat()} – Posts nach {cutoff.isoformat()} prüfen")

    conn = init_db()
    c    = conn.cursor()

    for cat in CATEGORIES:
        name    = cat["name"]
        webhook = cat["webhook_url"]

        # 1) single_thread-Mode?
        if cat.get("single_thread"):
            url = cat["thread_url"]
            # Thread-ID aus der URL extrahieren (hier 56068)
            tid = int(url.rstrip("/").split("/")[-1].split("-")[0])

            # sicherstellen, dass wir einen Eintrag haben
            c.execute(
                "INSERT OR IGNORE INTO threads(category, thread_id, last_post_id) VALUES (?,?,0)",
                (name, tid)
            )
            conn.commit()

            # letzten Post holen
            try:
                post_id, text, images, post_time = fetch_latest_post(url)
            except Exception as e:
                print(f"⚠️ Wartungsarbeiten fetch error: {e}")
                continue

            # check gegen DB
            c.execute(
                "SELECT last_post_id FROM threads WHERE category=? AND thread_id=?",
                (name, tid)
            )
            last_seen = c.fetchone()[0]

            if post_id and post_id > last_seen:
                print(f"[{name}] Neuer Post #{post_id}, sende an Discord…")
                send_to_discord(webhook, name, text, url, images)
                c.execute(
                    "UPDATE threads SET last_post_id=? WHERE category=? AND thread_id=?",
                    (post_id, name, tid)
                )
                conn.commit()
            else:
                print(f"[{name}] Kein neuer Post (letzter={last_seen}).")

        # 2) normaler Forum-Mode
        else:
            print(f"\n[{name}] Prüfe Forum-Listing…")
            try:
                threads = fetch_forum_listing(cat["forum_url"])
            except Exception as e:
                print(f"⚠️ Listing-Fehler {cat['forum_url']}: {e}")
                continue

            if not threads:
                print("  → Keine Threads gefunden.")
                continue

            # nimm immer den aktuellsten Thread
            tid, title, url, last_list_time = threads[0]
            print(f"  → Neuster Thread: {title} ({last_list_time})")

            try:
                post_id, text, images, post_time = fetch_latest_post(url)
            except Exception as e:
                print(f"⚠️ fetch_latest_post {url}: {e}")
                continue

            if not post_id or not post_time:
                print("  → Kein Post im Thread.")
                continue

            # nur Posts in der letzten Stunde
            if post_time > cutoff:
                print(f"  → Neuer Post seit {cutoff.time()}: {title}")
                send_to_discord(webhook, title, text, url, images)
            else:
                print("  → Kein neuer Post in der letzten Stunde.")

    conn.close()

if __name__ == "__main__":
    run()
