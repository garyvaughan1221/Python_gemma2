from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from urllib.parse import urljoin
import os
import json
import re
from scrape_manifest_json import log_scrape
import copy
import re

url = "https://www.piercecountywa.gov/971/What-Is-Allowed-in-a-Zone"
base_url = "https://www.piercecountywa.gov"
stem = "What-Is-Allowed-in-a-Zone"
output_file = f"data/{stem}.txt"

os.makedirs("data", exist_ok=True)

# ── Known nav link labels to strip (site menu noise) ────────────────────────
NAV_NOISE = {
    "home", "government", "departments h-z", "planning & public works",
    "development center", "parcel & property information",
    "get info about my property or project", "permitting forms (a to z)",
    "online development guide", "administrative appeals",
    "affordable housing incentives", "ask the development center",
    "build or demolish something", "residential", "platted lot program",
    "commercial", "get a fire permit", "get a sewer permit",
    "get a health department permit", "development services directory",
    "environmental decisions", "environmental review",
    "executive priority permitting program", "fire prevention bureau",
    "fire inspections", "fire permits", "fire investigations", "food trucks",
    "outdoor burning", "fireworks", "fire safety", "arson",
    "holiday fire safety", "fire code violations", "about us",
    "find forms and documents", "frequently asked questions",
    "impact fee deferral program",
    "land use, land division, civil infrastructure, shorelines",
    "permitting with pierce county education series", "request a refund",
    "sewer", "site plan resources", "traffic impact fees",
    "what is allowed in a zone?",
}

# ── Playwright fetch ──────────────────────────────────────────────────────────
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
    )
    page = context.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    page.goto(url, wait_until="load", timeout=60000)
    page.wait_for_timeout(3000)
    html = page.content()
    browser.close()

# ── Parse ─────────────────────────────────────────────────────────────────────
soup = BeautifulSoup(html, "html.parser")

# Strip global chrome
for tag in soup.select("header, footer, nav, script, style, .global-footer, .global-header, .breadcrumb, #top-nav"):
    tag.decompose()

main = soup.select_one("main, #main-content, [role='main'], .field-items")



def inline_links(tag, base_url):
    """Replace <a> tags with 'label (url)' then return clean text."""
    tag = copy.copy(tag)
    for a in tag.find_all('a'):
        href = a.get('href', '')
        label = a.get_text(strip=True)
        if href and not href.startswith('#'):
            full = urljoin(base_url, href) if href.startswith('/') else href
            replacement = f"{label} ({full})" if label else full
        else:
            replacement = label
        a.replace_with(replacement)
    return re.sub(r'\s+', ' ', tag.get_text(separator=' ', strip=True))


def node_to_lines(node, base_url, nav_noise):
    """
    Recursively convert a BS4 node to clean lines.
    Handles h*, p, li explicitly — recurses into containers.
    Avoids double-processing by returning early on terminal elements.
    """

    if isinstance(node, NavigableString):
        return []
    if not isinstance(node, Tag):
        return []

    name = node.name

    # Skip non-content tags entirely
    if name in ('script', 'style', 'nav', 'header', 'footer', 'img', 'form'):
        return []

    # Headings
    if name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        text = node.get_text(strip=True)
        if text and text.lower() not in nav_noise:
            return [f"\n{text.upper()}"]
        return []

    # List items — skip bare URLs and nav noise
    if name == 'li':
        label = node.get_text(strip=True)
        if label.lower() in nav_noise:
            return []
        text = inline_links(node, base_url)
        # Skip bare URLs with no meaningful label
        if re.match(r'^https?://', text.strip()):
            return []
        if text:
            return [f"  - {text}"]
        return []

    # Paragraphs — detect <strong>-only paragraphs as headings
    if name == 'p':
        real_children = [c for c in node.children if not (isinstance(c, NavigableString) and not c.strip())]
        if len(real_children) == 1 and hasattr(real_children[0], 'name') and real_children[0].name == 'strong':
            text = real_children[0].get_text(strip=True)
            if text and text.lower() not in nav_noise:
                return [f"\n{text.upper()}"]
            return []
        text = inline_links(node, base_url)
        if text and text.lower() not in nav_noise:
            return [text]
        return []

    # Everything else (div, ul, ol, section, article, etc.) — recurse
    lines = []
    for child in node.children:
        lines.extend(node_to_lines(child, base_url, nav_noise))
    return lines

# ── Extract clean text with link inlining and nav noise filtering ───────────────────────────────────────────────────
def extract_clean_text(element, base_url, nav_noise):
    lines = node_to_lines(element, base_url, nav_noise)
    # Collapse 3+ blank lines to 2
    output, blanks = [], 0
    for ln in lines:
        if ln.strip() == "":
            blanks += 1
            if blanks <= 2:
                output.append(ln)
        else:
            blanks = 0
            output.append(ln)
    return "\n".join(output)


# ── Build output ──────────────────────────────────────────────────────────────
header = (
    f"SOURCE: Pierce County — What Is Allowed in a Zone?\n"
    f"URL: {url}\n"
    f"{'─' * 70}\n"
)

body = extract_clean_text(main, base_url, NAV_NOISE) if main else "[No content found]"
output = header + "\n" + body

# ── Save ──────────────────────────────────────────────────────────────────────
try:
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"✓ Saved to {output_file}")
    log_scrape(url=url, output_file=output_file, status="success")
except Exception as e:
    print(f"✗ Failed: {e}")
    log_scrape(url=url, output_file=output_file, status="failed")