"""
scrape_real_data.py
Real data scraper for the Pierce County / WA State paralegal assistant.

Targets:
  - pierce.county.codes  (Pierce County Code)
  - app.leg.wa.gov       (WA Revised Code)
  - piercecountywa.gov   (permit / DIY info)

Usage (PowerShell, inside .venv):
  pip install requests beautifulsoup4 playwright
  playwright install chromium          # one-time
  python scrape_real_data.py

Output:
  Saves .txt files to  my-assistant/data/
  Each file is ready for ingest.py to pick up.
"""

import os
import re
import time
import json
import logging
from pathlib import Path
from urllib.parse import urljoin

import requests
from requests import get
from requests.exceptions import RequestException
from bs4 import BeautifulSoup

# ── Config ──────────────────────────────────────────────────────────────────

DATA_DIR = Path("../my-assistant/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

DELAY = 1.5          # seconds between requests — be polite
PLAYWRIGHT_WAIT = 3  # seconds after page load for JS to settle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Pierce County Code sections to scrape ───────────────────────────────────
# (output_filename_stem, PCC_path, human_label)
PIERCE_SECTIONS = [
    # Noise ordinances
    ("pcc_8.72_noise_disturbance",   "8.72",      "PCC Ch. 8.72 — Motor Vehicle, Public Disturbance & Nuisance Noise"),
    ("pcc_8.76_noise_pollution",     "8.76",      "PCC Ch. 8.76 — Noise Pollution Control"),
    # Fences / setbacks / density (DIY build limits)
    ("pcc_18a.15_density_setbacks",  "18A.15",    "PCC Ch. 18A.15 — Density, Lot Dimensions & Setbacks"),
    # ADU / accessory structures
    ("pcc_18a.37_adu",               "18A.37",    "PCC Ch. 18A.37 — Accessory Development (ADU)"),
    # Building / fire codes
    ("pcc_17c.30_building_codes",    "17C.30",    "PCC Ch. 17C.30 — Building & Fire Codes"),
    # Animals (barking dog complaints, livestock)
    ("pcc_6.02_animals",             "6.02",      "PCC Ch. 6.02 — Animals"),
    # Landlord-tenant (county-level)
    ("pcc_8.12_civil_disturbance",   "8.12",      "PCC Ch. 8.12 — Civil Disturbance"),
]

# ── WA Revised Code chapters to scrape (full text) ──────────────────────────
RCW_CHAPTERS = [
    # ("rcw_59.18_landlord_tenant",   "59.18",  "RCW Ch. 59.18 — Residential Landlord-Tenant Act"),
    ("rcw_59.12_unlawful_detainer", "59.12",  "RCW Ch. 59.12 — Unlawful Detainer (Eviction)"),
    ("rcw_19.27_building_code",     "19.27",  "RCW Ch. 19.27 — State Building Code Act"),
    ("rcw_70.107_noise_control",    "70.107", "RCW Ch. 70.107 — Noise Control Act"),
    ("rcw_36.70a_growth_mgmt",      "36.70A", "RCW Ch. 36.70A — Growth Management Act (zoning authority)"),
]

# ── Pierce County permit / DIY pages ────────────────────────────────────────
PERMIT_PAGES = [
    (
        "pcc_permits_homeowner_guide",
        "https://www.piercecountywa.gov/1119/Building-Permits",
        "Pierce County Building Permits — Homeowner Guide",
    ),
    (
        "pcc_permits_when_required",
        "https://www.piercecountywa.gov/1124/When-Is-a-Permit-Required",
        "Pierce County — When Is a Permit Required?",
    ),
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def save_text(stem: str, label: str, source_url: str, text: str) -> Path:
    """Write scraped content to DATA_DIR/<stem>.txt and return the path."""
    dest = DATA_DIR / f"{stem}.txt"
    header = (
        f"SOURCE: {label}\n"
        f"URL: {source_url}\n"
        f"{'─' * 70}\n\n"
    )
    dest.write_text(header + text.strip(), encoding="utf-8")
    log.info("  ✓ Saved  %s  (%d chars)", dest.name, len(text))
    return dest


def fetch_html(url: str, use_playwright: bool = False) -> str | None:
    """
    Fetch raw HTML from url.
    Tries plain requests first; if content looks empty/JS-only and
    use_playwright=True is set, falls back to Playwright headless Chromium.
    """
    if use_playwright:
        return _playwright_fetch(url)

    try:
        resp = get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        return resp.text
    except RequestException as exc:
        log.warning("  requests failed for %s: %s", url, exc)
        return None


def _playwright_fetch(url: str) -> str | None:
    """Headless Chromium via Playwright — for JS-rendered pages."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("Playwright not installed. Run:  pip install playwright && playwright install chromium")
        return None

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(extra_http_headers={"Accept-Language": "en-US,en;q=0.9"})
        try:
            page.goto(url, wait_until="networkidle", timeout=30_000)
            time.sleep(PLAYWRIGHT_WAIT)
            html = page.content()
        except Exception as exc:
            log.warning("  Playwright failed for %s: %s", url, exc)
            html = None
        finally:
            browser.close()
    return html


def looks_empty(soup: BeautifulSoup) -> bool:
    """Return True if the page body appears to be a JS shell with no real text."""
    body_text = soup.get_text(separator=" ", strip=True)
    # Heuristic: real pages have > 200 chars of visible text
    return len(body_text) < 200


def clean_text(text: str) -> str:
    """Collapse whitespace runs while preserving paragraph breaks."""
    # Normalise line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove lines that are pure whitespace
    lines = [ln.rstrip() for ln in text.split("\n")]
    # Collapse 3+ blank lines into 2
    result, blanks = [], 0
    for ln in lines:
        if ln == "":
            blanks += 1
            if blanks <= 2:
                result.append(ln)
        else:
            blanks = 0
            result.append(ln)
    return "\n".join(result)


# ── Scrapers ─────────────────────────────────────────────────────────────────

def scrape_pierce_section(stem: str, pcc_path: str, label: str) -> bool:
    """
    Scrape a Pierce County Code chapter from pierce.county.codes.
    Tries requests first; falls back to Playwright if the page looks empty.
    """
    url = f"https://pierce.county.codes/PCC/{pcc_path}"
    log.info("Fetching PCC %s  →  %s", pcc_path, url)

    html = fetch_html(url)
    if html is None:
        log.info("  Retrying with Playwright …")
        html = fetch_html(url, use_playwright=True)
    if html is None:
        log.error("  Skipping — could not fetch %s", url)
        return False

    soup = BeautifulSoup(html, "html.parser")

    if looks_empty(soup):
        log.info("  Page looks JS-only, retrying with Playwright …")
        html = fetch_html(url, use_playwright=True)
        if html:
            soup = BeautifulSoup(html, "html.parser")

    # pierce.county.codes wraps content in several possible containers;
    # try them in order of specificity.
    content_selectors = [
        "div.chapterContent",
        "div.sectionContent",
        "main",
        "article",
        "div#content",
        "body",
    ]
    content = None
    for sel in content_selectors:
        content = soup.select_one(sel)
        if content and len(content.get_text(strip=True)) > 100:
            break

    if content is None:
        log.warning("  No usable content block found for %s", url)
        return False

    # Drop nav / sidebar noise
    for tag in content.select("nav, header, footer, script, style, .breadcrumb, .sidebar"):
        tag.decompose()

    text = clean_text(content.get_text(separator="\n"))
    save_text(stem, label, url, text)
    return True


def scrape_rcw_chapter(stem: str, cite: str, label: str) -> bool:
    """
    Scrape a full RCW chapter from app.leg.wa.gov.
    The ?full=true param returns the entire chapter as a single page.
    """
    url = f"https://app.leg.wa.gov/RCW/default.aspx?cite={cite}&full=true"
    log.info("Fetching RCW %s  →  %s", cite, url)

    html = fetch_html(url)
    if html is None:
        log.error("  Skipping — could not fetch %s", url)
        return False

    soup = BeautifulSoup(html, "html.parser")

    # RCW site puts the chapter text inside #contentWrapper or #rcwContent
    content_selectors = [
        "div#rcwContent",
        "div#contentWrapper",
        "div.chapterContent",
        "div#main-content",
        "main",
        "body",
    ]
    content = None
    for sel in content_selectors:
        content = soup.select_one(sel)
        if content and len(content.get_text(strip=True)) > 200:
            break

    if content is None:
        log.warning("  No usable content found for RCW %s", cite)
        return False

    for tag in content.select("script, style, nav, header, footer, .breadcrumb"):
        tag.decompose()

    text = clean_text(content.get_text(separator="\n"))

    # RCW full chapters can be very long — truncate to ~250 KB to stay
    # within ChromaDB chunk limits and keep ingestion fast.
    MAX_CHARS = 250_000
    if len(text) > MAX_CHARS:
        log.warning("  Truncating RCW %s from %d to %d chars", cite, len(text), MAX_CHARS)
        text = text[:MAX_CHARS] + "\n\n[… truncated — fetch individual sections for full text]"

    save_text(stem, label, url, text)
    return True


def scrape_permit_page(stem: str, url: str, label: str) -> bool:
    """Scrape a Pierce County permit info page (plain HTML)."""
    log.info("Fetching permit page  →  %s", url)

    html = fetch_html(url)
    if html is None:
        log.error("  Skipping — could not fetch %s", url)
        return False

    soup = BeautifulSoup(html, "html.parser")

    content_selectors = [
        "div.field-items",
        "div#content-area",
        "main",
        "div.region-content",
        "body",
    ]
    content = None
    for sel in content_selectors:
        content = soup.select_one(sel)
        if content and len(content.get_text(strip=True)) > 100:
            break

    if content is None:
        log.warning("  No content block for %s", url)
        return False

    for tag in content.select("script, style, nav, header, footer, form"):
        tag.decompose()

    text = clean_text(content.get_text(separator="\n"))
    save_text(stem, label, url, text)
    return True


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    results = {"success": [], "failed": []}

    log.info("=" * 60)
    log.info("STEP 1 — Pierce County Code sections (%d)", len(PIERCE_SECTIONS))
    log.info("=" * 60)
    for stem, path, label in PIERCE_SECTIONS:
        ok = scrape_pierce_section(stem, path, label)
        (results["success"] if ok else results["failed"]).append(stem)
        time.sleep(DELAY)

    log.info("=" * 60)
    log.info("STEP 2 — WA Revised Code chapters (%d)", len(RCW_CHAPTERS))
    log.info("=" * 60)
    for stem, cite, label in RCW_CHAPTERS:
        ok = scrape_rcw_chapter(stem, cite, label)
        (results["success"] if ok else results["failed"]).append(stem)
        time.sleep(DELAY)

    log.info("=" * 60)
    log.info("STEP 3 — Pierce County permit pages (%d)", len(PERMIT_PAGES))
    log.info("=" * 60)
    for stem, url, label in PERMIT_PAGES:
        ok = scrape_permit_page(stem, url, label)
        (results["success"] if ok else results["failed"]).append(stem)
        time.sleep(DELAY)

    # ── Summary ──────────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("DONE.  %d succeeded, %d failed.", len(results["success"]), len(results["failed"]))
    if results["failed"]:
        log.warning("Failed sources (will need Playwright or manual download):")
        for s in results["failed"]:
            log.warning("  • %s", s)
    log.info("")
    log.info("Next step:  cd my-assistant && python ingest.py")
    log.info("=" * 60)

    # Write a quick manifest so you know what was scraped
    manifest = DATA_DIR / "_scrape_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "success": results["success"],
                "failed": results["failed"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()