from .PtpSubtitle import PtpSubtitle

import http.cookiejar
import datetime
import logging
import os
import sys
import requests


class MyGlobalsClass:
    def __init__(self):
        self.CookieJar = None
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
        self.CookieJar = http.cookiejar.CookieJar()
        self.PtpSubtitle = PtpSubtitle()

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

        self.Logger.setLevel(logging.DEBUG)

    # Inline imports are used here to avoid unnecessary dependencies.
    def GetTorrentClient(self):
        if self.TorrentClient is None:
            from .Settings import Settings

            if Settings.TorrentClientName.lower() == "transmission":
                from .Tool.Transmission import Transmission

                self.TorrentClient = Transmission(
                    Settings.TorrentClientAddress, Settings.TorrentClientPort
                )
            else:
                from .Tool.Rtorrent import Rtorrent

                self.TorrentClient = Rtorrent()

        return self.TorrentClient


MyGlobals = MyGlobalsClass()
