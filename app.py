from flask import Flask, request, send_file, jsonify
from playwright.sync_api import sync_playwright
from io import BytesIO
import time
from functools import wraps

app = Flask(__name__)

API_KEY = 'ThisIsTheAPIKey'

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.args.get("apikey")
        if key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def take_stealth_screenshot(url):
    buffer = BytesIO()
    with sync_playwright() as p:
        print('launching browser')
        browser = p.chromium.launch(
            headless=False,  # This works now with xvfb
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            ),
            java_script_enabled=True,
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        page = context.new_page()

        page.route("**/*", lambda route, request: 
            route.abort() if request.resource_type in ["image", "stylesheet"] else route.continue_()
        )
        
        page.goto(url, timeout=120000)
        print('starting sleep')
        time.sleep(20)
        print('sleep ended')

        #try:
        #    print('waiting for h1')
        #    page.wait_for_selector('h1, .product-title', timeout=2000)
        #except:
        #    print('wait timed out')
        #    pass

        print('look for cookie popup')
        handle_cookie_popup(page)

        screenshot_bytes = page.screenshot(type='jpeg', quality=80)
        buffer.write(screenshot_bytes)
        buffer.seek(0)

        browser.close()
    return buffer

def handle_cookie_popup(page):
    # List of common selectors for cookie banners/buttons
    selectors = [
        'input#sp-cc-accept',                   # amazon
        'button:has-text("Allow all")',
        'button#accept-cookies',                # example id
        'button.cookie-accept',                 # example class
        'button:has-text("Accept")',            # text-based selector (Playwright supports this)
        'button:has-text("Agree")',
        'button:has-text("Got it")',        
        'text="Accept Cookies"',
        'text="I Agree"',
        'div.cookie-banner button.close',      # common close button
    ]

    for selector in selectors:
        try:
            print('found selector')
            # Wait briefly for the popup button to appear
            button = page.wait_for_selector(selector, timeout=20000)
            if button:
                button.click()
                print(f"Cookie popup accepted/closed with selector: {selector}")
                # Wait a moment for popup to go away
                page.wait_for_timeout(20000)
                return True
        except:
            # Selector not found, try next
            continue
    print("No cookie popup detected or handled.")
    return False  

@app.route('/screenshot', methods=['GET'])
@require_api_key
def screenshot_endpoint():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing URL'}), 400
    try:
        image_stream = take_stealth_screenshot(url)
        return send_file(image_stream, mimetype='image/jpeg')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(host='0.0.0.0', port=5000, debug=True)
