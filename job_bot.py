import requests
from bs4 import BeautifulSoup
import time
import re
import os
import json
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

SEEN_FILE = "seen_jobs.json"

C2C_KEYWORDS = ["c2c", "corp to corp", "corp-to-corp", "c2c only", "corp2corp"]

DOTNET_KEYWORDS = [
    ".net", "dotnet", "dot net", "asp.net", "c#", "csharp",
    ".net core", ".net developer", ".net engineer", "blazor",
    "wpf", "winforms", "entity framework"
]

EXPERIENCE_PATTERN = re.compile(r'\d+\+?\s*(?:years?|yrs?)', re.IGNORECASE)
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

def load_seen_ids():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen_ids(seen_ids):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen_ids), f)

def search_linkedin_jobs(keywords, location, num_jobs=50):
    jobs = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for start in range(0, num_jobs, 25):
        url = (
            f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={keywords}&location={location}&f_JT=C&f_TPR=r86400&start={start}"
        )
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_="base-card")
            for card in cards:
                title = card.find("h3", class_="base-search-card__title")
                company = card.find("h4", class_="base-search-card__subtitle")
                location_el = card.find("span", class_="job-search-card__location")
                link_el = card.find("a", class_="base-card__full-link")
                job_id = card.get("data-entity-urn", "").split(":")[-1]
                jobs.append({
                    "title": title.text.strip() if title else "N/A",
                    "company": company.text.strip() if company else "N/A",
                    "location": location_el.text.strip() if location_el else "N/A",
                    "link": link_el["href"] if link_el else "",
                    "job_id": job_id
                })
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(2)
    return jobs

def get_job_details(job_id):
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        desc_el = soup.find("div", class_="description__text")
        return desc_el.get_text(" ", strip=True) if desc_el else ""
    except:
        return ""

def is_dotnet_job(title, description):
    text = (title + " " + description).lower()
    return any(kw in text for kw in DOTNET_KEYWORDS)

def is_c2c_job(description):
    text = description.lower()
    return any(kw in text for kw in C2C_KEYWORDS)

def extract_info(description):
    emails = EMAIL_PATTERN.findall(description)
    experience = EXPERIENCE_PATTERN.findall(description)
    return emails, experience

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

def run():
    searches = [
        (".Net developer C2C", "United States"),
        (".Net developer corp to corp", "United States"),
        (".Net C2C", "United States"),
        ("dotNet C2C", "United States"),
        ("C# developer C2C", "United States"),
        ("ASP.NET C2C", "United States"),
        (".Net core contract", "United States"),
    ]

    # Load previously seen job IDs from file
    seen_ids = load_seen_ids()
    print(f"Loaded {len(seen_ids)} previously seen jobs")
    sent_count = 0

    for keyword, location in searches:
        print(f"Searching: {keyword}")
        jobs = search_linkedin_jobs(keyword, location, num_jobs=50)
        print(f"Found {len(jobs)} jobs for: {keyword}")

        for job in jobs:
            if job["job_id"] in seen_ids:
                print(f"Skipped (already sent): {job['title']}")
                continue

            desc = get_job_details(job["job_id"])

            # Filter 1 — must be a .NET job
            if not is_dotnet_job(job["title"], desc):
                print(f"Skipped (not .NET): {job['title']}")
                seen_ids.add(job["job_id"])
                continue

            # Filter 2 — must mention C2C
            if not is_c2c_job(desc):
                print(f"Skipped (no C2C): {job['title']}")
                seen_ids.add(job["job_id"])
                continue

            emails, experience = extract_info(desc)
            email_str = ", ".join(emails) if emails else "Not listed"
            exp_str = ", ".join(experience) if experience else "Not listed"

            msg = (
                f"🔔 <b>New .NET C2C Job Alert!</b>\n\n"
                f"💼 <b>Title:</b> {job['title']}\n"
                f"🏢 <b>Company:</b> {job['company']}\n"
                f"📍 <b>Location:</b> {job['location']}\n"
                f"⏳ <b>Experience:</b> {exp_str}\n"
                f"📧 <b>Contact Email:</b> {email_str}\n"
                f"🔗 <b>Link:</b> {job['link']}\n"
            )

            send_telegram(msg)
            seen_ids.add(job["job_id"])
            sent_count += 1
            print(f"Sent ({sent_count}): {job['title']} at {job['company']}")
            time.sleep(1)

    # Save updated seen IDs back to file
    save_seen_ids(seen_ids)
    print(f"Done. Total sent: {sent_count}. Total seen IDs saved: {len(seen_ids)}")

if __name__ == "__main__":
    run()
