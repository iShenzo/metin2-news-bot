import sys
from datetime import datetime, timedelta, timezone
from scraper import fetch_forum_listing, fetch_latest_post, send_to_discord
from config import CATEGORIES

def run():
    now_utc   = datetime.now(timezone.utc)
    cutoff    = now_utc - timedelta(hours=1)
    print(f"► Run once @ {now_utc.isoformat()} – teile nur Posts nach {cutoff.isoformat()} UTC")

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

        tid, title, url, last_list_time = threads[0]
        print(f"  → Neuster Thread im Listing: {title} (List-Time: {last_list_time})")

        try:
            pid, text, images, post_time = fetch_latest_post(url)
        except Exception as e:
            print(f"⚠️ Fehler fetch_latest_post für {url}: {e}")
            continue

        if not pid or not post_time:
            print("  → Kein Post im Thread.")
            continue

        post_date_utc = post_time.astimezone(timezone.utc).date()
        print(f"  → Letzter Post am {post_date_utc} (UTC)")

        if post_time and post_time > cutoff:
            print(f"  → Neuer Post seit {cutoff.time()} UTC: {title}")
            send_to_discord(webhook, title, text, url, images)
        else:
            print("  → Kein neuer Post in der letzten Stunde.")

if __name__ == "__main__":
    run()
