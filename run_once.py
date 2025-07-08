from datetime import datetime, timedelta, timezone
from scraper import fetch_forum_listing, fetch_latest_post, send_to_discord
from config import CATEGORIES, CHECK_INTERVAL_HOURS

def run():
    # timezone-aware UTC cut-off
    cutoff = datetime.now(timezone.utc) - timedelta(hours=CHECK_INTERVAL_HOURS)

    for cat in CATEGORIES:
        threads = fetch_forum_listing(cat["forum_url"])
        for tid, title, url, _ in threads:
            pid, text, images, post_time = fetch_latest_post(url)
            if post_time and post_time > cutoff:
                send_to_discord(cat["webhook_url"], title, text, url, images)

if __name__ == "__main__":
    run()
