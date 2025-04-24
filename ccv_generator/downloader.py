import os
import json
import requests
from pathlib import Path
from platformdirs import user_cache_dir
from datetime import datetime, timedelta

APP_NAME = "CCCVGenerator"
CACHE_DIR = Path(user_cache_dir(APP_NAME))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ETAG_FILE = CACHE_DIR / "etag.json"
CHECK_INTERVAL = timedelta(days=15)  # Define 15-day interval

def load_etags():
    """Load ETags and last checked timestamps from a local metadata file."""
    if ETAG_FILE.exists():
        with open(ETAG_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}  # Return an empty dict if JSON is corrupted
    return {}

def save_etags(etags):
    """Save ETags and last checked timestamps to a local metadata file."""
    with open(ETAG_FILE, "w") as f:
        json.dump(etags, f, indent=4)  # Pretty-print for debugging

def retrieve_cached_file(url):
    """Download a file if it is missing or has changed, checking every 15 days."""
    filename = CACHE_DIR / os.path.basename(url)
    etags = load_etags()

    # Ensure the entry for this URL is a dictionary
    if not isinstance(etags.get(url), dict):
        etags[url] = {}

    headers = {}

    # Get last checked timestamp and ETag (if available)
    last_checked = etags[url].get("last_checked")
    etag = etags[url].get("etag")

    # Convert last_checked timestamp to datetime object
    if last_checked:
        last_checked = datetime.fromisoformat(last_checked)

    if  filename.exists():
        # If the file exists, only check if 15 days have passed
        if last_checked and datetime.now() - last_checked < CHECK_INTERVAL:
            return filename

        # Add If-None-Match header if an ETag exists
        if etag:
            headers["If-None-Match"] = etag

    response = requests.get(url, headers=headers, stream=True)

    if response.status_code == 200:
        # Save the new file
        with open(filename, "wb") as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        print(f"Downloaded {filename.name}")

        # Store new ETag and update last checked time
        etags[url] = {
            "etag": response.headers.get("ETag", ""),
            "last_checked": datetime.now().isoformat()
        }
        save_etags(etags)
    else:
        response.raise_for_status()

    return filename