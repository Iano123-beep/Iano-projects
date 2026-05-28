import os

import automation
import config
import database

SEARCH_BOX_SELECTORS = [
    "div[aria-label='Search input textbox']",
    "div[contenteditable='true'][data-tab='3']",
    "div[contenteditable='true'][data-tab='9']",
]

MESSAGE_BOX_SELECTORS = [
    "footer div[aria-label='Type a message']",
    "footer div[contenteditable='true'][data-tab='10']",
    "footer div[contenteditable='true'][data-tab='6']",
    "footer div[role='textbox'][contenteditable='true']",
]


def send_devotional():
    """Reads the database and pushes the verse to WhatsApp web headlessly."""
    message_text = database.get_today_reading()
    print(
        "LOG: Preparing automated broadcast: "
        f"{automation.safe_console_text(message_text)}"
    )

    try:
        headless = os.environ.get("PLAYWRIGHT_HEADLESS", "1") == "1"
        with automation.whatsapp_browser_context(headless=headless) as context:
            page = automation.open_whatsapp_page(context)

            search_box = automation.first_matching_locator(page, SEARCH_BOX_SELECTORS)
            search_box.click()
            search_box.fill("")
            search_box.fill(config.TARGET_NAME)
            search_box.press("Enter")
            page.wait_for_timeout(2000)

            message_box = automation.first_matching_locator(page, MESSAGE_BOX_SELECTORS)
            message_box.click()
            message_box.fill("")
            message_box.fill(message_text)
            message_box.press("Enter")

            page.wait_for_timeout(5000)

        return True, "Message sent successfully!", 200
    except automation.BrowserSessionBusyError as exc:
        return False, str(exc), 423
    except Exception as exc:
        error_message, status_code = automation.normalize_automation_error(exc)
        return False, f"Failed execution: {error_message}", status_code
