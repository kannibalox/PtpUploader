import os
import re
import time
from datetime import timedelta
from urllib.parse import parse_qs
from pathlib import Path

import bencode
import requests

from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderException import PtpUploaderException


# Supported formats: "100 GB", "100 MB", "100 bytes". (Space is optional.)
# Returns with an integer.
# Returns with 0 if size can't be found.
def GetSizeFromText(text: str):
    text = text.replace(" ", "")
    text = text.replace(",", "")  # For sizes like this: 1,471,981,530bytes
    text = text.replace("GiB", "GB")
    text = text.replace("MiB", "MB")

    matches = re.match("(.+)GB", text)
    if matches is not None:
        size = float(matches.group(1))
        return int(size * 1024 * 1024 * 1024)

    matches = re.match("(.+)MB", text)
    if matches is not None:
        size = float(matches.group(1))
        return int(size * 1024 * 1024)

    matches = re.match("(.+)bytes", text)
    if matches is not None:
        return int(matches.group(1))

    return 0


def SizeToText(size):
    if size < 1024 * 1024 * 1024:
        return "%.2f MiB" % (float(size) / (1024 * 1024))
    else:
        return "%.2f GiB" % (float(size) / (1024 * 1024 * 1024))


# timeDifference must be datetime.timedelta.
def TimeDifferenceToText(
    td: timedelta, levels: int = 2, agoText=" ago", noDifferenceText="Just now"
) -> str:
    timeDifference: int = int(td.total_seconds())
    if timeDifference < 3:
        return noDifferenceText

    years = timeDifference // 31556926  # 31556926 seconds = 1 year
    timeDifference %= 31556926

    months = (
        timeDifference // 2629744
    )  # 2629744 seconds = ~1 month (The mean month length of the Gregorian calendar is 30.436875 days.)
    timeDifference %= 2629744

    days = timeDifference // 86400  # 86400 seconds = 1 day
    timeDifference %= 86400

    hours = timeDifference // 3600
    timeDifference %= 3600

    minutes = timeDifference // 60
    timeDifference %= 60

    seconds = timeDifference

    text = ""
    if years > 0:
        text += str(years) + "y"
        levels -= 1

    if months > 0 and levels > 0:
        text += str(months) + "mo"
        levels -= 1

    if days > 0 and levels > 0:
        text += str(days) + "d"
        levels -= 1

    if hours > 0 and levels > 0:
        text += str(hours) + "h"
        levels -= 1

    if minutes > 0 and levels > 0:
        text += str(minutes) + "m"
        levels -= 1

    if seconds > 0 and levels > 0:
        text += str(seconds) + "s"

    if len(text) > 0:
        return text + agoText
    else:
        return noDifferenceText


def ParseQueryString(query):
    return parse_qs(query)


def MakeRetryingHttpGetRequestWithRequests(
    url, maximumTries=3, delayBetweenRetriesInSec=10
):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0"
    }

    while True:
        try:
            result = MyGlobals.session.get(url, headers=headers)
            result.raise_for_status()
            return result
        except requests.exceptions.ConnectionError:
            if maximumTries > 1:
                maximumTries -= 1
                time.sleep(delayBetweenRetriesInSec)
            else:
                raise


def MakeRetryingHttpPostRequestWithRequests(
    url, postData, maximumTries=3, delayBetweenRetriesInSec=10
):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0"
    }

    while True:
        try:
            result = MyGlobals.session.post(url, data=postData, headers=headers)
            result.raise_for_status()
            return result
        except requests.exceptions.ConnectionError:
            if maximumTries > 1:
                maximumTries -= 1
                time.sleep(delayBetweenRetriesInSec)
            else:
                raise


# Path can be a file or a directory. (Obviously.)
def GetPathSize(path) -> int:
    path = Path(path).resolve()
    if path.is_file():
        return path.stat().st_size

    return sum([p.stat().st_size for p in path.rglob("*")])

# Always uses / as path separator.
def GetFileListFromTorrent(torrentPath):
    with open(torrentPath, "rb") as fh:
        data = bencode.decode(fh.read())
    name = data["info"].get("name", None)
    files = data["info"].get("files", None)

    if files is None:
        return [name]
    else:
        fileList = []
        for fileInfo in files:
            path = "/".join(fileInfo["path"])
            fileList.append(path)

        return fileList


def RemoveDisallowedCharactersFromPath(text):
    newText = text

    # These characters can't be in filenames on Windows.
    forbiddenCharacters = r"""\/:*?"<>|"""
    for c in forbiddenCharacters:
        newText = newText.replace(c, "")

    newText = newText.strip()

    if len(newText) > 0:
        return newText
    else:
        raise PtpUploaderException("New name for '%s' resulted in empty string." % text)


def ValidateTorrentFile(torrentPath):
    try:
        with open(torrentPath, "rb") as fh:
            bencode.decode(fh.read())
    except Exception as e:
        raise PtpUploaderException("File '%s' is not a valid torrent." % torrentPath) from e


def GetSuggestedReleaseNameAndSizeFromTorrentFile(torrentPath):
    with open(torrentPath, "rb") as fh:
        data = bencode.decode(fh.read())
    name = data["info"].get("name", None)
    files = data["info"].get("files", None)
    if files is None:
        # It is a single file torrent, remove the extension.
        name, _ = os.path.splitext(name)
        size = data["info"]["length"]
        return name, size
    else:
        size = 0
        for file in files:
            size += file["length"]

        return name, size


def DecodeHtmlEntities(html):
    return html.unescape(html)
