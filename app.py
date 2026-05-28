import base64
import os
import re
import time

from flask import Flask, render_template, jsonify, request

import automation
import config
import main
import database

app = Flask(__name__)

QR_SELECTORS = [
    "canvas[aria-label='Scan me!']",
    "div[data-testid='qrcode']",
    "div[aria-label='Scan me']",
    "img[alt='Scan me']",
    "canvas[data-ref]",
    "div[data-ref] canvas",
]

LINKED_SESSION_SELECTORS = [
    "#pane-side",
    "div[data-testid='chat-list-search']",
    "div[aria-label='Chat list']",
    "header [data-testid='menu']",
]

PHONE_LINK_SELECTORS = [
    "text=Link with phone number",
    "a:has-text('Link with phone number')",
    "button:has-text('Link with phone number')",
    "div[role='button']:has-text('Link with phone number')",
]

PHONE_NUMBER_INPUT_SELECTORS = [
    "input[type='tel']",
    "input[inputmode='tel']",
    "input[autocomplete='tel']",
    "input[aria-label*='Phone']",
    "input[aria-label*='phone']",
    "input[placeholder*='Phone']",
    "input[placeholder*='phone']",
]

PAIRING_CODE_SELECTORS = [
    "[aria-details='link-device-phone-number-code-screen-instructions']",
    "div[aria-details='link-device-phone-number-code-screen-instructions']",
    "[data-testid='link-device-phone-number-code']",
    "[data-testid='link-device-phone-number-code-screen-instructions']",
]

NEXT_BUTTON_SELECTORS = [
    "button:has-text('Next')",
    "div[role='button']:has-text('Next')",
    "span:has-text('Next')",
]

PAIRING_CODE_PATTERN = re.compile(r"\b([A-Z0-9]{4})[-\s]?([A-Z0-9]{4})\b", re.I)


def normalize_phone_number(phone_number):
    digits = re.sub(r"\D", "", phone_number or "")
    if not 7 <= len(digits) <= 15:
        raise ValueError("Enter a phone number with country code, for example +254712345678.")
    return digits


def format_pairing_code(code):
    normalized = re.sub(r"[^A-Z0-9]", "", code.upper())
    return f"{normalized[:4]}-{normalized[4:]}"


def extract_pairing_code_from_text(text):
    matches = list(PAIRING_CODE_PATTERN.finditer(text or ""))
    if not matches:
        return None
    match = matches[-1]
    return format_pairing_code("".join(match.groups()))


def extract_pairing_code(page):
    for selector in PAIRING_CODE_SELECTORS:
        locator = page.locator(selector).first
        try:
            if locator.is_visible():
                code = extract_pairing_code_from_text(locator.inner_text())
                if code:
                    return code
        except Exception:
            continue
    return None


def wait_for_pairing_code(page, timeout=45000, poll_interval=1000):
    deadline = time.monotonic() + (timeout / 1000)
    while time.monotonic() < deadline:
        code = extract_pairing_code(page)
        if code:
            return code
        page.wait_for_timeout(poll_interval)
    return None


def click_first_visible(page, selectors, timeout=15000):
    state, locator = automation.wait_for_page_state(
        page,
        {"target": selectors},
        timeout=timeout,
        poll_interval=500,
    )
    if state != "target" or locator is None:
        return None
    locator.click()
    return locator


def generate_phone_link_code(phone_number):
    phone_number = normalize_phone_number(phone_number)

    with automation.whatsapp_browser_context(headless=True) as context:
        page = automation.open_whatsapp_page(context)

        state, locator = automation.wait_for_page_state(
            page,
            {
                "linked": LINKED_SESSION_SELECTORS,
                "phone_link": PHONE_LINK_SELECTORS,
                "qr": QR_SELECTORS,
            },
            timeout=45000,
        )

        if state == "linked":
            return {
                "screenshot": page.screenshot(type="png", full_page=True),
                "state": "linked",
                "message": "WhatsApp Web is already linked to this bot session.",
                "code": None,
            }

        if state == "phone_link" and locator is not None:
            locator.click()
        else:
            locator = click_first_visible(page, PHONE_LINK_SELECTORS, timeout=5000)

        if locator is None:
            return {
                "screenshot": page.screenshot(type="png", full_page=True),
                "state": "unknown",
                "message": (
                    "WhatsApp Web loaded, but the phone-number linking option was not visible. "
                    "Showing the current screen so you can inspect the current state."
                ),
                "code": None,
            }

        _, input_locator = automation.wait_for_page_state(
            page,
            {"phone_input": PHONE_NUMBER_INPUT_SELECTORS},
            timeout=15000,
            poll_interval=500,
        )
        if input_locator is None:
            return {
                "screenshot": page.screenshot(type="png", full_page=True),
                "state": "phone_input_missing",
                "message": "The phone-number screen opened, but the number field was not available.",
                "code": None,
            }

        input_locator.click()
        input_locator.fill(phone_number)

        next_button = click_first_visible(page, NEXT_BUTTON_SELECTORS, timeout=15000)
        if next_button is None:
            return {
                "screenshot": page.screenshot(type="png", full_page=True),
                "state": "next_missing",
                "message": "The phone number was entered, but the Next button was not available.",
                "code": None,
            }

        code = wait_for_pairing_code(page, timeout=45000)
        screenshot = page.screenshot(type="png", full_page=True)
        if not code:
            return {
                "screenshot": screenshot,
                "state": "code_missing",
                "message": (
                    "WhatsApp did not show a pairing code before the timeout. "
                    "Showing the current screen so you can inspect the current state."
                ),
                "code": None,
            }

        return {
            "screenshot": screenshot,
            "state": "code",
            "message": "Pairing code generated. Enter it in WhatsApp on the phone.",
            "code": code,
        }


def capture_qr_code():
    with automation.whatsapp_browser_context(headless=True) as context:
        page = automation.open_whatsapp_page(context)
        state, locator = automation.wait_for_page_state(
            page,
            {
                "qr": QR_SELECTORS,
                "linked": LINKED_SESSION_SELECTORS,
            },
            timeout=45000,
        )

        if state == "qr" and locator is not None:
            try:
                screenshot = locator.screenshot(type="png")
            except Exception:
                screenshot = page.screenshot(type="png", full_page=True)

            return {
                "screenshot": screenshot,
                "state": "qr",
                "message": "QR code captured. Scan this image with WhatsApp.",
            }

        screenshot = page.screenshot(type="png", full_page=True)

        if state == "linked":
            return {
                "screenshot": screenshot,
                "state": "linked",
                "message": (
                    "WhatsApp Web is already linked in this browser session. "
                    "Showing the current screen instead of a QR code."
                ),
            }

        return {
            "screenshot": screenshot,
            "state": "unknown",
            "message": (
                "WhatsApp Web loaded, but the QR code was not visible before the timeout. "
                "Showing the current screen so you can inspect the current state."
            ),
        }

@app.route('/')
def home():
    today_verse = database.get_today_reading()
    return render_template('index.html', verse=today_verse, target=config.TARGET_NAME)

@app.route('/scan-qr')
def scan_qr():
    """Captures a WhatsApp Web QR code screenshot for remote scanning."""
    try:
        result = capture_qr_code()
        qr_data = base64.b64encode(result["screenshot"]).decode("utf-8")
        return jsonify(
            {
                "status": "success",
                "message": result["message"],
                "screenshot": f"data:image/png;base64,{qr_data}",
                "state": result["state"],
            }
        )
    except automation.BrowserSessionBusyError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 423
    except Exception as exc:
        error_message, status_code = automation.normalize_automation_error(exc)
        return jsonify({"status": "error", "message": error_message}), status_code

@app.route('/link-phone', methods=['POST'])
def link_phone():
    """Generates a WhatsApp phone-number pairing code for this bot session."""
    payload = request.get_json(silent=True) or request.form
    phone_number = payload.get("phone_number", "")

    try:
        result = generate_phone_link_code(phone_number)
        screenshot = base64.b64encode(result["screenshot"]).decode("utf-8")
        return jsonify({
            "status": "success",
            "message": result["message"],
            "state": result["state"],
            "code": result["code"],
            "screenshot": f"data:image/png;base64,{screenshot}",
        })
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except automation.BrowserSessionBusyError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 423
    except Exception as exc:
        error_message, status_code = automation.normalize_automation_error(exc)
        return jsonify({"status": "error", "message": error_message}), status_code

@app.route('/trigger-now', methods=['POST'])
def trigger_now():
    """Forces the bot to execute the distribution function instantly."""
    success, message, status_code = main.send_devotional()
    if success:
        return jsonify({"status": "success", "message": message}), status_code
    else:
        return jsonify({"status": "error", "message": message}), status_code

if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug, host=host, port=port)
