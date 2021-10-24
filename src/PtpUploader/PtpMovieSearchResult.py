import datetime
import json

from PtpUploader.Helper import (SizeToText,
                                TimeDifferenceToText)
from PtpUploader.PtpUploaderException import PtpUploaderException


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


class PtpMovieSearchResultItem:
    def __init__(
        self,
        torrentId,
        fullTitle,
        codec,
        container,
        source,
        resolution,
        remasterTitle,
        size,
        uploadTime,
    ):
        self.TorrentId = int(torrentId)
        self.FullTitle = fullTitle
        self.Codec = codec
        self.Container = container
        self.Source = source
        self.SourceScore = GetSourceScore(source)
        self.Resolution = resolution
        self.RemasterTitle = remasterTitle
        self.Size = size
        self.UploadTime = uploadTime

    def GetUploadTimeAsDateTimeUtc(self):
        return datetime.datetime.strptime(self.UploadTime, "%Y-%m-%d %H:%M:%S")

    def __repr__(self):
        ago = TimeDifferenceToText(
            datetime.datetime.utcnow() - self.GetUploadTimeAsDateTimeUtc()
        )
        return "%s, %s, %s" % (self.FullTitle, SizeToText(self.Size), ago)


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
        self.SdList = []
        self.HdList = []
        self.UhdList = []
        self.OtherList = []

        if moviePageJsonText is not None:
            self.__ParseMoviePage(moviePageJsonText)

    @staticmethod
    def __ReprHelper(text, list, name):
        if len(list) > 0:
            if len(text) > 0:
                text += "\n"

            text += name + "\n"
            for item in list:
                text += str(item) + "\n"

        return text

    def __repr__(self):
        result = PtpMovieSearchResult.__ReprHelper(
            "", self.SdList, "Standard Definition"
        )
        result = PtpMovieSearchResult.__ReprHelper(
            result, self.HdList, "High Definition"
        )
        result = PtpMovieSearchResult.__ReprHelper(
            result, self.UhdList, "Ultra High Definition"
        )
        return PtpMovieSearchResult.__ReprHelper(result, self.OtherList, "Other")

    def __ParseMoviePageMakeItems(self, itemList, torrent):
        torrentId = torrent["Id"]
        size = int(torrent["Size"])
        source = torrent["Source"]
        container = torrent["Container"]
        codec = torrent["Codec"]
        resolution = torrent["Resolution"]
        remasterTitle = torrent.get("RemasterTitle", "")
        remasterYear = torrent.get("RemasterYear", "")
        uploadTime = torrent["UploadTime"]

        fullTitle = codec + " / " + container + " / " + source + " / " + resolution
        if len(remasterTitle) > 0:
            fullTitle += " / " + remasterTitle
            if len(remasterYear) > 0:
                fullTitle += " (%s)" % remasterYear

        itemList.append(
            PtpMovieSearchResultItem(
                torrentId,
                fullTitle,
                codec,
                container,
                source,
                resolution,
                remasterTitle,
                size,
                uploadTime,
            )
        )

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
            quality = torrent["Quality"]
            if quality == "Standard Definition":
                self.__ParseMoviePageMakeItems(self.SdList, torrent)
            elif quality == "High Definition":
                self.__ParseMoviePageMakeItems(self.HdList, torrent)
            elif quality == "Ultra High Definition":
                self.__ParseMoviePageMakeItems(self.UhdList, torrent)
            else:
                self.__ParseMoviePageMakeItems(self.OtherList, torrent)

    @staticmethod
    def __GetListOfMatches(list, codecs, sources=None, resolutions=None, remux=False):
        result = []
        for item in list:
            if (
                ((codecs is None) or (item.Codec in codecs))
                and ((sources is None) or (item.Source in sources))
                and ((resolutions is None) or (item.Resolution in resolutions))
                and remux == (item.RemasterTitle.find("Remux") != -1)
            ):
                result.append(item)

        return result

    @staticmethod
    def __IsInList(list, codecs, sources=None, resolutions=None, remux=False):
        existingReleases = PtpMovieSearchResult.__GetListOfMatches(
            list, codecs, sources, resolutions, remux
        )
        if len(existingReleases) > 0:
            return existingReleases[0]
        else:
            return None

    @staticmethod
    def __IsInListUsingSourceScore(
        list, codecs, sourceScore, resolutions=None, remux=False
    ):
        for item in list:
            if (
                ((codecs is None) or (item.Codec in codecs))
                and (item.SourceScore >= sourceScore)
                and ((resolutions is None) or (item.Resolution in resolutions))
                and remux == (item.RemasterTitle.find("Remux") != -1)
            ):
                return item

        return None

    @staticmethod
    def __IsFineSource(source):
        return source == "DVD" or source == "Blu-ray" or source == "HD-DVD"

    def __IsHdFineSourceReleaseExists(self, releaseInfo):
        if releaseInfo.IsRemux():
            if releaseInfo.Source == "Blu-ray" or releaseInfo.Source == "HD-DVD":
                return PtpMovieSearchResult.__IsInList(
                    self.HdList, None, ["Blu-ray", "HD-DVD"], ["1080i", "1080p"], True
                )
        else:
            if (
                releaseInfo.Source == "Blu-ray" or releaseInfo.Source == "HD-DVD"
            ) and releaseInfo.ResolutionType == "1080p":
                return PtpMovieSearchResult.__IsInList(
                    self.HdList, ["x264", "H.264"], ["Blu-ray", "HD-DVD"], ["1080p"]
                )
            elif (
                releaseInfo.Source == "Blu-ray" or releaseInfo.Source == "HD-DVD"
            ) and releaseInfo.ResolutionType == "720p":
                return PtpMovieSearchResult.__IsInList(
                    self.HdList, ["x264", "H.264"], ["Blu-ray", "HD-DVD"], ["720p"]
                )

        raise PtpUploaderException(
            "Can't check whether the release exist on PTP because its type is unsupported."
        )

    def __IsHdNonFineSourceReleaseExists(self, releaseInfo, releaseSourceScore):
        if releaseInfo.IsRemux():
            return PtpMovieSearchResult.__IsInListUsingSourceScore(
                self.HdList, None, releaseSourceScore, ["1080i", "1080p"], True
            )
        else:
            if releaseInfo.Source == "WEB":
                return PtpMovieSearchResult.__IsInListUsingSourceScore(
                    self.HdList,
                    ["x264", "H.264"],
                    releaseSourceScore,
                    ["720p", "1080p"],
                )
            else:
                if releaseInfo.ResolutionType == "1080p":
                    return PtpMovieSearchResult.__IsInListUsingSourceScore(
                        self.HdList,
                        ["x264", "H.264"],
                        releaseSourceScore,
                        ["1080p"],
                        releaseInfo.IsRemux(),
                    )
                elif releaseInfo.ResolutionType == "720p":
                    return PtpMovieSearchResult.__IsInListUsingSourceScore(
                        self.HdList, ["x264", "H.264"], releaseSourceScore, ["720p"]
                    )

        raise PtpUploaderException(
            "Can't check whether the release exist on PTP because its type is unsupported."
        )

    def __IsUhdFineSourceReleaseExists(self, releaseInfo):
        if releaseInfo.IsRemux():
            if releaseInfo.Source == "Blu-ray":
                return PtpMovieSearchResult.__IsInList(
                    self.UhdList, None, ["Blu-ray"], ["4K"], True
                )
        else:
            if releaseInfo.Source == "Blu-ray" and releaseInfo.ResolutionType == "4K":
                return PtpMovieSearchResult.__IsInList(
                    self.UhdList,
                    ["x264", "x265", "H.264", "H.265"],
                    ["Blu-ray"],
                    ["4K"],
                )

        raise PtpUploaderException(
            "Can't check whether the release exist on PTP because its type is unsupported."
        )

    def __IsUhdNonFineSourceReleaseExists(self, releaseInfo, releaseSourceScore):
        if releaseInfo.IsRemux():
            return PtpMovieSearchResult.__IsInListUsingSourceScore(
                self.UhdList, None, releaseSourceScore, ["4K"], True
            )
        else:
            if releaseInfo.Source == "WEB":
                return PtpMovieSearchResult.__IsInListUsingSourceScore(
                    self.UhdList,
                    ["x264", "x265", "H.264", "H.265"],
                    releaseSourceScore,
                    ["4K"],
                )
            else:
                if releaseInfo.ResolutionType == "4K":
                    return PtpMovieSearchResult.__IsInListUsingSourceScore(
                        self.UhdList,
                        ["x264", "x265", "H.264", "H.265"],
                        releaseSourceScore,
                        ["4K"],
                        releaseInfo.IsRemux(),
                    )

        raise PtpUploaderException(
            "Can't check whether the release exist on PTP because its type is unsupported."
        )

    @staticmethod
    def __CanCoExist(existingReleases, releaseInfo, minimumSizeDifferenceToCoExist):
        if len(existingReleases) <= 0:
            return None
        elif len(existingReleases) >= 2:
            return existingReleases[0]

        existingRelease = existingReleases[0]

        # If size is not set, we can't compare.
        if releaseInfo.Size == 0 or existingRelease.Size == 0:
            return existingRelease

        # If the current release is significantly larger than the existing one then we don't treat it as a duplicate.
        if releaseInfo.Size > (existingRelease.Size + minimumSizeDifferenceToCoExist):
            return None
        else:
            return existingRelease

    # From the rules:
    # "In general terms, 1CD (700MB) and 2CD (1400MB) XviD rips may always co-exist, same as 2CD (1400MB) and 3CD (2100MB) in the case of longer movies (2 hours+). Those sizes should only be used as general indicators as many rips may fall above or below them."
    # "PAL and NTSC may co-exist, as may DVD5 and DVD9."
    def __IsSdFineSourceReleaseExists(self, releaseInfo):
        # 600 MB seems like a good choice. Comparing by size ratio wouldn't be too effective.
        minimumSizeDifferenceToCoExist = 600 * 1024 * 1024

        if (
            releaseInfo.Source == "Blu-ray"
            or releaseInfo.Source == "HD-DVD"
            or releaseInfo.Source == "DVD"
        ):
            if releaseInfo.Codec == "x264" or releaseInfo.Codec == "H.264":
                # We can't check to co-existence for SD x264s, because the co-existence rule is quality based.
                return PtpMovieSearchResult.__IsInList(
                    self.SdList, ["x264", "H.264"], ["Blu-ray", "HD-DVD", "DVD"]
                )
            elif releaseInfo.Codec == "XviD" or releaseInfo.Codec == "DivX":
                list = PtpMovieSearchResult.__GetListOfMatches(
                    self.SdList, ["XviD", "DivX"], ["Blu-ray", "HD-DVD", "DVD"]
                )
                return PtpMovieSearchResult.__CanCoExist(
                    list, releaseInfo, minimumSizeDifferenceToCoExist
                )
            elif releaseInfo.IsDvdImage():
                if (
                    releaseInfo.ResolutionType == "NTSC"
                    or releaseInfo.ResolutionType == "PAL"
                ):
                    return PtpMovieSearchResult.__IsInList(
                        self.SdList,
                        [releaseInfo.Codec],
                        ["DVD"],
                        [releaseInfo.ResolutionType],
                    )
                else:
                    raise PtpUploaderException(
                        "Can't check whether the DVD image exist on PTP because resolution (NTSC or PAL) is not set."
                    )

        raise PtpUploaderException(
            "Can't check whether the release exist on PTP because its type is unsupported."
        )

    def __IsSdNonFineSourceReleaseExists(self, releaseInfo, releaseSourceScore):
        if (
            releaseInfo.Codec == "DivX"
            or releaseInfo.Codec == "XviD"
            or releaseInfo.Codec == "H.264"
            or releaseInfo.Codec == "x264"
        ):
            return PtpMovieSearchResult.__IsInListUsingSourceScore(
                self.SdList, ["DivX", "XviD", "x264", "H.264"], releaseSourceScore
            )

        raise PtpUploaderException(
            "Can't check whether the release exist on PTP because its type is unsupported."
        )

    def IsMoviePageExists(self):
        return len(self.PtpId) > 0

    def IsReleaseExists(self, releaseInfo):
        if not self.IsMoviePageExists():
            return None

        # We can't check if a special release is duplicate or not, but only manually edited jobs can be special releases so we allow them without checking.
        if releaseInfo.IsSpecialRelease():
            return None

        # Not too nice, but this is the easiest way to do ignore the torrents in duplicate checking.
        if releaseInfo.DuplicateCheckCanIgnore > 0:
            newList = []
            for item in self.SdList:
                if releaseInfo.IsTorrentNeedsDuplicateChecking(item.TorrentId):
                    newList.append(item)
            self.SdList = newList

            newList = []
            for item in self.HdList:
                if releaseInfo.IsTorrentNeedsDuplicateChecking(item.TorrentId):
                    newList.append(item)
            self.HdList = newList

            newList = []
            for item in self.UhdList:
                if releaseInfo.IsTorrentNeedsDuplicateChecking(item.TorrentId):
                    newList.append(item)
            self.UhdList = newList

            if (len(self.SdList) + len(self.HdList) + len(self.UhdList)) <= 0:
                return None

        releaseSourceScore = GetSourceScore(releaseInfo.Source)
        if releaseSourceScore == -1:
            raise PtpUploaderException("Unsupported source '%s'." % releaseInfo.Source)

        # If source is not DVD/HD-DVD/Blu-ray then we check if there is a release with any proper quality (retail) sources.
        # If there is, we won't add this lower quality release.
        if not PtpMovieSearchResult.__IsFineSource(releaseInfo.Source):
            if releaseInfo.IsHighDefinition() or releaseInfo.IsUltraHighDefinition():
                # If HD retail release already exists, then we don't allow a pre-retail HD or UHD release.
                for item in self.HdList:
                    if PtpMovieSearchResult.__IsFineSource(item.Source):
                        return item

                # If UHD retail release already exists, then we don't allow a pre-retail HD or UHD release.
                for item in self.UhdList:
                    if PtpMovieSearchResult.__IsFineSource(item.Source):
                        return item

                # If SD release with retail HD source already exists, then we don't allow a pre-retail HD or UHD release.
                # E.g.: if a Blu-ray sourced SD XviD exists, then we don't allow a 720p HDTV rip.
                list = PtpMovieSearchResult.__GetListOfMatches(
                    self.SdList, None, ["Blu-ray", "HD-DVD"]
                )
                if len(list) > 0:
                    return list[0]
            elif releaseInfo.IsStandardDefinition():
                # If SD, HD or UHD retail release already exists, then we don't allow a pre-retail SD release.

                for item in self.SdList:
                    if PtpMovieSearchResult.__IsFineSource(item.Source):
                        return item

                for item in self.HdList:
                    if PtpMovieSearchResult.__IsFineSource(item.Source):
                        return item

                for item in self.UhdList:
                    if PtpMovieSearchResult.__IsFineSource(item.Source):
                        return item
            else:
                raise PtpUploaderException(
                    "Can't check whether the release exists on PTP because its type is unsupported."
                )

        if releaseInfo.IsHighDefinition():
            if PtpMovieSearchResult.__IsFineSource(releaseInfo.Source):
                return self.__IsHdFineSourceReleaseExists(releaseInfo)
            else:
                return self.__IsHdNonFineSourceReleaseExists(
                    releaseInfo, releaseSourceScore
                )
        elif releaseInfo.IsStandardDefinition():
            if PtpMovieSearchResult.__IsFineSource(releaseInfo.Source):
                return self.__IsSdFineSourceReleaseExists(releaseInfo)
            else:
                return self.__IsSdNonFineSourceReleaseExists(
                    releaseInfo, releaseSourceScore
                )
        elif releaseInfo.IsUltraHighDefinition():
            if PtpMovieSearchResult.__IsFineSource(releaseInfo.Source):
                return self.__IsUhdFineSourceReleaseExists(releaseInfo)
            else:
                return self.__IsUhdNonFineSourceReleaseExists(
                    releaseInfo, releaseSourceScore
                )

        raise PtpUploaderException(
            "Can't check whether the release exists on PTP because its type is unsupported."
        )

    def GetLatestTorrent(self):
        latestTorrent = None
        latestTorrentId = 0

        for item in self.SdList:
            if item.TorrentId > latestTorrentId:
                latestTorrentId = item.TorrentId
                latestTorrent = item

        for item in self.HdList:
            if item.TorrentId > latestTorrentId:
                latestTorrentId = item.TorrentId
                latestTorrent = item

        for item in self.UhdList:
            if item.TorrentId > latestTorrentId:
                latestTorrentId = item.TorrentId
                latestTorrent = item

        for item in self.OtherList:
            if item.TorrentId > latestTorrentId:
                latestTorrentId = item.TorrentId
                latestTorrent = item

        return latestTorrent
