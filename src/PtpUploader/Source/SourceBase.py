import logging
import os
import re
import shutil
from pathlib import Path

from PtpUploader.IncludedFileList import IncludedFileList
from PtpUploader.Job.FinishedJobPhase import FinishedJobPhase
from PtpUploader.NfoParser import NfoParser
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.ReleaseExtractor import ReleaseExtractor
from PtpUploader.Settings import Settings


logger = logging.getLogger(__name__)


class SourceBase:
    def __init__(self):
        self.MaximumParallelDownloads = 1
        self.Name = None
        self.NameInSettings = None

    def LoadSettings(self, settings):
        self.Username = settings.GetDefault(self.NameInSettings, "Username", "")
        self.Password = settings.GetDefault(self.NameInSettings, "Password", "")
        self.AutomaticJobFilter = settings.GetDefault(
            self.NameInSettings, "AutomaticJobFilter", ""
        )

        # Do not allow bogus settings.
        maximumParallelDownloads = int(
            settings.GetDefault(self.NameInSettings, "MaximumParallelDownloads", "1")
        )
        if maximumParallelDownloads > 0:
            self.MaximumParallelDownloads = maximumParallelDownloads

        self.AutomaticJobStartDelay = int(
            settings.GetDefault(self.NameInSettings, "AutomaticJobStartDelay", "0")
        )
        self.AutomaticJobCooperationMemberCount = int(
            settings.GetDefault(
                self.NameInSettings, "AutomaticJobCooperationMemberCount", "0"
            )
        )
        self.AutomaticJobCooperationMemberId = int(
            settings.GetDefault(
                self.NameInSettings, "AutomaticJobCooperationMemberId", "0"
            )
        )
        self.AutomaticJobCooperationDelay = int(
            settings.GetDefault(
                self.NameInSettings, "AutomaticJobCooperationDelay", "0"
            )
        )

        self.StopAutomaticJob = settings.GetDefault(
            self.NameInSettings, "StopAutomaticJob", ""
        ).lower()
        self.StopAutomaticJobIfThereAreMultipleVideos = settings.GetDefault(
            self.NameInSettings, "StopAutomaticJobIfThereAreMultipleVideos", ""
        ).lower()

    def IsEnabled(self) -> bool:
        return True

    def Login(self):
        pass

    def PrepareDownload(self, _, releaseInfo):
        pass

    def ParsePageForExternalCreateJob(self, _, releaseInfo, html):
        pass

    def CheckSynopsis(self, _, releaseInfo):
        # If it exists on PTP then we don't need a synopsis.
        if (not releaseInfo.Synopsis) and (not releaseInfo.PtpId):
            raise PtpUploaderException("Synopsis is not set.")

    def CheckCoverArt(self, _, releaseInfo):
        # If it exists on PTP then we don't need a cover.
        if (not releaseInfo.CoverArtUrl) and (not releaseInfo.PtpId):
            raise PtpUploaderException("Cover art is not set.")

    def DownloadTorrent(self, _, releaseInfo, path):
        pass

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

    def IsDownloadFinished(self, _, releaseInfo):
        return Settings.GetTorrentClient().IsTorrentFinished(
            logger, releaseInfo.SourceTorrentInfoHash
        )

    def GetCustomUploadPath(self, _, releaseInfo):
        return ""

    def CreateUploadDirectory(self, releaseInfo):
        uploadDirectory = releaseInfo.GetReleaseUploadPath()
        logger.info("Creating upload directory at '%s'." % uploadDirectory)

        if os.path.exists(uploadDirectory):
            raise PtpUploaderException(
                "Upload directory '%s' already exists." % uploadDirectory
            )

        os.makedirs(uploadDirectory)

    def ExtractRelease(self, _, releaseInfo, includedFileList):
        ReleaseExtractor.Extract(
            logger,
            releaseInfo.GetReleaseDownloadPath(),
            releaseInfo.GetReleaseUploadPath(),
            includedFileList,
        )

    def ReadNfo(self, releaseInfo):
        releaseInfo.Nfo = NfoParser.FindAndReadNfoFileToUnicode(
            releaseInfo.GetReleaseDownloadPath()
        )

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

    @staticmethod
    def __DeleteDirectoryIfEmpyOrContainsOnlyEmptyDirectories(path):
        if not os.path.isdir(path):
            return

        for (dirPath, dirNames, fileNames) in os.walk(path):
            for file in fileNames:
                return

        shutil.rmtree(path)

    def Delete(self, releaseInfo, torrentClient, deleteSourceData, deleteUploadData):
        # Only delete if the release directory has been created by this job.
        # (This is needed because of the releases with the same name. This way deleting the second one won't delete the release directory of the first.)
        if not releaseInfo.IsJobPhaseFinished(
            FinishedJobPhase.Download_CreateReleaseDirectory
        ):
            return

        if deleteSourceData:
            # Delete the source torrent file.
            if releaseInfo.SourceTorrentFilePath and os.path.isfile(
                releaseInfo.SourceTorrentFilePath
            ):
                os.remove(releaseInfo.SourceTorrentFilePath)

            # Delete the source torrent from the torrent client.
            if len(releaseInfo.SourceTorrentInfoHash) > 0:
                torrentClient.DeleteTorrent(logger, releaseInfo.SourceTorrentInfoHash)

            # Delete the data of the source torrent.
            if os.path.isdir(releaseInfo.GetReleaseDownloadPath()):
                shutil.rmtree(releaseInfo.GetReleaseDownloadPath())

        if deleteUploadData:
            # Delete the uploaded torrent file.
            if releaseInfo.UploadTorrentFilePath and os.path.isfile(
                releaseInfo.UploadTorrentFilePath
            ):
                os.remove(releaseInfo.UploadTorrentFilePath)

            # Delete the uploaded torrent from the torrent client.
            if len(releaseInfo.UploadTorrentInfoHash) > 0:
                torrentClient.DeleteTorrent(logger, releaseInfo.UploadTorrentInfoHash)

            # Delete the data of the uploaded torrent.
            if os.path.isdir(releaseInfo.GetReleaseUploadPath()):
                shutil.rmtree(releaseInfo.GetReleaseUploadPath())

        if deleteSourceData and deleteUploadData:
            SourceBase.__DeleteDirectoryIfEmpyOrContainsOnlyEmptyDirectories(
                releaseInfo.GetReleaseRootPath()
            )

        log = Path(Settings.GetJobLogPath(), str(releaseInfo.Id))
        if log.is_file():
            log.unlink()

    def GetTemporaryFolderForImagesAndTorrent(self, releaseInfo):
        return releaseInfo.GetReleaseRootPath()

    def IsSingleFileTorrentNeedsDirectory(self, _) -> bool:
        return True

    def IncludeReleaseNameInReleaseDescription(self):
        return True

    def GetIdFromUrl(self, url: str) -> str:
        return ""

    def GetUrlFromId(self, id: str) -> str:
        return ""

    def GetIdFromAutodlIrssiUrl(self, url: str) -> str:
        return ""
