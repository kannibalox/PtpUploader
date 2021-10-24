import pickle
import datetime
from pathlib import Path
import logging
import os
import sys

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
        self.InitializeLogger(workingPath)
        self.PtpSubtitle = PtpSubtitle()
        self.cookie_file = Path(workingPath).joinpath("cookies.pickle")
        if self.cookie_file.exists():
            with self.cookie_file.open("rb") as fh:
                self.session.cookies = pickle.load(fh)

    def SaveCookies(self):
        with self.cookie_file.open("wb") as fh:
            pickle.dump(self.session.cookies, fh)

    # workingPath from Settings.WorkingPath.
    def InitializeLogger(self, workingPath):
        # This will create the log directory too.
        announcementLogDirPath = os.path.join(workingPath, "log/announcement")
        if not os.path.isdir(announcementLogDirPath):
            os.makedirs(announcementLogDirPath)

        logDirPath = os.path.join(workingPath, "log")

        logDate = datetime.datetime.now().strftime("%Y.%m.%d. - %H_%M_%S")
        logPath = os.path.join(logDirPath, logDate + ".txt")

        self.Logger = logging.getLogger("PtpUploader")

        # file
        handler = logging.FileHandler(logPath)
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        self.Logger.addHandler(handler)

        # stdout
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        self.Logger.addHandler(console)

        self.Logger.setLevel(logging.INFO)

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

                self.TorrentClient = Rtorrent()

        return self.TorrentClient


MyGlobals = MyGlobalsClass()
