import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config


class ConfigTests(unittest.TestCase):
    def test_get_chromium_executable_prefers_latest_chromium_browser(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            older = root / "chromium-1187" / "chrome-win"
            newer = root / "chromium-1190" / "chrome-win"
            headless = root / "chromium_headless_shell-1190" / "chrome-win"

            older.mkdir(parents=True)
            newer.mkdir(parents=True)
            headless.mkdir(parents=True)

            (older / "chrome.exe").write_text("", encoding="utf-8")
            (newer / "chrome.exe").write_text("", encoding="utf-8")
            (headless / "headless_shell.exe").write_text("", encoding="utf-8")

            with patch("config._playwright_browser_roots", return_value=[root]):
                executable = config.get_chromium_executable()

        self.assertEqual(executable, str(newer / "chrome.exe"))


if __name__ == "__main__":
    unittest.main()
