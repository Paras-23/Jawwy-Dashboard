from playwright.sync_api import sync_playwright
import time
from typing import List
import random
import pandas as pd
from urllib.parse import urlencode, urljoin
from urllib.parse import urlparse, urlunparse
import sys


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
                ignore_https_errors=True
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

            page = context.new_page()
            

            target_url = f"{site_url}?{urlencode(utm_params)}"
            
            # print(f"Visiting {target_url} with client_id {raw_client_id} -> cookie {ga_cookie_value}")
            
            page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
            


            time.sleep(5)
            
            session_start = time.time()
            MIN_SESSION_TIME = random.uniform(100, 120)


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
                    time.sleep(random.uniform(8, 15))

                for _ in range(random.randint(4, 7)):
                    scroll_amount = random.randint(200, 600)
                    page.mouse.wheel(0, scroll_amount)
                    time.sleep(random.uniform(2, 5))

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
                    
                time.sleep(random.uniform(4, 8))
                
            try:
                original_url = clientdata[raw_client_id][2]

                # if not original_url:
                #     # print("❌ Missing original URL, skipping")
                #     pass
                # else:
                #     final_url = build_clean_utm_url(original_url, utm_params)
                #     # print(f"🔁 Navigating to final page: {final_url}")
                
                if original_url:
                    final_url = build_clean_utm_url(original_url, utm_params)

                # page.goto(final_url, wait_until="domcontentloaded")
                if is_blocked_url(final_url):
                    print(f"🚫 Blocked final navigation: {final_url}")
                    page.goto("https://www.jawwy.sa/content/jawwy/en/shop.html")
                else:
                    page.goto(
                        final_url,
                        wait_until="domcontentloaded"
                    )
                time.sleep(random.uniform(8, 15))

                # Light interaction
                for _ in range(random.randint(2, 4)):
                    page.evaluate(f"window.scrollBy(0, {random.randint(200, 800)})")
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

