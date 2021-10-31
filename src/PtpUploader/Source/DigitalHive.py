import re

from PtpUploader.Helper import DecodeHtmlEntities, GetSizeFromText
from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.NfoParser import NfoParser
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.ReleaseNameParser import ReleaseNameParser
from PtpUploader.Source.SourceBase import SourceBase


class DigitalHive(SourceBase):
    def __init__(self):
        SourceBase.__init__(self)

        self.Name = "dh"
        self.NameInSettings = "DigitalHive"

    def IsEnabled(self):
        return len(self.Username) > 0 and len(self.Password) > 0

    def Login(self):
        MyGlobals.Logger.info("Logging in to DigitalHive.")

        # DigitalHive stores a cookie when login.php is loaded that is needed for takelogin.php.
        MyGlobals.session.get("https://www.digitalhive.org/login.php")

        postData = {"username": self.Username, "password": self.Password}
        result = MyGlobals.session.post(
            "https://www.digitalhive.org/takelogin.php", data=postData
        )
        result.raise_for_status()
        self.__CheckIfLoggedInFromResponse(result.text)

    def __CheckIfLoggedInFromResponse(self, response):
        if (
            response.find("""action='takelogin.php'""") != -1
            or response.find("""<a href='login.php'>Back to Login</a>""") != -1
        ):
            raise PtpUploaderException(
                "Looks like you are not logged in to DigitalHive. Probably due to the bad user name or password in settings."
            )

    def __GetTorrentPageAsString(self, logger, releaseInfo):
        url = (
            "https://www.digitalhive.org/details.php?id=%s" % releaseInfo.AnnouncementId
        )
        logger.info("Downloading description from page '%s'." % url)

        result = MyGlobals.session.get(url)
        result.raise_for_status()
        response = result.text
        self.__CheckIfLoggedInFromResponse(response)

        # Make sure we only get information from the description and not from the comments.
        descriptionEndIndex = response.find("""<p><a name="startcomments"></a></p>""")
        if descriptionEndIndex == -1:
            raise PtpUploaderException(
                JobRunningState.Ignored_MissingInfo,
                "Description can't found. Probably the layout of the site has changed.",
            )

        description = response[:descriptionEndIndex]
        return description

    def __TryGettingImdbIdFromNfoPage(self, logger, releaseInfo):
        url = (
            "https://www.digitalhive.org/viewnfo.php?id=%s" % releaseInfo.AnnouncementId
        )
        logger.info("Downloading NFO from page '%s'." % url)

        result = MyGlobals.session.get(url)
        result.raise_for_status()
        response = result.text
        response = response.encode("ascii", "ignore")
        self.__CheckIfLoggedInFromResponse(response)

        releaseInfo.ImdbId = NfoParser.GetImdbId(response)

    def __ReadTorrentPageInternal(self, logger, releaseInfo, description):
        # Get release name.
        matches = re.search(
            r"<title>Digital Hive :: Details for torrent &quot;(.+)&quot;</title>",
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
            if not releaseInfo.ImdbId:
                self.__TryGettingImdbIdFromNfoPage(logger, releaseInfo)

        # Get size.
        # Two possible formats:
        # <tr><td class="heading" valign="top" align="right">Size</td><td valign="top" align="left">4.47 GB (4,799,041,437bytes )</td></tr>
        # <tr><td class='heading' valign='top' align='right'>Size</td><td valign='top' align='left'>4.47 GB (4,799,041,437bytes )</td></tr>
        matches = re.search(
            r"""<tr><th><b>Size</b></th><th>.+ \((.+bytes) ?\)</th></tr>""", description
        )
        if matches is None:
            logger.warning("Size not found on torrent page.")
        else:
            size = matches.group(1)
            releaseInfo.Size = GetSizeFromText(size)

        return releaseName

    # Sets IMDb if presents in the torrent description.
    # Sets scene release if pretime presents on the page.
    # Returns with the release name.
    def __ReadTorrentPage(self, logger, releaseInfo):
        description = self.__GetTorrentPageAsString(logger, releaseInfo)
        releaseName = self.__ReadTorrentPageInternal(logger, releaseInfo, description)
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
                "Announcement release name '%s' and release name '%s' on DigitalHive are different."
                % (releaseInfo.ReleaseName, releaseName)
            )

        if releaseNameParser.Scene:
            releaseInfo.SetSceneRelease()

        if (not releaseInfo.SceneRelease) and self.AutomaticJobFilter == "SceneOnly":
            raise PtpUploaderException(JobRunningState.Ignored, "Non-scene release.")

    def PrepareDownload(self, logger, releaseInfo):
        if releaseInfo.IsUserCreatedJob():
            self.__HandleUserCreatedJob(logger, releaseInfo)
        else:
            self.__HandleAutoCreatedJob(logger, releaseInfo)

    def DownloadTorrent(self, logger, releaseInfo, path):
        url = (
            "https://www.digitalhive.org/download.php?id=%s&https=no"
            % releaseInfo.AnnouncementId
        )
        logger.info("Downloading torrent file from '%s' to '%s'." % (url, path))

        result = MyGlobals.session.get(url)
        result.raise_for_status()
        response = result.content
        self.__CheckIfLoggedInFromResponse(response)

        file = open(path, "wb")
        file.write(response)
        file.close()

        # Calling Helper.ValidateTorrentFile is not needed because NfoParser.IsTorrentContainsMultipleNfos will throw an exception if it is not a valid torrent file.

        # If a torrent contains multiple NFO files then it is likely that the site also showed the wrong NFO and we have checked the existence of another movie on PTP.
        # So we abort here. These errors happen rarely anyway.
        # (We could also try read the NFO with the same name as the release or with the same name as the first RAR and reschedule for checking with the correct IMDb id.)
        if NfoParser.IsTorrentContainsMultipleNfos(path):
            raise PtpUploaderException(
                "Torrent '%s' contains multiple NFO files." % path
            )

    def GetIdFromUrl(self, url):
        result = re.match(r".*digitalhive\.org/details\.php\?id=(\d+).*", url)
        if result is None:
            return ""
        else:
            return result.group(1)

    def GetUrlFromId(self, id):
        return "https://www.digitalhive.org/details.php?id=" + id

    def GetIdFromAutodlIrssiUrl(self, url):
        # https://www.digitalhive.org/download.php?id=1336019&https=no&name=Rogue.One.2016.1080p.BluRay.x264-SPARKS.torrent
        result = re.match(r".*digitalhive\.org/download\.php\?id=(\d+).*", url)
        if result is None:
            return ""
        else:
            return result.group(1)
