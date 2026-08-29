from playwright.sync_api import sync_playwright
import time
from typing import List
import random
import pandas as pd
from urllib.parse import urlencode, urljoin
from urllib.parse import urlparse, urlunparse
import sys

DOMAIN_FILE = "Saudi Arabia Website Longlist — 250 Domains.txt"

TOTAL_SESSION_TIME = 90
PRE_JAWWY_TIME = 20

def normalize_ga_cookie(client_id: str) -> str:
    if pd.isna(client_id):
        return ""
    s = str(client_id).strip()
    if not s or s.lower() == "nan":
        return ""
    if s.startswith("GA1.1."):
        s = s[6:]
    elif s.startswith("GA1."):
        parts = s.split(".")
        s = ".".join(parts[-2:]) if len(parts) >= 2 else s
    return f"GA1.1.{s}"


def clean_url(url):
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

def build_clean_utm_url(url, utm_params):
    parsed = urlparse(url)

    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        "",                      # params
        urlencode(utm_params),  # ONLY your UTMs
        ""                       # fragment
    ))
    
BLOCKED_URL = "https://www.jawwy.sa/content/jawwy/en/help.html"


def is_blocked_url(url):
    if not url:
        return False

    parsed = urlparse(url)

    blocked = urlparse(BLOCKED_URL)

    return (
        parsed.scheme == blocked.scheme
        and parsed.netloc == blocked.netloc
        and parsed.path.rstrip("/") == blocked.path.rstrip("/")
    )

import re
import random


def load_random_domains_by_category(count=3):
    try:
        with open(
            DOMAIN_FILE,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as file:
            lines = file.readlines()

        categories = {}
        current_category = None

        for line in lines:
            line = line.strip()

            if not line:
                continue

            # Category heading
            if line[0].isdigit() and ". " in line:
                parts = line.split(". ", 1)

                if len(parts) == 2:
                    possible_domain = parts[1].strip()

                    # If it looks like a domain, store it
                    if "." in possible_domain and " " not in possible_domain:
                        if current_category:
                            categories.setdefault(
                                current_category,
                                []
                            ).append(possible_domain)
                    else:
                        current_category = possible_domain

        available_categories = [
            category
            for category, domains in categories.items()
            if domains
        ]

        selected_categories = random.sample(
            available_categories,
            min(count, len(available_categories))
        )

        selected_domains = []

        for category in selected_categories:
            selected_domains.append(
                random.choice(categories[category])
            )

        return selected_domains

    except Exception as e:
        print(f"⚠️ Could not select random domains: {e}")
        return []


def visit_random_website(page, domain, duration):
    try:
        if not domain.startswith("http"):
            url = f"https://{domain}"
        else:
            url = domain

        print(f"🌐 Visiting: {url}")

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=20000
        )

        start_time = time.time()

        while time.time() - start_time < duration:

            try:
                # Random scroll
                page.mouse.wheel(
                    0,
                    random.randint(300, 900)
                )

                time.sleep(
                    random.uniform(2, 4)
                )

                # Occasionally scroll upward
                if random.random() < 0.3:
                    page.mouse.wheel(
                        0,
                        -random.randint(200, 600)
                    )

                    time.sleep(
                        random.uniform(1, 2)
                    )

            except Exception:
                break

    except Exception as e:
        print(f"⚠️ Failed to visit {domain}: {e}")

def generate_utm_traffic(client_ids: List[str], clientdata : dict, site_url: str, utm_params : dict):

    with sync_playwright() as p:
        
        browser = p.chromium.launch(
            headless=False,
            args=["--mute-audio"]
        )

        for raw_client_id in client_ids:
            ga_cookie_value = normalize_ga_cookie(raw_client_id)
            if not ga_cookie_value:
                continue

            context = browser.new_context(
                user_agent=clientdata[raw_client_id][0],
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True,
                proxy={
                    "server": "http://gw.dataimpulse.com:823",
                    "username": "72934cf642a202981e39",
                    "password": "23639d288a763301"
                },
            )
            
            context.add_cookies([
                {
                    "name": "_ga",
                    "value": ga_cookie_value,
                    "url": "https://www.jawwy.sa/",
                },
                {
                    "name": "_ga_T1MFHHPES0",
                    "value": clientdata[raw_client_id][1],
                    "url": "https://www.jawwy.sa/",
                }
            ])
            
            ALLOWED_HOSTS = {
                "www.jawwy.sa",
                "api.jawwy.sa",
            }

            GA_HOSTS = {
                "www.google-analytics.com",
                "analytics.google.com",
                "region1.analytics.google.com",
                "www.googletagmanager.com",
            }

            GOOGLE_SUPPORT_HOSTS = {
                "www.gstatic.com",
            }

            TAPPER_HOSTS = {
                "monitor.tapper.ai",
                "protect.tapper.ai",
                "fingerprint.tapper.ai",
            }
            
            
            def should_block(url):
                hostname = urlparse(url).hostname

                if not hostname:
                    return False

                hostname = hostname.lower()

                # Random website phase: allow everything
                if browsing_random_sites:
                    return False

                # Explicitly block Tapper
                if hostname in TAPPER_HOSTS:
                    return True

                # Allow GA + GTM
                if hostname in GA_HOSTS:
                    return False

                # Allow Google support resources
                if hostname in GOOGLE_SUPPORT_HOSTS:
                    return False

                # Allow Jawwy
                if hostname in ALLOWED_HOSTS:
                    return False

                # Block everything else
                return True
            
            context.route("**/*", lambda route: (
                route.abort() if should_block(route.request.url)
                else route.continue_()
            ))

            page = context.new_page()
            
            # Pick 3 domains from 3 different categories
            # Pick 3 domains from 3 different categories
            try:
                random_domains = load_random_domains_by_category(1)

                print("🌐 Selected websites:")

                for domain in random_domains:
                    print(f"   → {domain}")

            except Exception as e:
                print(f"⚠️ Could not select random domains: {e}")
                random_domains = []

            if random_domains:

                time_per_site = 10

                for domain in random_domains:

                    visit_random_website(
                        page,
                        domain,
                        duration=time_per_site
                    )
                    
            browsing_random_sites = False
            print("🔒 External browsing finished. Jawwy routing rules enabled.")

            target_url = f"{site_url}?{urlencode(utm_params)}"
            
            # print(f"Visiting {target_url} with client_id {raw_client_id} -> cookie {ga_cookie_value}")
            
            try:
                page.goto(
                    target_url,
                    wait_until="domcontentloaded",
                    timeout=45000
                )

            except Exception as e:
                print(f"⚠️ Could not open Jawwy page: {e}")
                context.close()
                continue
            


            time.sleep(5)
            
            session_start = time.time()
            MIN_SESSION_TIME = random.uniform(45, 50)


            clicked = set()

            while time.time() - session_start < MIN_SESSION_TIME:
                try:
                    tabs = page.query_selector_all(
                        "ul[class*='ProductCategoriesPicker'] li div[data-testid*='StyledOptionItem']"
                    )
                    if tabs:
                        random.choice(tabs[:4]).click(force=True)
                        time.sleep(random.uniform(2, 3))
                except Exception as e:
                    # print(f"Tab click error: {e}")
                    pass
                
                if random.random() < 0.3:
                    # print("🧍 User idle...")
                    time.sleep(random.uniform(5, 7))

                for _ in range(random.randint(4, 7)):
                    scroll_amount = random.randint(200, 600)
                    page.mouse.wheel(0, scroll_amount)
                    # time.sleep(random.uniform(2, 5))

                    try:
                        current_url = page.url

                        clickable_elements = page.query_selector_all(
                            "a[href*='/shop/'], a[href$='.html'], button, [onclick], [role='button']"
                        )

                        usable = []
                        for i, el in enumerate(clickable_elements[:30]):
                            try:
                                text = (el.inner_text() or "").strip()
                                href = el.get_attribute("href") or ""

                                if not href:
                                    continue

                                target_url = urljoin(page.url, href)

                                if is_blocked_url(target_url):
                                    print(f"🚫 Skipping blocked URL: {target_url}")
                                    # page.goto("https://www.jawwy.sa/content/jawwy/en/shop.html")
                                    continue
                                
                                key = f"{text}|{href}|{i}"
                                if key not in clicked:
                                    usable.append((key, el))
                            except:
                                continue
                        

                        if usable:
                            key, random_element = random.choice(usable)
                            clicked.add(key)
                            random_element.click(force=True)
                            time.sleep(random.uniform(2, 3))

                            if page.url != current_url:
                                if random.random() < 0.6:
                                    page.go_back(wait_until="domcontentloaded", timeout=15000)
                                    time.sleep(random.uniform(2, 3))

                                if random.random() < 0.25:
                                    page.go_forward(wait_until="domcontentloaded", timeout=15000)
                                    time.sleep(random.uniform(2, 3))

                    except Exception as e:
                        # print(f"Navigating....")
                        pass
                    
                time.sleep(random.uniform(4, 5))
                
            try:
                original_url = clientdata[raw_client_id][2]

                if not original_url:
                    print("⚠️ No final URL available, skipping final navigation")

                else:
                    final_url = build_clean_utm_url(
                        original_url,
                        utm_params
                    )

                    if is_blocked_url(final_url):
                        print(f"🚫 Blocked final navigation: {final_url}")

                        page.goto(
                            "https://www.jawwy.sa/content/jawwy/en/shop.html",
                            wait_until="domcontentloaded",
                            timeout=30000
                        )

                    else:
                        page.goto(
                            final_url,
                            wait_until="domcontentloaded",
                            timeout=30000
                        )

                    time.sleep(random.uniform(6, 8))

                    for _ in range(random.randint(2, 4)):
                        page.evaluate(
                            f"window.scrollBy(0, {random.randint(200, 800)})"
                        )
                        time.sleep(random.uniform(1.5, 3))

            except Exception as e:
                # print("Final navigation error:", e)
                pass
            

            context.close()
        
        browser.close()



if __name__ == '__main__':
    
    ga = sys.argv[1]
    ua = sys.argv[2]
    gs = sys.argv[3]
    url = sys.argv[4]
    site_url = (
        sys.argv[5]
        if len(sys.argv) > 5
        else "https://www.jawwy.sa/content/jawwy/en/shop.html"
    )
    flag = sys.argv[6]
    
    def_utm_params={
        "utm_source": "adintop",
        "utm_medium": "CPM",
        "utm_campaign": "Jawwy_AO_April_2026"
    }
    
    travel_utm_params={
        "utm_source": "adintop",
        "utm_medium": "CPM",
        "utm_campaign": "Jawwy_Travel_April_2026"
    }
    

    clientdata = {ga : [ua, gs, url]}

    client_ids = list(clientdata.keys())
    
    
    # print(f"Client IDs : {client_ids}")

    generate_utm_traffic(
        client_ids,
        clientdata,
        site_url=site_url,
        utm_params=def_utm_params if flag == "False" else travel_utm_params
    )
    
    # print("SESSIONS CREATED FOR :", ga)

