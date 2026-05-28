import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import main


@contextmanager
def fake_browser_context_manager():
    yield object()


def fake_browser_context(*args, **kwargs):
    return fake_browser_context_manager()


class SendDevotionalTests(unittest.TestCase):
    @patch("main.database.get_today_reading", return_value="📜 Test message")
    @patch("main.automation.first_matching_locator")
    @patch("main.automation.open_whatsapp_page")
    @patch("main.automation.whatsapp_browser_context", side_effect=fake_browser_context)
    @patch("builtins.print")
    def test_send_devotional_logs_unicode_safely(
        self,
        print_mock,
        whatsapp_browser_context,
        open_whatsapp_page,
        first_matching_locator,
        get_today_reading,
    ):
        search_box = MagicMock()
        message_box = MagicMock()
        first_matching_locator.side_effect = [search_box, message_box]

        page = MagicMock()
        open_whatsapp_page.return_value = page

        success, message, status_code = main.send_devotional()

        self.assertTrue(success)
        self.assertEqual(message, "Message sent successfully!")
        self.assertEqual(status_code, 200)
        print_mock.assert_called_once()

        log_line = print_mock.call_args.args[0]
        self.assertTrue(all(ord(char) < 128 for char in log_line))
        self.assertIn("\\U0001f4dc", log_line)

        search_box.fill.assert_any_call("My Devotional Group")
        message_box.fill.assert_any_call("📜 Test message")
        page.wait_for_timeout.assert_any_call(2000)
        page.wait_for_timeout.assert_any_call(5000)
        whatsapp_browser_context.assert_called_once_with(headless=True)
        get_today_reading.assert_called_once_with()

    @patch(
        "main.automation.whatsapp_browser_context",
        side_effect=main.automation.BrowserSessionBusyError("busy profile"),
    )
    @patch("main.database.get_today_reading", return_value="📜 Test message")
    @patch("builtins.print")
    def test_send_devotional_returns_423_for_busy_browser_session(
        self,
        print_mock,
        get_today_reading,
        whatsapp_browser_context,
    ):
        success, message, status_code = main.send_devotional()

        self.assertFalse(success)
        self.assertEqual(message, "busy profile")
        self.assertEqual(status_code, 423)
        get_today_reading.assert_called_once_with()
        whatsapp_browser_context.assert_called_once_with(headless=True)
        print_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
