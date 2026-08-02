import os
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

def get_api_keys():
    load_dotenv(override=True)
    pexels = os.getenv("PEXELS_API_KEY", "")
    pixabay = os.getenv("PIXABAY_API_KEY", "")
    return pexels, pixabay

def fetch_pexels_video(keyword: str, output_path: str) -> Optional[str]:
    """Sourcing vertical B-roll video from Pexels API."""
    pexels_key, _ = get_api_keys()
    if not pexels_key:
        print("Warning: PEXELS_API_KEY missing.")
        return None

    headers = {"Authorization": pexels_key}
    url = f"https://api.pexels.com/videos/search?query={keyword}&orientation=portrait&per_page=5"

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            videos = data.get("videos", [])
            for v in videos:
                files = v.get("video_files", [])
                # Pick 1080x1920 or highest quality mp4
                for vf in files:
                    if vf.get("file_type") == "video/mp4" and vf.get("width", 0) >= 720:
                        video_url = vf.get("link")
                        r = requests.get(video_url, stream=True)
                        with open(output_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=1024*1024):
                                f.write(chunk)
                        return output_path
    except Exception as e:
        print(f"Pexels fetch failed for '{keyword}': {e}")
    return None

def fetch_pixabay_video(keyword: str, output_path: str) -> Optional[str]:
    """Fallback Sourcing B-roll video from Pixabay API."""
    _, pixabay_key = get_api_keys()
    if not pixabay_key:
        print("Warning: PIXABAY_API_KEY missing.")
        return None

    url = f"https://pixabay.com/api/videos/?key={pixabay_key}&q={keyword}&video_type=film&per_page=5"

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            hits = data.get("hits", [])
            if hits:
                video_url = hits[0]["videos"]["large"]["url"]
                r = requests.get(video_url, stream=True)
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        f.write(chunk)
                return output_path
    except Exception as e:
        print(f"Pixabay fetch failed for '{keyword}': {e}")
    return None

def download_broll_asset(keyword: str, output_path: str) -> Optional[str]:
    """Attempts Pexels first, falls back to Pixabay."""
    res = fetch_pexels_video(keyword, output_path)
    if not res:
        res = fetch_pixabay_video(keyword, output_path)
    return res
