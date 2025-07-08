# run_once.py

import sys
from datetime import datetime, timedelta, timezone
from scraper import fetch_forum_listing, fetch_latest_post, send_to_discord
from config import CATEGORIES

def run():
    # Heutiges Datum in UTC
    today_utc = datetime.now(timezone.utc).date()

    for cat in CATEGORIES:
        name      = cat["name"]
        forum_url = cat["forum_url"]
        webhook   = cat["webhook_url"]

        print(f"\n[{name}] Prüfe neueste Threads…")
        try:
            threads = fetch_forum_listing(forum_url)
        except Exception as e:
            print(f"⚠️ Fehler Listing {forum_url}: {e}")
            continue

        if not threads:
            print("  → Keine Threads gefunden.")
            continue

        # 1) Den allerneuesten Thread aus dem Listing nehmen
        tid, title, url, last_list_time = threads[0]
        print(f"  → Neuster Thread im Listing: {title} (List-Time: {last_list_time})")

        # 2) Fetch des letzten Posts in diesem Thread
        try:
            pid, text, images, post_time = fetch_latest_post(url)
        except Exception as e:
            print(f"⚠️ Fehler fetch_latest_post für {url}: {e}")
            continue

        if not pid or not post_time:
            print("  → Kein Post im Thread.")
            continue

        # 3) Vergleiche Datum des Posts mit heute (UTC)
        post_date_utc = post_time.astimezone(timezone.utc).date()
        print(f"  → Letzter Post am {post_date_utc} (UTC)")

        if post_date_utc == today_utc:
            print(f"  → Poste an Discord: {title}")
            send_to_discord(webhook, title, text, url, images)
        else:
            print("  → Kein neuer Post heute.")

if __name__ == "__main__":
    run()
