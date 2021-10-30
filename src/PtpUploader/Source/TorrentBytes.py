import re

from PtpUploader.Helper import (
    DecodeHtmlEntities,
    GetSizeFromText,
    MakeRetryingHttpGetRequestWithRequests,
    MakeRetryingHttpPostRequestWithRequests,
)
from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.NfoParser import NfoParser
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.ReleaseNameParser import ReleaseNameParser
from PtpUploader.Source.SourceBase import SourceBase


class TorrentBytes(SourceBase):
    def __init__(self):
        SourceBase.__init__(self)

        self.Name = "tb"
        self.NameInSettings = "TorrentBytes"

    def LoadSettings(self, settings):
        SourceBase.LoadSettings(self, settings)

    def IsEnabled(self):
        return len(self.Username) > 0 and len(self.Password) > 0

    def Login(self):
        MyGlobals.Logger.info("Logging in to TorrentBytes.")

        postData = {
            "username": self.Username,
            "password": self.Password,
            "login": "Log in!",
        }
        result = MakeRetryingHttpPostRequestWithRequests(
            "https://www.torrentbytes.net/takelogin.php", postData
        )
        self.__CheckIfLoggedInFromResponse(result.text)

    def __CheckIfLoggedInFromResponse(self, response):
        if response.find('<form method="post" action="takelogin.php">') >= 0:
            raise PtpUploaderException(
                "Looks like you are not logged in to TorrentBytes. Probably due to the bad user name or password in settings."
            )

    # Sets IMDb if presents in the torrent description.
    # Returns with the release name.
    def __ReadTorrentPage(self, logger, releaseInfo):
        url = (
            "https://www.torrentbytes.net/details.php?id=" + releaseInfo.AnnouncementId
        )
        logger.info("Downloading NFO from page '%s'." % url)

        result = MakeRetryingHttpGetRequestWithRequests(url)
        response = result.text
        self.__CheckIfLoggedInFromResponse(response)

        # Make sure we only get information from the description and not from the comments.
        descriptionEndIndex = response.find("""<p><a name="startcomments"></a></p>""")
        if descriptionEndIndex < 0:
            raise PtpUploaderException(
                JobRunningState.Ignored_MissingInfo,
                "Description can't found. Probably the layout of the site has changed.",
            )

        description = response[:descriptionEndIndex]

        # Get release name.
        matches = re.search(
            r"""<title>Torrentbytes :: Details for torrent "(.+)"</title>""",
            description,
        )
        if matches is None:
            raise PtpUploaderException(
                JobRunningState.Ignored_MissingInfo,
                "Release name can't be found on torrent page.",
            )

        releaseName = DecodeHtmlEntities(matches.group(1))

        # Get IMDb id.
        if (not releaseInfo.ImdbId) and (not releaseInfo.PtpId):
            releaseInfo.ImdbId = NfoParser.GetImdbId(description)

        # Get size.
        # <tr><td class="heading" valign="top" align="right">Size</td><td valign="top" align=left>3.30 GB (3,543,492,217 bytes)</td></tr>
        matches = re.search(
            r""">Size</td><td valign="top" align=left>.+ \((.+ bytes)\)</td>""",
            description,
        )
        if matches is None:
            logger.warning("Size not found on torrent page.")
        else:
            size = matches.group(1)
            releaseInfo.Size = GetSizeFromText(size)

        return releaseName

    def __HandleUserCreatedJob(self, logger, releaseInfo):
        releaseName = self.__ReadTorrentPage(logger, releaseInfo)
        if not releaseInfo.ReleaseName:
            releaseInfo.ReleaseName = releaseName

        releaseNameParser = ReleaseNameParser(releaseInfo.ReleaseName)
        releaseNameParser.GetSourceAndFormat(releaseInfo)
        if releaseNameParser.Scene:
            releaseInfo.SetSceneRelease()

    def __HandleAutoCreatedJob(self, logger, releaseInfo):
        # In case of automatic announcement we have to check the release name if it is valid.
        # We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source.
        releaseNameParser = ReleaseNameParser(releaseInfo.ReleaseName)
        isAllowedMessage = releaseNameParser.IsAllowed()
        if isAllowedMessage is not None:
            raise PtpUploaderException(JobRunningState.Ignored, isAllowedMessage)

        releaseNameParser.GetSourceAndFormat(releaseInfo)

        releaseName = self.__ReadTorrentPage(logger, releaseInfo)
        if releaseName != releaseInfo.ReleaseName:
            raise PtpUploaderException(
                "Announcement release name '%s' and release name '%s' on TorrentBytes are different."
                % (releaseInfo.ReleaseName, releaseName)
            )

        if releaseNameParser.Scene:
            releaseInfo.SetSceneRelease()

        if (
            not releaseInfo.SceneRelease
        ) and self.AutomaticJobFilter == "SceneOnly":
            raise PtpUploaderException(JobRunningState.Ignored, "Non-scene release.")

    def PrepareDownload(self, logger, releaseInfo):
        if releaseInfo.IsUserCreatedJob():
            self.__HandleUserCreatedJob(logger, releaseInfo)
        else:
            self.__HandleAutoCreatedJob(logger, releaseInfo)

    def DownloadTorrent(self, logger, releaseInfo, path):
        # We don't log the download URL because it is sensitive information.
        logger.info("Downloading torrent file from TorrentBytes to '%s'." % path)

        url = (
            "https://www.torrentbytes.net/download.php?id=%s&SSL=1"
            % releaseInfo.AnnouncementId
        )
        result = MakeRetryingHttpGetRequestWithRequests(url)
        response = result.content
        self.__CheckIfLoggedInFromResponse(response)

        f = open(path, "wb")
        f.write(response)
        f.close()

        # Calling Helper.ValidateTorrentFile is not needed because NfoParser.IsTorrentContainsMultipleNfos will throw an exception if it is not a valid torrent file.

        # If a torrent contains multiple NFO files then it is likely that the site also showed the wrong NFO and we have checked the existence of another movie on PTP.
        # So we abort here. These errors happen rarely anyway.
        # (We could also try read the NFO with the same name as the release or with the same name as the first RAR and reschedule for checking with the correct IMDb id.)
        if NfoParser.IsTorrentContainsMultipleNfos(path):
            raise PtpUploaderException(
                "Torrent '%s' contains multiple NFO files." % path
            )

    def GetIdFromUrl(self, url):
        result = re.match(r".*torrentbytes\.net/details.php\?id=(\d+).*", url)
        if result is None:
            return ""
        else:
            return result.group(1)

    def GetUrlFromId(self, id):
        return "https://www.torrentbytes.net/details.php?id=" + id

    def GetIdFromAutodlIrssiUrl(self, url):
        # http://torrentbytes.net/download.php/897257/
        result = re.match(r".*torrentbytes\.net/download.php\?id=(\d+).*", url)
        if result is None:
            return ""
        else:
            return result.group(1)
