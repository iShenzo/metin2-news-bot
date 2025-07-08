from scraper import fetch_forum_listing, fetch_latest_post, send_to_discord
from config import CATEGORIES

def initial():
    for cat in CATEGORIES:
        threads = fetch_forum_listing(cat["forum_url"])
        if not threads:
            print(f"⚠️ Keine Threads in {cat['name']}")
            continue

        tid, title, url, _ = threads[0]
        pid, text, images, _ = fetch_latest_post(url)
        if pid:
            print(f"→ Poste initial: [{cat['name']}] {title}")
            send_to_discord(cat["webhook_url"], title, text, url, images)
        else:
            print(f"⚠️ Thread {tid} hat keinen Post.")

if __name__=="__main__":
    initial()
