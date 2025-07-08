import sys
from scraper import fetch_forum_listing, fetch_latest_post, send_to_discord
from config import CATEGORIES

def test_category(category_name, candidates=5, to_send=1):
    cat = next((c for c in CATEGORIES if c["name"] == category_name), None)
    if not cat:
        print(f"❌ Kategorie '{category_name}' nicht gefunden.")
        return

    threads = fetch_forum_listing(cat["forum_url"])
    print(f"→ Gefundene Threads (non-sticky): {len(threads)}. Prüfe die ersten {candidates}…")

    pool = []
    for tid, title, url, listing_time in threads[:candidates]:
        pid, text, images, post_time = fetch_latest_post(url)
        if pid and post_time:
            pool.append({
                "tid": tid,
                "title": title,
                "url": url,
                "text": text,
                "images": images,
                "post_time": post_time
            })
        else:
            print(f"  • Thread {tid} (‘{title}’) übersprungen (kein Datum/kein Post).")

    if not pool:
        print("⚠️ Keine Posts gefunden.")
        return

    pool.sort(key=lambda x: x["post_time"], reverse=True)

    for entry in pool[:to_send]:
        print(f"→ Sende Thread {entry['tid']} – {entry['title']} ({entry['post_time']})")
        send_to_discord(
            cat["webhook_url"],
            entry["title"],
            entry["text"],
            entry["url"],
            entry["images"]
        )
        print("  ✔️ gesendet.\n")

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "News - Itemshop"
    test_category(name, candidates=5, to_send=1)
