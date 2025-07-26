import os
import io
import threading
from flask import Flask, request, send_file, jsonify
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from urllib.parse import urlparse
import time

API_KEY = 'ThisIsTheAPIKey'  # Set in Render or Docker env

app = Flask(__name__)

# Global browser objects
playwright = None
browser = None
context = None
browser_initialized = False
visited_domains = set()
init_lock = threading.Lock()

@app.before_request
def ensure_browser_initialized():
    global browser_initialized, playwright, browser, context

    if not browser_initialized:
        with init_lock:
            if not browser_initialized:  # double-checked locking
                print("🚀 Initializing Playwright browser...")
                playwright = sync_playwright().start()

                browser = playwright.chromium.launch(
                    headless=False,
                    args=[
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--start-maximized',
                        '--disable-blink-features=AutomationControlled'
                    ],
                )
                
                context = browser.new_context(
                    viewport={"width": 1280, "height": 1280},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/115.0.0.0 Safari/537.36"
                    ),
                )
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                """)
                browser_initialized = True

@app.route("/screenshot")
def screenshot():
    t1 = time.time()
    key = request.args.get("key")
    if key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing URL parameter"}), 400
    
    domain = urlparse(url).netloc

    print(f"📸 Screenshot requested for: {url}")
    page = context.new_page()

    try:
        page.goto(url, timeout=120000, wait_until="load")
        if domain not in visited_domains:
            print(f"🔍 Handling cookie popup for domain: {domain}")
            handle_cookie_popup(page)
            visited_domains.add(domain)
        else:
            print(f"✅ Domain {domain} already visited. Skipping cookie popup.")

        # Screenshot to memory
        image_bytes = page.screenshot(type="jpeg", full_page=False, quality=80)
        print ('Request completed in - ', time.time() - t1)
        return send_file(io.BytesIO(image_bytes), mimetype="image/jpeg")

    except PlaywrightTimeoutError as e:
        return jsonify({"error": f"Timeout loading page: {e}"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        page.close()

        

def handle_cookie_popup(page):
    selectors = [
        'input#sp-cc-accept',
        'button#accept-cookies',
        'button.cookie-accept',
        'button:has-text("Accept")',
        'button:has-text("Agree")',
        'button:has-text("Got it")',
        'button:has-text("Allow all")',
        'text="Accept Cookies"',
        'text="I Agree"',
        'div.cookie-banner button.close',
    ]

    for selector in selectors:
        try:
            button = page.wait_for_selector(selector, timeout=10000)
            if button:
                button.click()
                page.wait_for_timeout(10000)
                print(f"✅ Cookie popup closed using: {selector}")
                break
        except:
            continue

if __name__ == "__main__":
    print("🔧 Starting Flask app...")
    app.run(host="0.0.0.0", port=5000, threaded=False)
