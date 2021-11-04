import datetime
import json
import logging

from PtpUploader.Helper import SizeToText, TimeDifferenceToText
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.ReleaseInfo import ReleaseInfo

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
        latestTorrent = None
        latestTorrentId = 0

        for item in self.Torrents:
            if item["Id"] > latestTorrentId:
                latestTorrentId = item.TorrentId
                latestTorrent = item

        return latestTorrent

    def IsReleaseExists(self, release):
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

        # TODO: Refactor into one big loop (where possible)
        # PTP wouldn't let us upload something with the same name anyway
        matched_name = [t for t in self.Torrents if t["ReleaseName"] == release.ReleaseName]
        if matched_name:
            return matched_name[0]

        # Find any really obvious duplicates
        for t in self.Torrents:
            if t["Source"] == release.Source and t["Codec"] == release.Codec:
                if abs((release.Size / t["Size"]) - 1) * 100 < 3:
                    return t
        
        # 4.4.1 One slot per untouched DVD format
        if release.Resolution == "PAL":
            if "PAL" in [t["Resolution"] for t in self.Torrents]:
                return [t for t in self.Torrents if t["Resolution"] == "PAL"][0]
            return None

        if release.Resolution == "NTSC":
            if "NTSC" in [t["Resolution"] for t in self.Torrents]:
                return [t for t in self.Torrents if t["Resolution"] == "NTSC"][0]
            return None

        # Two slots for SD
        if release.ResolutionType in [Resolutions.Other, "480p"]:
            print("bleh")
            for t in self.Torrents:
                print(t)
                if t["Quality"] == "Standard Definition":
                    # 4.1.1.1 40% difference to be able to coexist
                    print(abs((release.Size / t["Size"]) - 1) * 100)
                    if abs((release.Size / t["Size"]) - 1) * 100 < 40:
                        return t
        # One slot for  576
        if release.Resolution == "576p":
            # Check for any other 576p
            for t in self.Torrents:
                if t["Resolution"] == "576p":
                    return t

        return None
