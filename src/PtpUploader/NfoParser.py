import os
import re
from pathlib import Path

from PtpUploader.Helper import GetFileListFromTorrent


class NfoParser:
    # Return with the IMDb id.
    # Eg.: 0111161 for http://www.imdb.com/title/tt0111161/
    @staticmethod
    def GetImdbId(nfoText: str) -> str:
        matches = re.search(r"imdb.com/title/tt(\d+)", nfoText)
        if not matches:
            matches = re.search(r"imdb.com/Title\?(\d+)", nfoText)

        if matches:
            return matches.group(1)
        return ""

    @staticmethod
    def ReadNfo(nfoPath: os.PathLike) -> str:
        with Path(nfoPath).open("rb") as nfoFile:
            return nfoFile.read().decode("cp437", "ignore")

    # If there are multiple NFOs, it returns with an empty string.
    @staticmethod
    def FindAndReadNfoFileToUnicode(directoryPath) -> str:
        nfoPath = None
        nfoFound = False

        for entry in os.listdir(directoryPath):
            entryPath = os.path.join(directoryPath, entry)
            if os.path.isfile(entryPath) and entry.lower().endswith(".nfo"):
                if nfoFound:
                    nfoPath = None
                else:
                    nfoPath = entryPath
                    nfoFound = True

        if nfoPath is not None:
            with open(nfoPath, "rb") as nfoFile:
                return nfoFile.read().decode("cp437", "ignore")
        return ""

    @staticmethod
    def IsTorrentContainsMultipleNfos(torrentPath):
        files = GetFileListFromTorrent(torrentPath)
        nfoCount = 0
        for file in files:
            file = file.lower()

            # Only check in the root folder.
            if file.find("/") != -1 or file.find("\\") != -1:
                continue

            if file.endswith(".nfo"):
                nfoCount += 1
                if nfoCount > 1:
                    return True

        return False
