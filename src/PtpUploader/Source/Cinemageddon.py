import html
import logging
import os
import re

from guessit import guessit
import unidecode

from PtpUploader.Helper import (
    GetSizeFromText,
    RemoveDisallowedCharactersFromPath,
    ValidateTorrentFile,
)
from PtpUploader.InformationSource.Imdb import Imdb
from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Source.SourceBase import SourceBase


logger = logging.getLogger(__name__)


class Cinemageddon(SourceBase):
    def __init__(self):
        SourceBase.__init__(self)

        self.Name = "cg"
        self.NameInSettings = "Cinemageddon"

    def LoadSettings(self, _):
        super().LoadSettings(_)
        self.Username = self.settings.username
        self.Password = self.settings.password

    def Login(self):
        logger.info("Logging in to Cinemageddon.")

        if "cinemageddon.net" not in MyGlobals.session.cookies.list_domains():
            postData = {"username": self.Username, "password": self.Password}
            result = MyGlobals.session.post(
                "https://cinemageddon.net/takelogin.php", data=postData
            )
            result.raise_for_status()
            self.__CheckIfLoggedInFromResponse(result.content)
            MyGlobals.SaveCookies()
        else:
            logger.debug("Re-using Cinemageddon cookies.")

    def __CheckIfLoggedInFromResponse(self, response: bytes):
        if b'action="takelogin.php"' in response or b"Login failed!" in response:
            raise PtpUploaderException(
                f"Looks like you are not logged in to Cinemageddon. Probably due to the bad user name or password in settings. Response: {response.decode()}"
            )

    def __ParsePage(
        self, _, releaseInfo, raw_html: bytes, parseForExternalCreateJob=False
    ):
        # Make sure we only get information from the description and not from the comments.
        descriptionEndIndex = raw_html.find(b'<p><a name="startcomments"></a></p>')
        if descriptionEndIndex == -1:
            raise PtpUploaderException(
                JobRunningState.Ignored_MissingInfo,
                "Description can't found on torrent page. Probably the layout of the site has changed.",
            )

        description: bytes = raw_html[:descriptionEndIndex]

        # We will use the torrent's name as release name.
        if not parseForExternalCreateJob:
            matches = re.search(
                rb'href="download.php\?id=(\d+)&name=.+">(.+)\.torrent</a>', description
            )
            if matches is None:
                raise PtpUploaderException(
                    JobRunningState.Ignored_MissingInfo,
                    "Can't get release name from torrent page.",
                )

            releaseInfo.ReleaseName = html.unescape(matches.group(2).decode())

        # Get source and format type
        sourceType = ""
        formatType = ""
        if not releaseInfo.Source or not releaseInfo.Codec:
            matches = None
            if parseForExternalCreateJob:
                matches = re.search(
                    rb'torrent details for "(.+) \[(\d+)/(.+)/(.+)\]"', description
                )
            else:
                matches = re.search(
                    rb"torrent details for &quot;(.+) \[(\d+)/(.+)/(.+)\]&quot;",
                    description,
                )

            if matches is None:
                raise PtpUploaderException(
                    JobRunningState.Ignored_MissingInfo,
                    "Can't get release source and format type from torrent page.",
                )

            sourceType = matches.group(3).decode()
            formatType = matches.group(4).decode()

            if "/" in sourceType and not releaseInfo.ResolutionType:
                sourceType, _, resolutionType = sourceType.partition("/")
                resolutionType.strip("p")
                if resolutionType in ["576", "720", "1080"]:
                    releaseInfo.ResolutionType = resolutionType + "p"
                else:
                    releaseInfo.ResolutionType = "Other"

        # Get IMDb id.
        if (not releaseInfo.ImdbId) and (not releaseInfo.PtpId):
            match = re.search(
                r'<span id="torrent_imdb">(.*?)</span>',
                description.decode(errors="ignore"),
            )
            if not match:
                raise PtpUploaderException(
                    JobRunningState.Ignored_MissingInfo,
                    "IMDb container can't be found on torrent page.",
                )
            imdbs = match.group(1).replace("t", "").split(" ")
            if not imdbs:
                raise PtpUploaderException(
                    JobRunningState.Ignored_MissingInfo,
                    "IMDb id can't be found on torrent page.",
                )
            if len(imdbs) > 1:
                raise PtpUploaderException(
                    JobRunningState.Ignored_MissingInfo,
                    "Multiple IMDb IDs found on page.",
                )

            releaseInfo.ImdbId = imdbs[0]

        # Get size.
        # Two possible formats:
        # <tr><td class="rowhead" valign="top" align="right">Size</td><td valign="top" align="left">1.46 GB (1,570,628,119 bytes)</td></tr>
        # <tr><td class="rowhead" valign="top" align="right">Size</td><td valign="top" align=left>1.46 GB (1,570,628,119 bytes)</td></tr>
        matches = re.search(
            rb"""<tr><td class="rowhead" valign="top" align="right">Size</td><td valign="top" align="?left"?>.+ \((.+ bytes)\)</td></tr>""",
            description,
        )
        if matches is None:
            releaseInfo.logger().warning("Size not found on torrent page.")
        else:
            size: bytes = matches.group(1)
            releaseInfo.Size = GetSizeFromText(size.decode())

        # Ignore XXX releases.
        if description.find(b'>Type</td><td valign="top" align=left>XXX<') != -1:
            raise PtpUploaderException(
                JobRunningState.Ignored_Forbidden, "Marked as XXX."
            )

        self.__MapSourceAndFormatToPtp(releaseInfo, sourceType, formatType, raw_html)

        # Make sure that this is not a wrongly categorized DVDR.
        if (not releaseInfo.IsDvdImage()) and (
            re.search(rb"\.vob</td>", description, re.IGNORECASE)
            or re.search(rb"\.iso</td>", description, re.IGNORECASE)
        ):
            raise PtpUploaderException(
                JobRunningState.Ignored_NotSupported, "Wrongly categorized DVDR."
            )

    def __DownloadNfo(self, _, releaseInfo):
        url = (
            "https://cinemageddon.net/details.php?id=%s&filelist=1"
            % releaseInfo.AnnouncementId
        )
        releaseInfo.logger().info("Collecting info from torrent page '%s'.", url)

        result = MyGlobals.session.get(url)
        result.raise_for_status()
        response = result.content
        self.__CheckIfLoggedInFromResponse(response)

        self.__ParsePage(releaseInfo.logger(), releaseInfo, response)

    def __MapSourceAndFormatToPtp(
        self, releaseInfo, sourceType, formatType, raw_html: bytes
    ):
        sourceType = sourceType.lower()
        formatType = formatType.lower()

        if releaseInfo.Source:
            releaseInfo.logger().info(
                "Source '%s' is already set, not getting from the torrent page.",
                releaseInfo.Source,
            )
        elif sourceType in ["dvdrip", "dvd-r"]:
            releaseInfo.Source = "DVD"
        elif sourceType == "vhsrip":
            releaseInfo.Source = "VHS"
        elif sourceType == "tvrip":
            releaseInfo.Source = "TV"
        elif sourceType in ["webrip", "web-dl"]:
            releaseInfo.Source = "WEB"
        elif sourceType == "bdrip":  # brrips exist but aren't allowed on PTP
            releaseInfo.Source = "Blu-ray"
        else:
            raise PtpUploaderException(
                JobRunningState.Ignored_NotSupported,
                "Unsupported source type '%s'." % sourceType,
            )

        if releaseInfo.Codec:
            releaseInfo.logger().info(
                "Codec '%s' is already set, not getting from the torrent page.",
                releaseInfo.Codec,
            )
        elif formatType == "x264":
            releaseInfo.Codec = "x264"
        elif formatType == "xvid":
            releaseInfo.Codec = "XviD"
        elif formatType == "divx":
            releaseInfo.Codec = "DivX"
        elif formatType == "dvd-r":
            if releaseInfo.Size > 4700000000:
                releaseInfo.Codec = "DVD9"
            else:
                releaseInfo.Codec = "DVD5"
        else:
            raise PtpUploaderException(
                JobRunningState.Ignored_NotSupported,
                "Unsupported format type '%s'." % formatType,
            )

        # Adding BDrip support would be problematic because there is no easy way to decide if it is HD or SD.
        # Maybe we could use the resolution and file size. But what about the oversized and upscaled releases?

        if releaseInfo.ResolutionType:
            releaseInfo.logger().info(
                "Resolution type '%s' is already set, not getting from the torrent page.",
                releaseInfo.ResolutionType,
            )
        elif releaseInfo.IsDvdImage():
            if re.search(rb"Standard +: NTSC", raw_html):
                releaseInfo.ResolutionType = "NTSC"
            elif re.search(rb"Standard +: PAL", raw_html):
                releaseInfo.ResolutionType = "PAL"
            else:
                releaseInfo.logger().info("DVD detected but could not find resolution")
        elif releaseInfo.Source not in ["Blu-ray", "WEB"]:
            releaseInfo.ResolutionType = "Other"
        else:
            releaseInfo.logger().info("Could not detect resolution")

        if releaseInfo.IsDvdImage() and not releaseInfo.Container:
            if re.search(rb"\.vob</td>", raw_html, re.IGNORECASE):
                releaseInfo.Container = "VOB IFO"
            elif re.search(rb"\.iso</td>", raw_html, re.IGNORECASE):
                releaseInfo.Container = "ISO"
            else:
                releaseInfo.logger().info("DVD detected but could not find container")

    def PrepareDownload(self, _, releaseInfo):
        if releaseInfo.IsUserCreatedJob():
            self.__DownloadNfo(releaseInfo.logger(), releaseInfo)
        else:
            # TODO: add filtering support for Cinemageddon
            # In case of automatic announcement we have to check the release name if it is valid.
            # We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source.
            # if not ReleaseFilter.IsValidReleaseName( releaseInfo.ReleaseName ):
            #    logger.info( "Ignoring release '%s' because of its name." % releaseInfo.ReleaseName )
            #    return None
            self.__DownloadNfo(releaseInfo.logger(), releaseInfo)

    def ParsePageForExternalCreateJob(self, _, releaseInfo, html):
        self.__ParsePage(
            releaseInfo.logger(), releaseInfo, html, parseForExternalCreateJob=True
        )

    def DownloadTorrent(self, _, releaseInfo, path):
        url = "https://cinemageddon.net/download.php?id=%s" % releaseInfo.AnnouncementId
        releaseInfo.logger().info(
            "Downloading torrent file from '%s' to '%s'.", url, path
        )

        result = MyGlobals.session.get(url)
        result.raise_for_status()
        response = result.content
        self.__CheckIfLoggedInFromResponse(response)

        # The number of maximum simultaneous downloads is limited on Cinemageddon.
        if response.find(b"<h2>Max Torrents Reached</h2>") != -1:
            raise PtpUploaderException("Maximum torrents reached on CG.")

        with open(path, "wb") as fh:
            fh.write(response)

        ValidateTorrentFile(path)

    # Because some of the releases on CG do not contain the full name of the movie, we have to rename them because of the uploading rules on PTP.
    # The new name will be formatted like this: Movie Name Year
    def GetCustomUploadPath(self, _, releaseInfo) -> str:
        # TODO: if the user forced a release name, then let it upload by that name.
        if releaseInfo.ImdbId == "0":
            raise PtpUploaderException(
                "Uploading from CG with zero IMDb ID is not yet supported."
            )

        # If the movie already exists on PTP then the IMDb info is not populated in ReleaseInfo.
        if not releaseInfo.InternationalTitle or not releaseInfo.Year:
            imdbInfo = Imdb.GetInfo(logger, releaseInfo.ImdbId)
            # If the release name matches IMDb, preserve the name
            guess = guessit(releaseInfo.ReleaseName, {"enforce_list": True})
            if "title" in guess and imdbInfo.Title in guess["title"]:
                return releaseInfo.GetReleaseUploadPath()
            if not releaseInfo.InternationalTitle:
                releaseInfo.InternationalTitle = imdbInfo.Title
            if not releaseInfo.Year:
                releaseInfo.Year = imdbInfo.Year
            releaseInfo.save()

        if not releaseInfo.InternationalTitle:
            print(imdbInfo.Raw)
            raise PtpUploaderException("No title found, cannot rename.")

        if not releaseInfo.Year:
            print(imdbInfo.Raw)
            raise PtpUploaderException("No year found, cannot rename.")

        if len(releaseInfo.Year) <= 0:
            raise PtpUploaderException("Can't rename release because year is empty.")

        name = "{} ({}) {} {}".format(
            releaseInfo.InternationalTitle,
            releaseInfo.Year,
            releaseInfo.Source,
            releaseInfo.Codec,
        )
        name = RemoveDisallowedCharactersFromPath(name)

        releaseInfo.logger().info(
            "Upload directory will be named '%s' instead of '%s'.",
            name,
            releaseInfo.ReleaseName,
        )

        newUploadPath = releaseInfo.GetReleaseUploadPath()
        newUploadPath = os.path.dirname(newUploadPath)
        newUploadPath = os.path.join(newUploadPath, unidecode.unidecode(name))
        return newUploadPath

    def IncludeReleaseNameInReleaseDescription(self):
        return False

    def GetIdFromUrl(self, url):
        result = re.match(r".*cinemageddon\.net/details.php\?id=(\d+).*", url)
        if result is None:
            return ""
        return result.group(1)

    def GetUrlFromId(self, id):
        return "https://cinemageddon.net/details.php?id=" + id
