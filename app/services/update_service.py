"""
Update service for checking, downloading, and applying application updates.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict
from urllib import request
from zipfile import ZipFile

from packaging import version


class UpdateService:
    UPDATE_URL = "https://your-server.com/api/updates"

    def __init__(self, current_version: str = "0.0.0"):
        self.current_version = current_version or "0.0.0"
        self.app_dir = self._get_app_dir()

    def _get_app_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent
        return Path(__file__).parent.parent.parent

    def get_current_version(self) -> str:
        return self.current_version

    def check_for_updates(self) -> Dict:
        """Check remote endpoint for a newer version."""
        try:
            with request.urlopen(self.UPDATE_URL, timeout=10) as resp:
                payload = resp.read().decode("utf-8")
                data = json.loads(payload)
        except Exception as exc:
            return {"available": False, "error": str(exc)}

        remote_version = str(data.get("version") or data.get("tag_name") or "0.0.0")
        changelog = data.get("changelog") or data.get("body") or ""
        download_url = data.get("download_url") or data.get("browser_download_url") or ""

        try:
            is_newer = version.parse(remote_version) > version.parse(self.current_version)
        except Exception:
            is_newer = False

        return {
            "available": bool(is_newer and download_url),
            "version": remote_version,
            "changelog": changelog,
            "download_url": download_url,
        }

    def download_update(self, url: str, progress_callback: Callable[[int], None] | None = None) -> str:
        """Download update file and report progress. Returns path to file."""
        tmp_dir = Path(tempfile.mkdtemp(prefix="update_"))
        target_path = tmp_dir / "update_package.zip"

        try:
            with request.urlopen(url) as resp, open(target_path, "wb") as f:
                total = int(resp.getheader("Content-Length") or 0)
                downloaded = 0
                chunk_size = 1024 * 64
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        percent = int(downloaded / total * 100)
                        progress_callback(percent)
            return str(target_path)
        except Exception:
            if target_path.exists():
                target_path.unlink()
            raise

    def apply_update(self, update_path: str) -> bool:
        """Apply update from a downloaded zip archive."""
        try:
            with ZipFile(update_path, "r") as zf:
                zf.extractall(self.app_dir)
            return True
        except Exception:
            return False

