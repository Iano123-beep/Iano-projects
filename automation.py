import os
import threading
import time
from contextlib import contextmanager, suppress

from playwright.sync_api import sync_playwright

import config

SESSION_LOCK = threading.Lock()


class BrowserSessionBusyError(RuntimeError):
    """Raised when another request is already using the persistent browser profile."""


def safe_console_text(value):
    return value.encode("ascii", "backslashreplace").decode("ascii")


def normalize_automation_error(exc):
    message = str(exc)

    if (
        "Executable doesn't exist" in message
        and "chromium_headless_shell" in message
    ):
        return (
            "Playwright tried to use a missing headless-shell binary. "
            "Restart the app so it picks up the installed Chromium browser, "
            "or run 'playwright install chromium' if the browser files are incomplete.",
            503,
        )

    if "ProcessSingleton" in message or "Lock file can not be created" in message:
        return (
            "WhatsApp browser profile is locked by another Chromium instance. "
            "Close the other browser session using this bot profile and try again.",
            423,
        )

    if "ERR_NETWORK_ACCESS_DENIED" in message:
        return (
            "This environment cannot reach WhatsApp Web right now. "
            "Check network or firewall access and try again.",
            503,
        )

    return message, 500


def first_matching_locator(page, selectors, timeout=45000):
    selector = ", ".join(selectors)
    page.wait_for_selector(selector, state="visible", timeout=timeout)
    return page.locator(selector).first


def first_visible_locator(page, selectors):
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.is_visible():
                return locator
        except Exception:
            continue
    return None


def wait_for_page_state(page, state_selectors, timeout=45000, poll_interval=1000):
    deadline = time.monotonic() + (timeout / 1000)

    while time.monotonic() < deadline:
        for state, selectors in state_selectors.items():
            locator = first_visible_locator(page, selectors)
            if locator is not None:
                return state, locator

        page.wait_for_timeout(poll_interval)

    return "unknown", None


def open_whatsapp_page(context):
    page = context.new_page()
    page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
    return page


@contextmanager
def whatsapp_browser_context(headless=True):
    if not SESSION_LOCK.acquire(blocking=False):
        raise BrowserSessionBusyError(
            "WhatsApp session is busy. Wait for the current scan/send job to finish, then try again."
        )

    playwright = None
    context = None
    try:
        os.makedirs(config.SESSION_DIR, exist_ok=True)
        playwright = sync_playwright().start()

        launch_args = {
            "user_data_dir": config.SESSION_DIR,
            "headless": headless,
            "args": ["--disable-quic"],
        }

        executable_path = config.get_chromium_executable()
        if executable_path:
            launch_args["executable_path"] = executable_path

        context = playwright.chromium.launch_persistent_context(**launch_args)
        yield context
    finally:
        if context is not None:
            with suppress(Exception):
                context.close()

        if playwright is not None:
            with suppress(Exception):
                playwright.stop()

        SESSION_LOCK.release()
