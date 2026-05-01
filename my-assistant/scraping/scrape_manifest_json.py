import json
import os
from datetime import datetime

MANIFEST_PATH = "data/_scrape_manifest.json"


def log_scrape(url: str, output_file: str, status: str):
    if os.path.exists(MANIFEST_PATH) and os.path.getsize(MANIFEST_PATH) > 0:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = []

    manifest.append({
        "datetime":    datetime.now().isoformat(),
        "output_file": output_file,
        "url":         url,
        "status":      status,
    })

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)