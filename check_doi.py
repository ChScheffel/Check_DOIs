import re
import sys
import time
import requests
from urllib.parse import quote

# --- CONFIGURATION ---
USER_AGENT = "DOIChecker/1.0 (mailto:christoph_scheffel@tu-dresden.de)"  # <-- Replace with your email!
CROSSREF_API = "https://api.crossref.org/works/"
DOI_ORG_URL = "https://doi.org/"
REQUEST_TIMEOUT = 10
RETRY_DELAY = 2
MAX_RETRIES = 3
SLEEP_BETWEEN = 0.5

# --- DOI EXTRACTION REGEX ---
DOI_REGEX = re.compile(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', re.IGNORECASE)
TRAILING_PUNCT = '.,;)'

def extract_dois(text):
    matches = DOI_REGEX.findall(text)
    dois = [m.rstrip(TRAILING_PUNCT) for m in matches]
    return list(dict.fromkeys(dois))  # Deduplicate, preserve order

def check_doi_crossref(doi):
    url = CROSSREF_API + quote(doi)
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                title = data.get("message", {}).get("title", [""])[0]
                return ("ACCESSIBLE", title)
            elif resp.status_code == 404:
                return ("NOT FOUND / DOES NOT EXIST", "")
            elif resp.status_code == 429:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            else:
                return (f"ERROR (HTTP {resp.status_code})", "")
        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            return (f"ERROR ({str(e)})", "")
    return ("ERROR (Max retries reached)", "")

def check_doi_doi_org(doi):
    url = DOI_ORG_URL + quote(doi)
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.head(url, headers=headers, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        if resp.status_code in (200, 302):
            return "ACCESSIBLE"
        elif resp.status_code == 404:
            return "NOT FOUND / DOES NOT EXIST"
        else:
            return f"ERROR (HTTP {resp.status_code})"
    except requests.RequestException as e:
        return f"ERROR ({str(e)})"

def main():
    print("Paste your reference section below. Finish input with a blank line or Ctrl+D:\n")
    lines = []
    try:
        while True:
            line = input()
            if not line.strip():
                break
            lines.append(line)
    except EOFError:
        pass
    text = "\n".join(lines)
    dois = extract_dois(text)
    if not dois:
        print("\nNo DOIs found in the input.")
        return

    print(f"\nFound {len(dois)} unique DOI(s):\n")
    results = []
    for idx, doi in enumerate(dois, 1):
        print(f"[{idx}] Checking DOI: {doi} ...", end=" ")
        status, title = check_doi_crossref(doi)
        if status.startswith("ERROR"):
            # Fallback to doi.org
            status = check_doi_doi_org(doi)
            title = ""
        results.append((doi, status, title))
        print(status + (f" | Title: {title}" if title else ""))
        time.sleep(SLEEP_BETWEEN)

    # --- REPORT ---
    print("\n" + "="*60)
    print("DOI Accessibility Report")
    print("="*60)
    accessible = 0
    not_found = 0
    errors = 0
    for idx, (doi, status, title) in enumerate(results, 1):
        print(f"{idx}. {doi}")
        print(f"   Status: {status}")
        if title:
            print(f"   Title: {title}")
        if status == "ACCESSIBLE":
            accessible += 1
        elif status == "NOT FOUND / DOES NOT EXIST":
            not_found += 1
        else:
            errors += 1
    print("-"*60)
    print(f"Total DOIs checked: {len(dois)}")
    print(f"  Accessible: {accessible}")
    print(f"  Not found: {not_found}")
    print(f"  Errors: {errors}")

    main()