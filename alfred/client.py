from __future__ import annotations

import json
import sys
from collections.abc import Callable
from os import environ
from pathlib import Path
from plistlib import dump, load
from time import time

from aiohttp import ClientSession
from packaging import version

from .models import AlfredResult


class AlfredClient:

    query: str
    page_count: int

    results: list[AlfredResult]

    def __init__(self) -> None:
        self.page_count = sys.argv[1].count("+") + 1
        self.query = sys.argv[1].replace("+", "")
        self.results = []

    async def update(self, user: str, repo: str):
        """Update alfred workflow if needed"""
        with open("info.plist", "rb") as f:
            plist = load(f)
        current_version = plist["version"]
        if time() - plist.get("lastcheckedtime", 0) > 7 * 24 * 60 * 60:
            async with ClientSession() as session:
                async with session.get(f"https://api.github.com/repos/{user}/{repo}/releases") as response:
                    if response.status != 200:
                        self.add_result(
                            title="Update failed",
                            subtitle="Could not get latest release",
                            icon_path="alfred/icons/failed.png"
                        )
                    else:
                        releases = await response.json()
                        latest_release = releases[0]
                        latest_version = latest_release["tag_name"]
                        download_url = latest_release["assets"][0]["browser_download_url"]
                        current_version = plist["version"]
                        if version.parse(latest_version) > version.parse(current_version):
                            self.add_result(
                                title=f"Update available {current_version} → {latest_version}",
                                subtitle=f"Hold ⇧ and enter to update",
                                icon_path="alfred/icons/updated.png",
                                arg=download_url
                            )
                            plist["needupdate"] = True
                        plist["latestversion"] = latest_version
                        plist["downloadurl"] = download_url
                        plist["lastcheckedtime"] = int(time())
        elif plist.get("needupdate", False):
            self.add_result(
                title=f"Update available {current_version} → {plist['latestversion']}",
                subtitle=f"Hold ⇧ and enter to update",
                icon_path="alfred/icons/updated.png",
                arg=plist["downloadurl"]
            )
        with open("info.plist", "wb") as f:
            dump(plist, f)

    def add_result(
        self,
        title: str,
        subtitle: str,
        icon_path: str | Path | None = None,
        arg: str | None = None,
        http_downloader: Callable[[str], str] | None = None,
    ):
        """Create and add alfred result."""
        icon = None
        if icon_path:
            if http_downloader and "http" in str(icon_path):
                icon_path = http_downloader(str(icon_path))
            icon = AlfredResult.Icon(str(icon_path))
        self.results.append(AlfredResult(title=title, subtitle=subtitle, icon=icon, arg=arg))

    def response(self):
        """Print alfred results and exit."""
        print(json.dumps({"items": [result.to_dict() for result in self.results]}))
        exit(0)
