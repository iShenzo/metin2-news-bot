# run_once.py
import sqlite3
from datetime import datetime, timedelta, timezone
from scraper import fetch_forum_listing, fetch_latest_post, send_to_discord
from config import CATEGORIES

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
    return conn

def run():
    # 1) DB + Cursor
    conn = init_db()
    c    = conn.cursor()

    # 2) Zeitschwelle = jetzt minus 1 Stunde
    now_utc = datetime.now(timezone.utc)
    cutoff  = now_utc - timedelta(hours=1)
    print(f"► run_once @ {now_utc.isoformat()} – prüfe Posts nach {cutoff.isoformat()}")

    # 3) über alle Kategorien iterieren
    for cat in CATEGORIES:
        name    = cat["name"]
        webhook = cat["webhook_url"]

        # 3a) single_thread‐Fall (Wartungsarbeiten)
        if cat.get("single_thread"):
            url = cat["thread_url"]
            # Thread‐ID aus URL extrahieren
            tid = int(url.rstrip("/").split("/")[-1].split("-")[0])

            # DB‐Seed für diesen Thread, falls noch nicht vorhanden
            c.execute(
                "INSERT OR IGNORE INTO threads(category, thread_id, last_post_id) VALUES (?,?,0)",
                (name, tid)
            )
            conn.commit()

            # aktuellen letzten Post holen
            try:
                post_id, text, images, post_time = fetch_latest_post(url)
            except Exception as e:
                print(f"[{name}] Fehler beim Holen: {e}")
                continue

            # zuletzt gesehenen Post aus DB
            last_seen = c.execute(
                "SELECT last_post_id FROM threads WHERE category=? AND thread_id=?",
                (name, tid)
            ).fetchone()[0]

            # nur senden, wenn wirklich neuer als DB und neuer als cutoff
            if post_time and post_time > cutoff and post_id > last_seen:
                print(f"[{name}] Neuer Post #{post_id} (@{post_time.isoformat()}), sende…")
                send_to_discord(webhook, name, text, url, images)
                c.execute(
                    "UPDATE threads SET last_post_id=? WHERE category=? AND thread_id=?",
                    (post_id, name, tid)
                )
                conn.commit()
            else:
                print(f"[{name}] Kein neuer Post (letzter gesehen: #{last_seen}).")

        # 3b) reguläre Forum‐Kategorien
        else:
            print(f"\n[{name}] prüfe Forum‐Listing…")
            try:
                threads = fetch_forum_listing(cat["forum_url"])
            except Exception as e:
                print(f"[{name}] Listing‐Fehler: {e}")
                continue

            if not threads:
                print(f"[{name}] → keine Threads gefunden.")
                continue

            # **ALLE** Threads durchgehen und bei jedem neuen Post senden
            for tid, title, url, list_time in threads:
                # DB‐Seed für jeden neuen Thread
                c.execute(
                    "INSERT OR IGNORE INTO threads(category, thread_id, last_post_id) VALUES (?,?,0)",
                    (name, tid)
                )
                conn.commit()

                # zuletzt gesehenen Post aus DB
                last_seen = c.execute(
                    "SELECT last_post_id FROM threads WHERE category=? AND thread_id=?",
                    (name, tid)
                ).fetchone()[0]

                # aktuellen letzten Post holen
                try:
                    post_id, text, images, post_time = fetch_latest_post(url)
                except Exception as e:
                    print(f"[{name}] Fehler fetch_latest_post für {title}: {e}")
                    continue

                # wenn post_time existent, > cutoff und > last_seen → senden
                if post_time and post_time > cutoff and post_id > last_seen:
                    print(f"[{name}] Neuer Post in „{title}“ #{post_id} (@{post_time.isoformat()}), sende…")
                    send_to_discord(webhook, title, text, url, images)
                    c.execute(
                        "UPDATE threads SET last_post_id=? WHERE category=? AND thread_id=?",
                        (post_id, name, tid)
                    )
                    conn.commit()
                else:
                    print(f"[{name}] „{title}“ – kein neuer Post (letzter gesehen: #{last_seen}).")

    conn.close()
    print("► run_once abgeschlossen.")

if __name__ == "__main__":
    run()
