"""
scrape_title18.py — Iteratively scrape all /PCC/18* pages from pierce.county.codes.

Strategy:
  1. Load the TOC page (/PCC/contents) and harvest every href matching /PCC/18*
  2. Deduplicate and sort the discovered URLs
  3. Visit each URL with Playwright, extract #main text
  4. Save each page as an individual .txt file in ./data/title18/
  5. Write a manifest JSON

Usage:
    python scrape_title18.py

Output:
    data/title18/<name>.txt       — one file per page
    data/_scrape_manifest.json    — appended log via scrape_manifest_json
"""

import os
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from scrape_manifest_json import log_scrape

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL    = "https://pierce.county.codes"
TOC_URL     = "https://pierce.county.codes/PCC/contents"
PATTERN     = re.compile(r"^/PCC/18", re.IGNORECASE)   # wildcard: /PCC/18*
OUTPUT_DIR  = Path("data/title18")
DELAY_SEC   = 1.5   # polite crawl delay between pages

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# ── Helpers ───────────────────────────────────────────────────────────────────
def safe_filename(text: str) -> str:
    """Strip characters that are unsafe in Windows filenames."""
    return re.sub(r'[<>:"/|?*\\]', "_", text).strip()


def url_to_slug(url: str) -> str:
    """Fallback filename from URL path: PCC_18A.35.010"""
    path = urlparse(url).path
    slug = path.strip("/").replace("/", "_")
    return safe_filename(slug) or "unknown"


def extract_page(html: str) -> tuple[str, str]:
    """
    Parse the page HTML and return (filename_stem, main_text).

    Filename stem is built from <h4 class="inner-header">:
        <span class="num">Chapter 18.20</span>
        <span class="name">INTRODUCTION</span>
    → "Chapter_18.20_Introduction"

    Falls back to the URL slug if the header isn't found.
    """
    soup = BeautifulSoup(html, "html.parser")

    # ── Derive filename from inner-header ────────────────────────────────────
    filename_stem = ""
    header = soup.select_one("h4.inner-header")
    if header:
        num  = (header.select_one("span.num")  or header).get_text(strip=True)
        name = (header.select_one("span.name") or header).get_text(strip=True)
        # Combine and normalise: spaces → underscores, title-case the name part
        combined = f"{num}_{name.title()}"
        filename_stem = safe_filename(combined).replace(" ", "_")

    # ── Extract #main text ───────────────────────────────────────────────────
    for tag in soup.select("header, footer, nav, .global-header, .global-footer, script, style"):
        tag.decompose()

    main = (
        soup.select_one("#main")
        or soup.select_one("main")
        or soup.select_one("[role='main']")
        or soup.select_one(".field-items")
        or soup.body
    )
    text = main.get_text(separator="\n", strip=True) if main else ""

    return filename_stem, text


def discover_links(page, toc_url: str) -> list[str]:
    """
    Load the TOC page and harvest all unique hrefs matching /PCC/18*.
    Returns a sorted list of absolute URLs.
    """
    print(f"Loading TOC: {toc_url}")
    page.goto(toc_url, wait_until="networkidle", timeout=60_000)
    page.wait_for_timeout(4_000)   # let JS finish rendering

    html  = page.content()
    soup  = BeautifulSoup(html, "html.parser")

    found = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Normalise relative paths
        if href.startswith("/"):
            if PATTERN.match(href):
                found.add(BASE_URL + href)
        elif href.startswith(BASE_URL):
            path = urlparse(href).path
            if PATTERN.match(path):
                found.add(href)

        if len(found) >= 1:
            print("  → Maximum link limit reached.")
            break

    urls = sorted(found)
    print(f"  → {len(urls)} /PCC/18* links discovered\n")
    return urls


def scrape_page(page, url: str) -> tuple[str, str] | tuple[None, None]:
    """
    Navigate to a single URL and return (filename_stem, text).
    Returns (None, None) on failure.
    """
    try:
        page.goto(url, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(2_000)
        return extract_page(page.content())
    except Exception as exc:
        print(f"  [error] {url}: {exc}")
        return None, None


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    counts = {"success": 0, "failed": 0, "skipped": 0}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            user_agent=UA,
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # ── Step 1: discover ─────────────────────────────────────────────────
        urls = discover_links(page, TOC_URL)

        if not urls:
            print(
                "No /PCC/18* links found on the TOC page.\n"
                "The site may require interaction to expand the TOC tree.\n"
                "Trying the direct Title 18 page as a fallback seed..."
            )
            # Fallback: seed from the title-level page itself
            urls = [f"{BASE_URL}/PCC/18"]

        # ── Step 2: iterate ──────────────────────────────────────────────────
        total = len(urls)
        for i, url in enumerate(urls, 1):
            fallback_slug = url_to_slug(url)

            print(f"[{i}/{total}] {url}")

            # Check if this URL was already scraped (scan for matching fallback slug
            # in case the header-named file exists from a prior run)
            existing = list(OUTPUT_DIR.glob(f"*{fallback_slug}*.txt"))
            if existing:
                print(f"  [skip] already scraped → {existing[0].name}")
                log_scrape(url, existing[0].name, "skipped")
                counts["skipped"] += 1
                time.sleep(0.2)
                continue

            filename_stem, text = scrape_page(page, url)

            # Use header-derived name; fall back to URL slug if header wasn't found
            stem     = filename_stem if filename_stem else fallback_slug
            out_file = OUTPUT_DIR / f"{stem}.txt"

            if text and len(text.strip()) > 50:
                header_line = f"=== {url} ===\n"
                content = header_line + text + "\n"
                out_file.write_text(content, encoding="utf-8")
                log_scrape(url, out_file.name, "success")
                counts["success"] += 1
                print(f"  ✓ {len(text):,} chars → {out_file.name}")
            else:
                log_scrape(url, "", "failed")
                counts["failed"] += 1
                print(f"  ✗ empty or too short — skipped")

            time.sleep(DELAY_SEC)

        browser.close()

    print(
        f"\nSummary: {counts['success']} scraped, "
        f"{counts['skipped']} skipped, "
        f"{counts['failed']} failed"
    )


if __name__ == "__main__":
    main()