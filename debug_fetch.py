# debug_fetch.py

import sys
from scraper import fetch_forum_listing, fetch_latest_post
from config import CATEGORIES

def debug_category(cat, max_threads):
    print(f"\n=== Kategorie: {cat['name']} ===")
    threads = fetch_forum_listing(cat["forum_url"])
    print(f"Gefundene Threads: {len(threads)} (zeige die ersten {max_threads})")
    for tid, title, url, last_listing_time in threads[:max_threads]:
        print(f"→ Thread {tid}: {title}")
        print(f"    Listing-Zeit: {last_listing_time}")
        pid, text, images, post_time = fetch_latest_post(url)
        if pid:
            print(f"    Neuer Post: ID={pid}, Zeit={post_time}, Bilder={len(images)}")
        else:
            print(f"    Kein Post gefunden.")
    print()

def main():
    # CLI-Argumente: Kategorie-Name (optional) und max_threads (optional)
    args = sys.argv[1:]
    category_name = None
    max_threads   = 5

    if args:
        category_name = args[0]
        if len(args) > 1:
            try:
                max_threads = int(args[1])
            except:
                pass

    if category_name:
        cat = next((c for c in CATEGORIES if c["name"] == category_name), None)
        if not cat:
            print(f"❌ Kategorie '{category_name}' nicht in config.py.")
            return
        debug_category(cat, max_threads)
    else:
        for cat in CATEGORIES:
            debug_category(cat, max_threads)

if __name__ == "__main__":
    main()
