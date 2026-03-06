import xml.etree.ElementTree as ET
import requests
import time
import json

xml_file = 'animelist.xml' # Make sure this matches your file name
output_file = 'data.json'

tree = ET.parse(xml_file)
root = tree.getroot()

anime_database = []

print("Starting data enrichment... This will take a moment to respect API limits.")

for anime in root.findall('anime'):
    # Safely extract XML data
    animedb_id = anime.find('series_animedb_id')
    title = anime.find('series_title')
    status = anime.find('my_status')
    score = anime.find('my_score')

    if animedb_id is None or title is None:
        continue

    anime_data = {
        "id": animedb_id.text,
        "title": title.text,
        "status": status.text,
        "score": int(score.text) if score is not None and score.text.isdigit() else 0,
        "image": "",
        "genres": []
    }

    # Fetch rich data from Jikan API
    try:
        response = requests.get(f"https://api.jikan.moe/v4/anime/{anime_data['id']}")
        if response.status_code == 200:
            api_data = response.json().get('data', {})
            anime_data['image'] = api_data.get('images', {}).get('jpg', {}).get('large_image_url', '')
            anime_data['genres'] = [g['name'] for g in api_data.get('genres', [])]
            print(f"Fetched: {anime_data['title']}")
        else:
            print(f"Failed to fetch {anime_data['title']} - Status: {response.status_code}")
    except Exception as e:
        print(f"Error fetching {anime_data['title']}: {e}")

    anime_database.append(anime_data)
    
    # Sleep to strictly respect Jikan's 3 requests/second limit
    time.sleep(0.4) 

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(anime_database, f, ensure_ascii=False, indent=4)

print(f"\nSuccess! Rich data saved to {output_file}")