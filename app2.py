import os
import io
import threading
from flask import Flask, request, send_file, jsonify
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from urllib.parse import urlparse
import time
import psutil

API_KEY = 'ThisIsTheAPIKey'  # Set in Render or Docker env

app = Flask(__name__)

# Global browser objects
playwright = None
browser = None
context = None
cks = None
browser_initialized = False
visited_domains = set()
init_lock = threading.Lock()

def log_memory_usage(note=""):
    process = psutil.Process(os.getpid())
    mem_mb = process.memory_info().rss / 1024 / 1024  # RSS = Resident Set Size
    print(f"🧠 Memory usage {note}: {mem_mb:.2f} MB")

def total_memory_usage(note=""):
    parent = psutil.Process(os.getpid())
    children = parent.children(recursive=True)
    total = parent.memory_info().rss
    for child in children:
        try:
            total += child.memory_info().rss
        except psutil.NoSuchProcess:
            pass
    print(f"🧠 Total memory (including Chromium) {note}: {total / 1024 / 1024:.2f} MB")    

@app.before_request
def ensure_browser_initialized():
    global browser_initialized, playwright, browser, context

    if not browser_initialized:
        with init_lock:
            if not browser_initialized:  # double-checked locking
                print("🚀 Initializing Playwright browser...")

                t = time.time()
                playwright = sync_playwright().start()
                print('initiate playwright - ', time.time()-t)
                
                t = time.time()
                browser = playwright.chromium.launch(headless=False)
                print('initiate browser - ', time.time()-t)
                
                t = time.time()
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
                
                if cks != None:
                    context.add_cookies(cks)
                print('initiate context - ', time.time()-t)    

                browser_initialized = False                

@app.route("/screenshot")
def screenshot():
    global cks
    total_memory_usage("before request")
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
        t = time.time()
        page.goto(url, timeout=120000, wait_until="load")
        print('page load - ', time.time()-t)
        if domain not in visited_domains:
            print(f"🔍 Handling cookie popup for domain: {domain}")
            t = time.time()
            handle_cookie_popup(page)
            print('handle cookies - ', time.time()-t)
            visited_domains.add(domain)
        else:
            print(f"✅ Domain {domain} already visited. Skipping cookie popup.")

        # Screenshot to memory
        t = time.time()
        image_bytes = page.screenshot(type="jpeg", full_page=False, quality=80)
        print('screenshot - ', time.time()-t)
        print ('Request completed in - ', time.time() - t1)
        return send_file(io.BytesIO(image_bytes), mimetype="image/jpeg")

    except PlaywrightTimeoutError as e:
        return jsonify({"error": f"Timeout loading page: {e}"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        total_memory_usage("before page close")
        page.close()
        total_memory_usage("after page close")
        cks = context.cookies()
        context.close()
        total_memory_usage("after context close")
        browser.close()
        total_memory_usage("after browser close")
        playwright.stop()
        total_memory_usage("after closing everything")

        

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
                page.wait_for_timeout(5000)
                print(f"✅ Cookie popup closed using: {selector}")
                break
        except:
            continue

if __name__ == "__main__":
    print("🔧 Starting Flask app...")
    app.run(host="0.0.0.0", port=5000, threaded=False)
