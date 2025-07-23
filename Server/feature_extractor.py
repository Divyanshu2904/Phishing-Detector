import re
import socket
import ssl
import whois
import requests
import tldextract
import dns.resolver
import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

# Suppress warnings
import logging
logging.getLogger("whois").setLevel(logging.CRITICAL)
from bs4 import XMLParsedAsHTMLWarning
import warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def analyze_behavior_with_browser(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-http2"]  # ✅ Prevent HTTP2 protocol errors
            )
            page = browser.new_page()
            page.goto(url, timeout=60000)  # ✅ 60 sec timeout for slow pages

            # Safe form analysis
            try:
                form_locator = page.locator("form")
                if form_locator.count() > 0:
                    first_form_action = form_locator.first.get_attribute("action", timeout=10000) or ""
                else:
                    first_form_action = ""
            except Exception as e:
                print("⚠️ Form analysis failed:", e)
                first_form_action = ""

            has_password_input = page.locator("input[type='password']").count() > 0
            right_click_disabled = page.evaluate("document.oncontextmenu !== null")

            browser.close()
            return [
                int(has_password_input),
                int(first_form_action in ["", "#", None]),
                int(right_click_disabled)
            ]
    except Exception as e:
        print(f"⚠️ Browser analysis failed: {e}")
        return [0, 0, 0]


def extract_features_from_url(url):
    print(f"🔍 Extracting from: {url}")
    features = []

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        path = parsed.path or ""
        domain_info = tldextract.extract(url)
        domain = domain_info.registered_domain
        subdomain = domain_info.subdomain or ""

        # -------------------------------
        # 1–17: Basic URL-based features
        # -------------------------------
        try:
            features += [
                len(url),
                len(hostname),
                len(path),
                url.count('-'),
                url.count('@'),
                url.count('.'),
                url.count('//'),
                url.lower().count('https'),
                url.lower().count('http'),
                url.count('%'),
                url.count('='),
                url.count('?'),
                1 if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", hostname) else 0,
                len(subdomain.split('.')),
                len(domain_info.suffix),
                path.count('/'),
                1 if any(k in url.lower() for k in ['login', 'secure', 'account', 'update', 'bank', 'verify']) else 0
            ]
        except:
            features += [0] * (17 - len(features))

        # -----------------------------------
        # 18. DNS Record
        # -----------------------------------
        try:
            dns.resolver.resolve(hostname, 'A')
            features.append(0)
        except:
            features.append(1)

        # -----------------------------------
        # 19. SSL Certificate
        # -----------------------------------
        try:
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(socket.socket(), server_hostname=hostname) as s:
                s.settimeout(5)
                s.connect((hostname, 443))
                s.getpeercert()
                features.append(0)
        except:
            features.append(1)

        # -----------------------------------
        # 20–21: WHOIS
        # -----------------------------------
        try:
            w = whois.whois(domain)
            created = w.creation_date
            expiry = w.expiration_date
            if isinstance(created, list): created = created[0]
            if isinstance(expiry, list): expiry = expiry[0]
            now = datetime.datetime.now()
            features += [
                (now - created).days if created else -1,
                (expiry - now).days if expiry else -1
            ]
        except:
            features += [-1, -1]

        # -----------------------------------
        # 22–30: Page content
        # -----------------------------------
        try:
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.content, "html.parser")
            all_links = soup.find_all('a', href=True)
            external_links = [l for l in all_links if not urlparse(l['href']).netloc == hostname]
            internal_links = [l for l in all_links if urlparse(l['href']).netloc == hostname or l['href'].startswith('/')]
            total_links = len(all_links)
            external_ratio = len(external_links) / total_links if total_links else 0

            features += [
                len(soup.find_all('form')),
                len(soup.find_all('input')),
                len(soup.find_all('script')),
                len(soup.find_all('iframe')),
                len(external_links),
                len(internal_links),
                external_ratio,
                len(soup.find_all('input', {'type': 'hidden'})),
                len(soup.find_all('input', {'type': 'submit'}))
            ]
        except:
            features += [0] * 9

        # -----------------------------------
        # 31–40: Suspicious keywords in text
        # -----------------------------------
        try:
            text = soup.get_text().lower()
            for word in ['password', 'login', 'verify', 'ssn', 'credit card', 'debit card', 'cvv', 'otp', 'netbanking', 'security']:
                features.append(1 if word in text else 0)
        except:
            features += [0] * 10

        # -----------------------------------
        # 41–43: Real browser analysis (Playwright)
        # -----------------------------------
        features += analyze_behavior_with_browser(url)

        # -----------------------------------
        # 44–48: Placeholder
        # -----------------------------------
        features += [0] * 5

        # ✨ Final sanity
        if len(features) > 48:
            features = features[:48]
        while len(features) < 48:
            features.append(0)

    except Exception as e:
        print("❌ Feature extraction failed for", url, "→", e)
        return [0] * 48

    return features
