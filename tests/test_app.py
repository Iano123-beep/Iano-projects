import base64
import unittest
from unittest.mock import patch

import automation
import app


class AppRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_home_renders_dashboard(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("SamBot", body)
        self.assertIn("My Devotional Group", body)

    @patch(
        "app.capture_qr_code",
        return_value={
            "screenshot": b"png-bytes",
            "state": "qr",
            "message": "QR code captured. Scan this image with WhatsApp.",
        },
    )
    def test_scan_qr_returns_base64_image(self, capture_qr_code):
        response = self.client.get("/scan-qr")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["state"], "qr")
        self.assertEqual(
            payload["screenshot"],
            f"data:image/png;base64,{base64.b64encode(b'png-bytes').decode('utf-8')}",
        )
        capture_qr_code.assert_called_once_with()

    @patch(
        "app.capture_qr_code",
        return_value={
            "screenshot": b"page-bytes",
            "state": "linked",
            "message": (
                "WhatsApp Web is already linked in this browser session. "
                "Showing the current screen instead of a QR code."
            ),
        },
    )
    def test_scan_qr_returns_current_screen_when_session_is_already_linked(
        self,
        capture_qr_code,
    ):
        response = self.client.get("/scan-qr")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["state"], "linked")
        self.assertIn("already linked", payload["message"])
        self.assertEqual(
            payload["screenshot"],
            f"data:image/png;base64,{base64.b64encode(b'page-bytes').decode('utf-8')}",
        )
        capture_qr_code.assert_called_once_with()

    @patch(
        "app.capture_qr_code",
        side_effect=automation.BrowserSessionBusyError("busy profile"),
    )
    def test_scan_qr_returns_423_when_browser_profile_is_busy(self, capture_qr_code):
        response = self.client.get("/scan-qr")

        self.assertEqual(response.status_code, 423)
        payload = response.get_json()
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["message"], "busy profile")
        capture_qr_code.assert_called_once_with()

    @patch(
        "app.generate_phone_link_code",
        return_value={
            "screenshot": b"screen-bytes",
            "state": "code",
            "message": "Pairing code generated. Enter it in WhatsApp on the phone.",
            "code": "ABCD-EFGH",
        },
    )
    def test_link_phone_returns_pairing_code(self, generate_phone_link_code):
        response = self.client.post(
            "/link-phone",
            json={"phone_number": "+254712345678"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["state"], "code")
        self.assertEqual(payload["code"], "ABCD-EFGH")
        self.assertEqual(
            payload["screenshot"],
            f"data:image/png;base64,{base64.b64encode(b'screen-bytes').decode('utf-8')}",
        )
        generate_phone_link_code.assert_called_once_with("+254712345678")

    def test_link_phone_validates_phone_number(self):
        response = self.client.post("/link-phone", json={"phone_number": "123"})

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertEqual(payload["status"], "error")
        self.assertIn("country code", payload["message"])

    @patch("main.send_devotional", return_value=(False, "send failed", 500))
    def test_trigger_now_returns_error_status_code(self, send_devotional):
        response = self.client.post("/trigger-now")

        self.assertEqual(response.status_code, 500)
        payload = response.get_json()
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["message"], "send failed")
        send_devotional.assert_called_once_with()

    def test_normalize_phone_number_accepts_international_format(self):
        self.assertEqual(app.normalize_phone_number("+254 712 345 678"), "254712345678")

    def test_extract_pairing_code_from_text(self):
        self.assertEqual(
            app.extract_pairing_code_from_text("Your code is abcd efgh"),
            "ABCD-EFGH",
        )


if __name__ == "__main__":
    unittest.main()
