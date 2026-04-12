import requests
from bs4 import BeautifulSoup

url = "https://your-target-site.com/section"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

content = soup.find("div", class_="main-content")  # adjust to match the site
text = content.get_text(separator="\n", strip=True)

with open("data/scraped_content.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("Scrape complete. Data saved to data/scraped_content.txt")