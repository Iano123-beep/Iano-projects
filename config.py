TARGET_NAME = "My Devotional Group"
SESSION_DIR = "./whatsapp_session"


def _playwright_browser_roots():
    from pathlib import Path
    import os

    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if browsers_path and browsers_path not in {"0", ""}:
        root = Path(browsers_path)
        if root.exists():
            return [root]

    return [Path.home() / "AppData" / "Local" / "ms-playwright"]


def _version_key(path):
    try:
        return int(path.name.rsplit("-", 1)[-1])
    except (ValueError, IndexError):
        return -1


def get_chromium_executable():
    from pathlib import Path
    import os

    override = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if override:
        override_path = Path(override)
        if override_path.exists():
            return str(override_path)

    for root in _playwright_browser_roots():
        if not root.exists():
            continue

        chromium_dirs = sorted(root.glob("chromium-*"), key=_version_key, reverse=True)
        for chromium_dir in chromium_dirs:
            candidate = chromium_dir / "chrome-win" / "chrome.exe"
            if candidate.exists():
                return str(candidate)

        headless_dirs = sorted(
            root.glob("chromium_headless_shell-*"),
            key=_version_key,
            reverse=True,
        )
        for headless_dir in headless_dirs:
            candidate = headless_dir / "chrome-win" / "headless_shell.exe"
            if candidate.exists():
                return str(candidate)

    return None
