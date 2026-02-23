import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import os
from datetime import datetime, timedelta

MAX_PRICE = 10000000
CACHE_FILE = "ads_cache.json"

def load_cached_ads():
    """Load cached ads from file with timestamp tracking"""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
                return {
                    ad['id']: {
                        **ad,
                        'first_seen': ad.get('first_seen', datetime.now().isoformat()),
                        'last_seen': ad.get('last_seen', datetime.now().isoformat())
                    }
                    for ad in cache.get('ads', [])
                }
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Cache loading error, starting fresh: {e}")
    return {}

def save_cached_ads(ads_dict):
    """Save ads to cache file with metadata"""
    cache_data = {
        'last_updated': datetime.now().isoformat(),
        'ads': [
            {
                **ad,
                'first_seen': ad.get('first_seen', datetime.now().isoformat()),
                'last_seen': ad.get('last_seen', datetime.now().isoformat())
            }
            for ad in ads_dict.values()
        ]
    }
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        print(f"Error saving cache: {e}")

def watch_ads(url, use_cache=True):
    """Main function to scrape and monitor ads with cache support"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    try:
        cached_ads = load_cached_ads() if use_cache else {}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        current_ads = []
        for item in soup.find_all('li', class_='item'):
            try:
                title_tag = item.find('h2').find('a')
                ad_url = urljoin(url, title_tag.get('href', '').strip())
                ad_id = ad_url.split('-')[-1]
                
                price_text = item.find('div', class_='boxintxt b').get_text(strip=True)
                try:
                    price = int(''.join(filter(str.isdigit, price_text or '0')))
                except:
                    price = 0         

                if price > MAX_PRICE:
                    continue
                
                current_ads.append({
                    'id': ad_id,
                    'title': title_tag.get('title', '').strip(),
                    'url': ad_url,
                    'price': price_text,
                    'price_numeric': price,
                    'location': item.find('div', class_='boxintxt').get_text(strip=True),
                    'mileage': item.find_all('div', class_='boxintxt')[2].get_text(strip=True),
                    'date': item.find('div', class_='boxintxt s').get_text(strip=True),
                    'image': urljoin(url, item.find('img')['src']) if item.find('img') else None
                })
            except Exception as e:
                print(f"Error processing listing: {e}")
                continue
        
        if use_cache:
            new_ads = [ad for ad in current_ads if ad['id'] not in cached_ads]
            for ad in current_ads:
                cached_ads[ad['id']] = ad
            save_cached_ads(cached_ads)
            return new_ads
        return current_ads        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return []
