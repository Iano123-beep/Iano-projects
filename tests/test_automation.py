import unittest

import automation


class FakeLocator:
    def __init__(self, visible):
        self.visible = visible
        self.first = self

    def is_visible(self):
        return self.visible


class FakePage:
    def __init__(self, visible_states):
        self.visible_states = visible_states
        self.index = 0

    def locator(self, selector):
        current = self.visible_states[min(self.index, len(self.visible_states) - 1)]
        return FakeLocator(selector in current)

    def wait_for_timeout(self, _milliseconds):
        self.index += 1


class AutomationErrorTests(unittest.TestCase):
    def test_wait_for_page_state_returns_first_visible_match(self):
        page = FakePage(
            [
                set(),
                {"div[data-testid='qrcode']"},
            ]
        )

        state, locator = automation.wait_for_page_state(
            page,
            {
                "qr": ["div[data-testid='qrcode']"],
                "linked": ["#pane-side"],
            },
            timeout=2000,
            poll_interval=1,
        )

        self.assertEqual(state, "qr")
        self.assertIsNotNone(locator)
        self.assertTrue(locator.is_visible())

    def test_normalize_missing_headless_shell_error(self):
        message, status_code = automation.normalize_automation_error(
            RuntimeError(
                "Executable doesn't exist at "
                "C:\\Users\\Admin\\AppData\\Local\\ms-playwright\\chromium_headless_shell-1187\\chrome-win\\headless_shell.exe"
            )
        )

        self.assertEqual(status_code, 503)
        self.assertIn("missing headless-shell binary", message)

    def test_normalize_profile_lock_error(self):
        message, status_code = automation.normalize_automation_error(
            RuntimeError("Failed to create a ProcessSingleton for your profile directory")
        )

        self.assertEqual(status_code, 423)
        self.assertIn("locked by another Chromium instance", message)

    def test_normalize_network_error(self):
        message, status_code = automation.normalize_automation_error(
            RuntimeError("Page.goto: net::ERR_NETWORK_ACCESS_DENIED")
        )

        self.assertEqual(status_code, 503)
        self.assertIn("cannot reach WhatsApp Web", message)


if __name__ == "__main__":
    unittest.main()
