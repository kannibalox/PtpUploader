import datetime
import logging
import os
import pickle
import sys

from pathlib import Path

import requests

from PtpUploader.PtpSubtitle import PtpSubtitle


class MyGlobalsClass:
    def __init__(self):
        self.Logger = None
        self.PtpUploader = None
        self.SourceFactory = None
        self.PtpSubtitle = None
        self.TorrentClient = None

        self.session = requests.session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.45 Safari/537.36"
            }
        )

        # Use cloudflare-scrape if installed.
        try:
            from cfscrape import CloudflareAdapter

            self.session.mount("https://", CloudflareAdapter())
        except ImportError:
            pass

    def InitializeGlobals(self, workingPath):
        from PtpUploader.Settings import config
        self.InitializeLogger(workingPath)
        self.PtpSubtitle = PtpSubtitle()
        self.cookie_file: Path = Path(workingPath).joinpath("cookies.pickle")
        self.cookie_file: Path = Path(config.cookie_file).expanduser()
        if self.cookie_file.exists() and self.cookie_file.is_file():
            with self.cookie_file.open("rb") as fh:
                    self.session.cookies = pickle.load(fh)

    def SaveCookies(self):
        with self.cookie_file.open("wb") as fh:
            pickle.dump(self.session.cookies, fh)

    # workingPath from Settings.WorkingPath.
    def InitializeLogger(self, workingPath):
        # This will create the log directory too.
        self.Logger = logging.getLogger(__name__)

    # Inline imports are used here to avoid unnecessary dependencies.
    def GetTorrentClient(self):
        if self.TorrentClient is None:
            from PtpUploader.Settings import Settings

            if Settings.TorrentClientName.lower() == "transmission":
                from PtpUploader.Tool.Transmission import Transmission

                self.TorrentClient = Transmission(
                    Settings.TorrentClientAddress, Settings.TorrentClientPort
                )
            else:
                from PtpUploader.Tool.Rtorrent import Rtorrent

                self.TorrentClient = Rtorrent(Settings.TorrentClientAddress)
        return self.TorrentClient


MyGlobals = MyGlobalsClass()
