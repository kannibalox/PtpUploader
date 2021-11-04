import datetime
import json
import logging

from PtpUploader.Helper import SizeToText, TimeDifferenceToText
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.NfoParser import NfoParser

# Shortcuts for reference
Codecs = ReleaseInfo.CodecChoices
Containers = ReleaseInfo.ContainerChoices
Sources = ReleaseInfo.SourceChoices
Resolutions = ReleaseInfo.ResolutionChoices

logger = logging.getLogger(__name__)


def GetSourceScore(source):
    scores = {
        "VHS": 3,
        "TV": 3,
        "HDTV": 5,
        "WEB": 5,
        # DVD has the same score as HD-DVD and Blu-ray because it must be
        # manually checked if it can co-exists or not.
        "DVD": 7,
        "HD-DVD": 7,
        "Blu-ray": 7,
    }

    return scores.get(source, -1)  # -1 is the default value


# Notes:
# - We treat HD-DVD and Blu-ray as same quality.
# - We treat DVD and Blu-ray rips equally in the standard definition category.
# - We treat H.264 and x264 equally because of the uploading rules: "MP4 can only be trumped by MKV if the use of that container causes problems with video or audio".
# - We treat XviD and DivX as equally irrelevant.
class PtpMovieSearchResult:
    def __init__(self, ptpId, moviePageJsonText):
        self.PtpId = ptpId
        self.ImdbId = ""
        self.ImdbRating = ""
        self.ImdbVoteCount = ""
        self.Torrents = []

        if moviePageJsonText is not None:
            self.__ParseMoviePage(moviePageJsonText)

    def __ParseMoviePageMakeItems(self, itemList, torrent):
        torrent["Id"] = int(torrent["Id"])
        torrent["Size"] = int(torrent["Size"])
        torrent["SourceScore"] = GetSourceScore(torrent["Source"])
        torrent["UploadTime"] = datetime.datetime.strptime(
            torrent["UploadTime"], "%Y-%m-%d %H:%M:%S"
        )
        if "RemasterTitle" not in torrent:
            torrent["RemasterTitle"] = ""
        if "RemasterYear" not in torrent:
            torrent["RemasterYear"] = ""

        fullTitle = f'{torrent["ReleaseName"]} / {torrent["Container"]} / {torrent["Codec"]} / {torrent["Resolution"]}'
        if len(torrent["RemasterTitle"]) > 0:
            fullTitle += " / " + torrent["RemasterTitle"]
            if len(torrent["RemasterYear"]) > 0:
                fullTitle += " (%s)" % torrent["RemasterYear"]
        torrent["FullTitle"] = fullTitle

        itemList.append(torrent)

    def __ParseMoviePage(self, moviePageJsonText):
        moviePageJson = json.loads(moviePageJsonText)

        if moviePageJson["Result"] != "OK":
            raise PtpUploaderException(
                "Unexpected movie page JSON response: '%s'." % moviePageJsonText
            )

        self.ImdbId = moviePageJson.get("ImdbId", "")
        self.ImdbRating = str(moviePageJson.get("ImdbRating", ""))
        self.ImdbVoteCount = str(moviePageJson.get("ImdbVoteCount", ""))

        torrents = moviePageJson["Torrents"]
        if len(torrents) <= 0:
            raise PtpUploaderException(
                "No torrents on movie page 'https://passthepopcorn.me/torrents.php?id=%s'."
                % self.PtpId
            )

        # Get the list of torrents for each section.
        for torrent in torrents:
            self.__ParseMoviePageMakeItems(self.Torrents, torrent)

    def GetLatestTorrent(self):
        return sorted(self.Torrents, key=lambda t: int(t['Id']), reverse=True)[0]

    def IsReleaseExists(self, release):
        if self.PtpId == "":
            return None
        # Flag un-checkable fields
        if release.Codec == Codecs.Other:
            raise PtpUploaderException(
                "Unsupported codec '%s' for duplicate checking" % release.CodecOther
            )
        if release.Container == Containers.Other:
            raise PtpUploaderException(
                "Unsupported container '%s' for duplicate checking"
                % release.ContainerOther
            )
        if release.Source == Sources.Other:
            raise PtpUploaderException(
                "Unsupported source '%s' for duplicate checking" % release.SourceOther
            )

        # 3.1.3 If literally anything else exists, xvid/divx need manual checking
        if release.Codec in [
            Codecs.XVID,
            Codecs.DIVX,
        ]:
            return self.Torrents[0]

        # 4.4.1 One slot per untouched DVD format, and screen them out early
        if release.ResolutionType in ["PAL", "NTSC"]:
            if release.ResolutionType in [t["Resolution"] for t in self.Torrents]:
                return [
                    t
                    for t in self.Torrents
                    if t["Resolution"] == release.ResolutionType
                ][0]
            return None

        for t in self.Torrents:
            # PTP wouldn't let us upload something with the same name anyway
            if t["ReleaseName"] == release.ReleaseName:
                return t
            # Most likely not coincedence
            if t["Size"] == release.Size:
                return t

            # Find any really close duplicates
            if t["Source"] == release.Source and t["Codec"] == release.Codec:
                if abs((release.Size / t["Size"]) - 1) * 100 < 3:
                    return t

            # Two slots are available, first check if we can coexist with any of them
            if (
                release.ResolutionType in [Resolutions.Other, "480p"]
                and t["Quality"] == "Standard Definition"
            ):
                if (
                    abs((release.Size / t["Size"]) - 1) * 100 < 40
                ):  # 4.1.1.1 40% size difference to be able to coexist
                    return t
            if release.ResolutionType == "576p" and t["Resolution"] == "576p":
                return t

        return None
