import os
import re

from PtpUploader.Helper import (
    DecodeHtmlEntities,
    GetFileListFromTorrent,
    GetSizeFromText,
    RemoveDisallowedCharactersFromPath,
    ValidateTorrentFile,
)
from PtpUploader.InformationSource.Imdb import Imdb
from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Source.SourceBase import SourceBase


class Cinematik(SourceBase):
    def __init__(self):
        SourceBase.__init__(self)

        self.Name = "tik"
        self.NameInSettings = "Cinematik"

    def IsEnabled(self):
        return len(self.Username) > 0 and len(self.Password) > 0

    def Login(self):
        MyGlobals.Logger.info("Logging in to Cinematik.")

        postData = {"username": self.Username, "password": self.Password}
        result = MyGlobals.session.post(
            "http://cinematik.net/takelogin.php", data=postData
        )
        result.raise_for_status()
        self.__CheckIfLoggedInFromResponse(result.text)

    def __CheckIfLoggedInFromResponse(self, response):
        if (
            response.find('action="takelogin.php"') != -1
            or response.find("<h2>Login failed!</h2>") != -1
        ):
            raise PtpUploaderException(
                "Looks like you are not logged in to Cinematik. Probably due to the bad user name or password in settings."
            )

    def __DownloadNfo(self, logger, releaseInfo):
        url = (
            "http://cinematik.net/details.php?id=%s&filelist=1"
            % releaseInfo.AnnouncementId
        )
        logger.info("Collecting info from torrent page '%s'." % url)

        result = MyGlobals.session.get(url)
        result.raise_for_status()
        response = result.text
        self.__CheckIfLoggedInFromResponse(response)

        # Make sure we only get information from the description and not from the comments.
        descriptionEndIndex = response.find('<p><a name="startcomments"></a></p>')
        if descriptionEndIndex == -1:
            raise PtpUploaderException(
                JobRunningState.Ignored_MissingInfo,
                "Description can't found on torrent page. Probably the layout of the site has changed.",
            )

        description = response[:descriptionEndIndex]

        # Get source and format type
        # <title>Cinematik :: Behind the Mask: The Rise of Leslie Vernon (2006) NTSC DVD9 VIDEO_TS</title>
        matches = re.search(
            r"<title>Cinematik :: (.+?) \((\d+)\) (.+?) (.+?) (.+?)</title>",
            description,
        )
        if matches is None:
            raise PtpUploaderException(
                JobRunningState.Ignored_MissingInfo,
                "Can't get resolution type, codec and container from torrent page.",
            )

        title = DecodeHtmlEntities(matches.group(1)).strip()
        year = DecodeHtmlEntities(matches.group(2)).strip()
        resolutionType = DecodeHtmlEntities(matches.group(3)).strip()
        codec = DecodeHtmlEntities(matches.group(4)).strip()
        container = DecodeHtmlEntities(matches.group(5)).strip()

        releaseName = "%s (%s) %s %s" % (title, year, resolutionType, codec)
        releaseInfo.ReleaseName = RemoveDisallowedCharactersFromPath(releaseName)

        # Get IMDb id.
        if (not releaseInfo.HasImdbId()) and (not releaseInfo.PtpId):
            matches = re.search(r"imdb\.com/title/tt(\d+)", description)
            if matches is None:
                raise PtpUploaderException(
                    JobRunningState.Ignored_MissingInfo,
                    "IMDb id can't be found on torrent page.",
                )

            releaseInfo.ImdbId = matches.group(1)

        # Get size.
        # Two formats:
        # <td class="heading" align="right" valign="top">Size</td><td align="left" valign="top">6.81 GB &nbsp;&nbsp;&nbsp;(7,313,989,632 bytes)</td>
        # <td class="heading" valign="top" align="right">Size</td><td valign="top" align="left">4.38 GB    (4,699,117,568 bytes)</td>
        matches = re.search(
            r"""<td class="heading" v?align=".+?" v?align=".+?">Size</td><td v?align=".+?" v?align=".+?">.+\((.+ bytes)\)</td>""",
            description,
        )
        if matches is None:
            logger.warning("Size not found on torrent page.")
        else:
            size = matches.group(1)
            releaseInfo.Size = GetSizeFromText(size)

        return resolutionType, codec, container

    def __MapInfoFromTorrentDescriptionToPtp(
        self, releaseInfo, resolutionType, codec, container
    ):
        resolutionType = resolutionType.lower()
        codec = codec.lower()
        container = container.lower()

        if releaseInfo.IsResolutionTypeSet():
            releaseInfo.Logger.info(
                "Resolution type '%s' is already set, not getting from the torrent page."
                % releaseInfo.ResolutionType
            )
        elif resolutionType == "ntsc":
            releaseInfo.ResolutionType = "NTSC"
        elif resolutionType == "pal":
            releaseInfo.ResolutionType = "PAL"
        else:
            raise PtpUploaderException(
                JobRunningState.Ignored_NotSupported,
                "Unsupported resolution type '%s'." % resolutionType,
            )

        if releaseInfo.Codec and releaseInfo.Source:
            releaseInfo.Logger.info(
                "Codec '%s' and source '%s' are already set, not getting from the torrent page."
                % (releaseInfo.Codec, releaseInfo.Source)
            )
        elif codec == "dvd5":
            releaseInfo.Codec = "DVD5"
            releaseInfo.Source = "DVD"
        elif codec == "dvd9":
            releaseInfo.Codec = "DVD9"
            releaseInfo.Source = "DVD"
        else:
            raise PtpUploaderException(
                JobRunningState.Ignored_NotSupported,
                "Unsupported codec type '%s'." % codec,
            )

        if releaseInfo.IsContainerSet():
            releaseInfo.Logger.info(
                "Container '%s' is already set, not getting from the torrent page."
                % releaseInfo.Container
            )
        elif container == "video_ts" or container == "video_ts [widescreen]":
            releaseInfo.Container = "VOB IFO"
        else:
            raise PtpUploaderException(
                JobRunningState.Ignored_NotSupported,
                "Unsupported container type '%s'." % container,
            )

    def PrepareDownload(self, logger, releaseInfo):
        resolutionType = ""
        codec = ""
        container = ""

        if releaseInfo.IsUserCreatedJob():
            resolutionType, codec, container = self.__DownloadNfo(logger, releaseInfo)
        else:
            # TODO: add filterting support for Cinematik
            resolutionType, codec, container = self.__DownloadNfo(logger, releaseInfo)

        self.__MapInfoFromTorrentDescriptionToPtp(
            releaseInfo, resolutionType, codec, container
        )

    def __ValidateTorrentFile(self, torrentPath):
        files = GetFileListFromTorrent(torrentPath)
        for file in files:
            file = file.lower()

            # Make sure it doesn't contains ISO files.
            if file.endswith(".iso"):
                raise PtpUploaderException(
                    JobRunningState.Ignored_NotSupported,
                    "Found an ISO file in the torrent.",
                )

            # Make sure that all files are in the VIDEO_TS folder. (This is needed because of the uploading rules on PTP.)
            if not file.startswith("video_ts"):
                raise PtpUploaderException(
                    JobRunningState.Ignored_NotSupported,
                    "Files are not in the VIDEO_TS folder in the torrent.",
                )

    def DownloadTorrent(self, logger, releaseInfo, path):
        url = "http://cinematik.net/download.php?id=%s" % releaseInfo.AnnouncementId
        logger.info("Downloading torrent file from '%s' to '%s'." % (url, path))

        result = MyGlobals.session.get(url)
        result.raise_for_status()
        response = result.content
        self.__CheckIfLoggedInFromResponse(response)

        file = open(path, "wb")
        file.write(response)
        file.close()

        ValidateTorrentFile(path)
        self.__ValidateTorrentFile(path)

    # TODO: Cinematik: use a shared function with Cinemageddon
    # Because some of the releases on Cinematik do not contain the full name of the movie, we have to rename them because of the uploading rules on PTP.
    # The new name will be formatted like this: Movie Name Year
    def GetCustomUploadPath(self, logger, releaseInfo):
        # TODO: if the user forced a release name, then let it upload by that name.
        if releaseInfo.IsZeroImdbId():
            raise PtpUploaderException(
                "Uploading to Cinematik with zero IMDb ID is not yet supported."
            )

        # If the movie already exists on PTP then the IMDb info is not populated in ReleaseInfo.
        if len(releaseInfo.InternationalTitle) <= 0 or len(releaseInfo.Year) <= 0:
            imdbInfo = Imdb.GetInfo(logger, releaseInfo.GetImdbId())
            if len(releaseInfo.InternationalTitle) <= 0:
                releaseInfo.InternationalTitle = imdbInfo.Title
            if len(releaseInfo.Year) <= 0:
                releaseInfo.Year = imdbInfo.Year

        if len(releaseInfo.InternationalTitle) <= 0:
            raise PtpUploaderException(
                "Can't rename release because international title is empty."
            )

        if len(releaseInfo.Year) <= 0:
            raise PtpUploaderException("Can't rename release because year is empty.")

        name = "%s (%s) %s %s" % (
            releaseInfo.InternationalTitle,
            releaseInfo.Year,
            releaseInfo.ResolutionType,
            releaseInfo.Codec,
        )
        name = RemoveDisallowedCharactersFromPath(name)

        logger.info(
            "Upload directory will be named '%s' instead of '%s'."
            % (name, releaseInfo.ReleaseName)
        )

        newUploadPath = releaseInfo.GetReleaseUploadPath()
        newUploadPath = os.path.dirname(newUploadPath)
        newUploadPath = os.path.join(newUploadPath, name)
        return newUploadPath

    def IncludeReleaseNameInReleaseDescription(self):
        return False

    def GetIdFromUrl(self, url):
        result = re.match(r".*cinematik\.net/details.php\?id=(\d+).*", url)
        if result is None:
            return ""
        else:
            return result.group(1)

    def GetUrlFromId(self, id):
        return "http://cinematik.net/details.php?id=" + id
