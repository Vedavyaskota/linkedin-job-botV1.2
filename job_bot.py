import requests
from bs4 import BeautifulSoup
import time
import re
import os

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# Keywords that signal C2C / contract roles
C2C_KEYWORDS = ["c2c", "corp to corp", "corp-to-corp", "contract", "1099", "w2/c2c", "w2 or c2c"]
EXPERIENCE_PATTERN = re.compile(r'\d+\+?\s*(?:years?|yrs?)', re.IGNORECASE)
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

def search_linkedin_jobs(keywords, location, num_jobs=50):
    jobs = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for start in range(0, num_jobs, 25):
        url = (
            f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={keywords}&location={location}&f_JT=C&start={start}"
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

def extract_info(description):
    emails = EMAIL_PATTERN.findall(description)
    experience = EXPERIENCE_PATTERN.findall(description)
    is_c2c = any(kw in description.lower() for kw in C2C_KEYWORDS)
    return emails, experience, is_c2c

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, json=payload)

def run():
    # Customize your search terms and location here
    searches = [
        ("software engineer C2C", "United States"),
        ("java developer contract", "Remote"),
        ("python developer corp to corp", "United States"),
    ]
    
    seen_ids = set()
    
    for keyword, location in searches:
        jobs = search_linkedin_jobs(keyword, location, num_jobs=50)
        for job in jobs:
            if job["job_id"] in seen_ids:
                continue
            seen_ids.add(job["job_id"])
            
            desc = get_job_details(job["job_id"])
            emails, experience, is_c2c = extract_info(desc)
            
           if not is_c2c:
               continue
            
            email_str = ", ".join(emails) if emails else "Not listed"
            exp_str = ", ".join(experience) if experience else "Not listed"
            
            msg = (
                f"🔔 <b>New C2C Job Alert!</b>\n\n"
                f"💼 <b>Title:</b> {job['title']}\n"
                f"🏢 <b>Company:</b> {job['company']}\n"
                f"📍 <b>Location:</b> {job['location']}\n"
                f"⏳ <b>Experience:</b> {exp_str}\n"
                f"📧 <b>Contact Email:</b> {email_str}\n"
                f"🔗 <b>Link:</b> {job['link']}\n"
            )
            
            send_telegram(msg)
            time.sleep(1)

if __name__ == "__main__":
    run()
