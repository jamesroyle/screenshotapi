from fastapi import FastAPI, Query, Response
from fastapi.responses import FileResponse
from playwright.sync_api import sync_playwright
import uuid
import os

app = FastAPI()

def take_screenshot(url, output_path):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            '--disable-blink-features=AutomationControlled'
        ])
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        page = context.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)

        try:
            page.screenshot(path=output_path, type='jpeg', quality=80, full_page=True)
        finally:
            browser.close()

@app.get("/screenshot")
def screenshot(url: str = Query(...)):
    filename = f"screenshot-{uuid.uuid4().hex}.jpg"
    output_path = f"/tmp/{filename}"

    try:
        take_screenshot(url, output_path)
        return FileResponse(output_path, media_type="image/jpeg", filename="screenshot.jpg")
    except Exception as e:
        return Response(content=f"Error: {str(e)}", status_code=500)