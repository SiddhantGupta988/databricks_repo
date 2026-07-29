"""
Naukri Profile Auto-Refresher — Plain Python Version

Logs into Naukri and toggles a trailing character in your Profile Summary,
then saves it — refreshing the "Last updated" timestamp.

⚠️ Automating logins to a third-party site like Naukri may violate their Terms of Service.
Use at your own risk, on your own account.
"""

import os
import time
import logging
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

# ----------------------------
# 1. Config — credentials + paths
# ----------------------------
NAUKRI_EMAIL = os.getenv("NAUKRI_EMAIL")
NAUKRI_PASSWORD = os.getenv("NAUKRI_PASSWORD")

DEBUG_MODE = True  # Set True for first manual run
STATE_DIR = Path("./naukri_auto")  # local folder for session + logs

STATE_DIR.mkdir(parents=True, exist_ok=True)
log_dir = STATE_DIR / "logs"
log_dir.mkdir(exist_ok=True)
state_file = STATE_DIR / "naukri_session.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_dir / f"run_{datetime.now():%Y-%m-%d}.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("naukri")


def screenshot(page, name):
    path = log_dir / f"{name}_{datetime.now():%Y%m%d_%H%M%S}.png"
    try:
        page.screenshot(path=str(path), full_page=True)
        log.info(f"Saved debug screenshot: {path}")
    except Exception as e:
        log.warning(f"Could not save screenshot: {e}")


def is_logged_in(page) -> bool:
    page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)
    return "login" not in page.url.lower() and "nlogin" not in page.url.lower()


def login(page):
    log.info("Logging in...")
    page.goto("https://www.naukri.com/nlogin/login", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_selector("#Email ID / Username", timeout=15000)
    page.fill("#Email ID / Username", NAUKRI_EMAIL)
    page.fill("#Password", NAUKRI_PASSWORD)
    page.click("button[type='submit']")

    time.sleep(4)
    if page.locator("text=OTP").count() > 0 or page.locator("text=verification").count() > 0:
        screenshot(page, "otp_prompt")
        raise RuntimeError("Naukri is asking for OTP/verification — unattended automation may not work.")

    page.wait_for_load_state("domcontentloaded", timeout=20000)
    if "login" in page.url.lower():
        screenshot(page, "login_failed")
        raise RuntimeError("Login appears to have failed — check credentials or screenshot.")
    log.info("Login successful.")


def toggle_summary(page):
    log.info("Navigating to profile...")
    page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    edit_selectors = [
        "span[title='Edit Profile Summary']",
        "div.profileSummary span.edit",
        "text=Profile Summary >> xpath=../..//span[contains(@class,'edit')]",
    ]

    edit_btn = None
    for sel in edit_selectors:
        loc = page.locator(sel)
        if loc.count() > 0:
            edit_btn = loc.first
            break

    if edit_btn is None:
        screenshot(page, "summary_edit_button_not_found")
        raise RuntimeError("Could not find the Profile Summary edit button.")

    edit_btn.click()
    time.sleep(2)

    textarea = page.locator("textarea").first
    textarea.wait_for(timeout=10000)
    current_text = textarea.input_value()

    if current_text.rstrip().endswith("."):
        new_text = current_text.rstrip()[:-1]
    else:
        new_text = current_text.rstrip() + "."

    textarea.fill(new_text)
    time.sleep(1)

    save_selectors = ["button:has-text('Save')", "button[type='submit']"]
    saved = False
    for sel in save_selectors:
        loc = page.locator(sel)
        if loc.count() > 0:
            loc.first.click()
            saved = True
            break

    if not saved:
        screenshot(page, "save_button_not_found")
        raise RuntimeError("Could not find the Save button.")

    time.sleep(3)
    log.info("Profile summary toggled and saved.")


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context_kwargs = {}
        if state_file.exists():
            context_kwargs["storage_state"] = str(state_file)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        try:
            if not state_file.exists() or not is_logged_in(page):
                login(page)
            toggle_summary(page)
            context.storage_state(path=str(state_file))
            log.info("Session saved for next run.")
            print("SUCCESS: Naukri profile refreshed.")
        except Exception as e:
            log.error(f"Run failed: {e}")
            screenshot(page, "failure")
            print(f"FAILED: {e}")
            raise
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    run()
