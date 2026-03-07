import xml.etree.ElementTree as ET
import requests
import time
import json

xml_file = 'animelist.xml'
output_file = 'data.json'

tree = ET.parse(xml_file)
root = tree.getroot()

anime_database = []
failed = []

print("Starting data enrichment... This will take a moment to respect API limits.\n")

for anime in root.findall('anime'):
    animedb_id = anime.find('series_animedb_id')
    title_raw   = anime.find('series_title')
    status      = anime.find('my_status')
    score       = anime.find('my_score')

    if animedb_id is None or title_raw is None:
        continue

    mal_id = animedb_id.text

    anime_data = {
        "id":     mal_id,
        "title":  title_raw.text,          # fallback — will be overwritten if API succeeds
        "status": status.text if status is not None else "Unknown",
        "score":  int(score.text) if score is not None and score.text.isdigit() else 0,
        "image":  "",
        "genres": []
    }

    # ── Fetch from Jikan ────────────────────────────────────────────────────
    try:
        resp = requests.get(
            f"https://api.jikan.moe/v4/anime/{mal_id}",
            timeout=10
        )

        if resp.status_code == 200:
            api = resp.json().get('data', {})

            # ── English title priority order ─────────────────────────────────
            # 1. title_english  (e.g. "Your Lie in April")
            # 2. title          (romaji, usually readable)
            # 3. Original XML title as last resort
            eng = api.get('title_english') or ''
            romaji = api.get('title') or ''

            anime_data['title'] = (eng.strip() or romaji.strip()) or anime_data['title']

            # Cover image
            anime_data['image'] = (
                api.get('images', {})
                   .get('jpg', {})
                   .get('large_image_url', '')
            )

            # Genres
            anime_data['genres'] = [g['name'] for g in api.get('genres', [])]

            print(f"  [OK] {mal_id:>6}  →  {anime_data['title']}")

        elif resp.status_code == 404:
            print(f"  [404] {mal_id:>6}  →  {anime_data['title']} (not found on MAL)")

        elif resp.status_code == 429:
            # Rate limited — back off and retry once
            print(f"  [429] Rate limited. Waiting 5s before retrying {mal_id}…")
            time.sleep(5)
            resp2 = requests.get(f"https://api.jikan.moe/v4/anime/{mal_id}", timeout=10)
            if resp2.status_code == 200:
                api = resp2.json().get('data', {})
                eng    = api.get('title_english') or ''
                romaji = api.get('title') or ''
                anime_data['title']  = (eng.strip() or romaji.strip()) or anime_data['title']
                anime_data['image']  = api.get('images', {}).get('jpg', {}).get('large_image_url', '')
                anime_data['genres'] = [g['name'] for g in api.get('genres', [])]
                print(f"  [OK] {mal_id:>6}  →  {anime_data['title']} (after retry)")
            else:
                print(f"  [FAIL] {mal_id:>6}  →  retry gave {resp2.status_code}")
                failed.append(mal_id)

        else:
            print(f"  [ERR] {mal_id:>6}  →  HTTP {resp.status_code}")
            failed.append(mal_id)

    except requests.exceptions.Timeout:
        print(f"  [TIMEOUT] {mal_id:>6}  →  skipping")
        failed.append(mal_id)
    except Exception as e:
        print(f"  [EXCEPTION] {mal_id:>6}  →  {e}")
        failed.append(mal_id)

    anime_database.append(anime_data)

    # Jikan allows ~3 req/s — 0.4s sleep keeps us safely under that
    time.sleep(0.4)

# ── Write output ─────────────────────────────────────────────────────────────
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(anime_database, f, ensure_ascii=False, indent=4)

print(f"\n✓ Done! {len(anime_database)} entries written to {output_file}")

if failed:
    print(f"\n⚠  {len(failed)} entries failed to fetch:")
    for fid in failed:
        print(f"   MAL ID {fid}  →  https://myanimelist.net/anime/{fid}")
    print("\nYou can re-run the script or look these up manually.")