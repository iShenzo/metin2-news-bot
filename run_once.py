# run_once.py

from datetime import datetime, timedelta
from scraper import fetch_forum_listing, fetch_latest_post, send_to_discord
from config import CATEGORIES, CHECK_INTERVAL_HOURS

def run():
    # Alle Posts der letzten CHECK_INTERVAL_HOURS Stunden
    cutoff = datetime.utcnow() - timedelta(hours=CHECK_INTERVAL_HOURS)

    for cat in CATEGORIES:
        threads = fetch_forum_listing(cat["forum_url"])
        for tid, title, url, _ in threads:
            pid, text, images, post_time = fetch_latest_post(url)
            # falls post_time in UTC vorliegt, convert falls nötig
            if post_time and post_time > cutoff:
                send_to_discord(cat["webhook_url"], title, text, url, images)

if __name__=="__main__":
    run()
