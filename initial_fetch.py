# initial_push.py
import sqlite3
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

def run_initial():
    conn = init_db()
    c    = conn.cursor()

    for cat in CATEGORIES:
        if cat.get("single_thread"):
            # nur der eine Thread
            url = cat["thread_url"]
            tid = int(url.rstrip("/").split("/")[-1].split("-")[0])
            post_id, _, _, _ = fetch_latest_post(url)
            c.execute(
                "INSERT OR REPLACE INTO threads(category, thread_id, last_post_id) VALUES (?,?,?)",
                (cat["name"], tid, post_id or 0)
            )
            print(f"[{cat['name']}] Seed: Thread {tid} → last_post_id={post_id}")
        else:
            # alle Threads im Listing
            threads = fetch_forum_listing(cat["forum_url"])
            for tid, title, url, _ in threads:
                post_id, _, _, _ = fetch_latest_post(url)
                c.execute(
                    "INSERT OR REPLACE INTO threads(category, thread_id, last_post_id) VALUES (?,?,?)",
                    (cat["name"], tid, post_id or 0)
                )
                print(f"[{cat['name']}] Seed: „{title}“ ({tid}) → last_post_id={post_id}")

    conn.commit()
    conn.close()
    print("Initial Seed abgeschlossen.")

if __name__ == "__main__":
    run_initial()
