import html
import logging
import os
import re
import xml.etree.ElementTree as ET

from urllib.parse import urlparse

import requests

from PtpUploader.IncludedFileList import IncludedFileList
from PtpUploader.NfoParser import NfoParser
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.ReleaseExtractor import ReleaseExtractor
from PtpUploader.Settings import Settings
from PtpUploader.Source.SourceBase import SourceBase


logger = logging.getLogger(__name__)


class Prowlarr(SourceBase):
    def __init__(self):
        super().__init__()
        self.MaximumParallelDownloads = 1
        self.Name = "prowlarr"
        self.NameInSettings = "Prowlarr"

    def LoadSettings(self, _):
        super().LoadSettings(_)
        self.ApiKey = self.settings.api_key
        self.Url = self.settings.url
        self.loaded_indexers = {}

    def Login(self):
        logger.info("Logging into %s", self.Name)
        self.session = requests.Session()
        self.session.headers.update({"X-Api-Key": self.ApiKey})
        r = self.session.get(self.Url + "/api/v1/indexer").json()
        for t in r:
            self.loaded_indexers[t["name"]] = t
        logger.info(
            "Loaded indexers from prowlarr: %s", list(self.loaded_indexers.keys())
        )

    def PrepareDownload(self, _, releaseInfo):
        logger.info("Processing '%s' with prowlarr", releaseInfo.AnnouncementId)
        if not releaseInfo.ImdbId:
            return
        match = self.match_imdb(releaseInfo)
        if match is None:
            logger.warning("Could not find release info in prowlarr")
            return
        for field in match:
            if field.tag == "title" and not releaseInfo.ReleaseName:
                releaseInfo.ReleaseName = field.text
            if field.tag == "size" and not releaseInfo.Size:
                releaseInfo.Size = field.text

    def match_imdb(self, releaseInfo):
        indexer = self.get_indexer(releaseInfo)
        response = self.session.get(
            f"{self.Url}/api/v1/indexer/{indexer['id']}/newznab",
            params={"t": "movie", "imdbid": 'tt' + str(releaseInfo.ImdbId)},
        )
        for i in ET.fromstring(response.text)[0].findall("item"):
            for field in i:
                if (
                    field.tag in ["guid", "comments"]
                    and field.text == releaseInfo.AnnouncementId
                ):
                    return i
        return None

    def get_indexer(self, release):
        o = urlparse(release.AnnouncementId)
        for t in self.loaded_indexers.values():
            for u in t["indexerUrls"]:
                iu = urlparse(u)
                if iu.netloc == o.netloc:
                    return t
        return None

    def DownloadTorrent(self, _, releaseInfo, path):
        match = self.match_imdb(releaseInfo)
        link = None
        for field in match:
            if field.tag == "link":
                link = field.text
                break
        if link is None:
            raise PtpUploaderException("No download link found in prowlarr")
        with open(path, "wb") as fh:
            fh.write(self.session.get(html.unescape(link)).content)

    # fileList must be an instance of IncludedFileList.
    def CheckFileList(self, releaseInfo, fileList):
        logger.info("Checking the contents of the release.")

        if releaseInfo.IsDvdImage():
            return

        # Check if the release contains multiple non-ignored videos.
        numberOfVideoFiles = 0
        for file in fileList.Files:
            if file.IsIncluded() and Settings.HasValidVideoExtensionToUpload(file.Name):
                numberOfVideoFiles += 1

        if numberOfVideoFiles > 1:
            raise PtpUploaderException("Release contains multiple video files.")

    # fileList must be an instance of IncludedFileList.
    def DetectSceneReleaseFromFileList(self, releaseInfo, fileList):
        rarRe = re.compile(r".+\.(?:rar|r\d+)$", re.IGNORECASE)
        rarCount = 0

        for file in fileList.Files:
            if rarRe.match(file.Name) is None:
                continue

            # If there are multiple RAR files then it's likely a scene release.
            rarCount += 1
            if rarCount > 1:
                releaseInfo.SetSceneRelease()
                break

    # Must returns with a tuple consisting of the list of video files and the list of additional files.
    def ValidateExtractedRelease(self, releaseInfo, includedFileList):
        videoFiles, additionalFiles = ReleaseExtractor.ValidateDirectory(
            logger, releaseInfo.GetReleaseUploadPath(), includedFileList
        )
        if len(videoFiles) < 1:
            raise PtpUploaderException(
                "Upload path '%s' doesn't contain any video files."
                % releaseInfo.GetReleaseUploadPath()
            )

        return videoFiles, additionalFiles

    def GetIncludedFileList(self, releaseInfo):
        includedFileList = IncludedFileList()

        if os.path.isfile(releaseInfo.SourceTorrentFilePath):
            includedFileList.FromTorrent(releaseInfo.SourceTorrentFilePath)

        return includedFileList

    def GetTemporaryFolderForImagesAndTorrent(self, releaseInfo):
        return releaseInfo.GetReleaseRootPath()

    def IsSingleFileTorrentNeedsDirectory(self, releaseInfo) -> bool:
        return True

    def IncludeReleaseNameInReleaseDescription(self):
        return True

    def GetIdFromUrl(self, url: str) -> str:
        o = urlparse(url)
        for t in self.loaded_indexers.values():
            for u in t["indexerUrls"]:
                iu = urlparse(u)
                if iu.netloc == o.netloc:
                    return url
        return ""

    # Unique situation, the ID is a full URL, since that's what prowlarr's
    # newznab API uses as a guid
    def GetUrlFromId(self, id: str) -> str:
        return id
