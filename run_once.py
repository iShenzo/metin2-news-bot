# run_once.py
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from scraper import fetch_forum_listing, fetch_latest_post, send_to_discord
from config import CATEGORIES

DB = "news.db"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
      CREATE TABLE IF NOT EXISTS threads (
        category     TEXT NOT NULL,
        thread_id    INTEGER NOT NULL,
        last_post_id INTEGER NOT NULL,
        PRIMARY KEY(category, thread_id)
      )
    """)
    return conn

def run():
    now_utc = datetime.now(timezone.utc)
    cutoff  = now_utc - timedelta(hours=1)
    print(f"► Run once @ {now_utc.isoformat()} – prüfe neue Posts seit {cutoff.isoformat()}")

    conn = init_db()
    c    = conn.cursor()

for cat in CATEGORIES:
    name    = cat["name"]
    webhook = cat["webhook_url"]

    if cat.get("single_thread"):
        # —— Nur dieser eine Thread: Wartungsarbeiten —— #
        url = cat["thread_url"]
        tid = int(url.rstrip("/").split("/")[-1].split("-")[0])

        # In DB eintragen, falls neu
        c.execute(
            "INSERT OR IGNORE INTO threads(category, thread_id, last_post_id) VALUES (?,?,0)",
            (name, tid)
        )
        conn.commit()

        post_id, text, images, post_time = fetch_latest_post(url)
        last_seen = c.execute(
            "SELECT last_post_id FROM threads WHERE category=? AND thread_id=?",
            (name, tid)
        ).fetchone()[0]

        if post_time > cutoff and post_id > last_seen:
            send_to_discord(webhook, name, text, url, images)
            c.execute(
                "UPDATE threads SET last_post_id=? WHERE category=? AND thread_id=?",
                (post_id, name, tid)
            )
            conn.commit()

    else:
        # —— Alle anderen Kategorien: iterate über _alle_ Threads —— #
        threads = fetch_forum_listing(cat["forum_url"])
        for tid, title, url, list_time in threads:
            c.execute(
                "INSERT OR IGNORE INTO threads(category, thread_id, last_post_id) VALUES (?,?,0)",
                (name, tid)
            )
            last_seen = c.execute(
                "SELECT last_post_id FROM threads WHERE category=? AND thread_id=?",
                (name, tid)
            ).fetchone()[0]

            post_id, text, images, post_time = fetch_latest_post(url)
            if post_time > cutoff and post_id > last_seen:
                send_to_discord(webhook, title, text, url, images)
                c.execute(
                    "UPDATE threads SET last_post_id=? WHERE category=? AND thread_id=?",
                    (post_id, name, tid)
                )
                conn.commit()
            else:
                print(f"[{name}] Kein neuer Post (letzter gesehen: #{last_seen}).")

        # ——— Normales Forum (Listing von Threads) ———
        else:
            print(f"\n[{name}] prüfe Forum-Listing…")
            try:
                threads = fetch_forum_listing(cat["forum_url"])
            except Exception as e:
                print(f"⚠️ [{name}] Listing-Fehler: {e}")
                continue

            if not threads:
                print(f"[{name}] → keine Threads gefunden.")
                continue

            # Wir nehmen nur den allerersten (jüngsten) Thread
            tid, title, url, list_time = threads[0]
            print(f"[{name}] Neuster Thread: “{title}” (ID {tid}, gelistet {list_time.isoformat()})")

            # Initialisiere DB-Eintrag, falls neu
            c.execute(
                "INSERT OR IGNORE INTO threads(category, thread_id, last_post_id) VALUES (?,?,0)",
                (name, tid)
            )
            conn.commit()

            # was haben wir zuletzt gesehen?
            c.execute(
                "SELECT last_post_id FROM threads WHERE category=? AND thread_id=?",
                (name, tid)
            )
            last_seen = c.fetchone()[0]

            # Hol’ den letzten Post in diesem Thread
            try:
                post_id, text, images, post_time = fetch_latest_post(url)
            except Exception as e:
                print(f"⚠️ [{name}] fetch_latest_post {url}: {e}")
                continue

            if not post_id or not post_time:
                print(f"[{name}] → kein Post gefunden.")
                continue

            # Sende nur, wenn wirklich neuer und in der letzten Stunde
            if post_time > cutoff and post_id > last_seen:
                print(f"[{name}] Neuer Post #{post_id} (Zeit {post_time.isoformat()}), sende an Discord…")
                send_to_discord(webhook, title, text, url, images)
                c.execute(
                    "UPDATE threads SET last_post_id=? WHERE category=? AND thread_id=?",
                    (post_id, name, tid)
                )
                conn.commit()
            else:
                print(f"[{name}] Kein neuer Post (letzter gesehen: #{last_seen}).")

    conn.close()
    print("\n► run_once abgeschlossen.")

if __name__ == "__main__":
    run()
