import logging
import os

from pathlib import Path

from PtpUploader.PtpUploaderException import *
from PtpUploader.Settings import Settings
from PtpUploader.Tool.MediaInfo import MediaInfo
from PtpUploader.Tool.ScreenshotMaker import ScreenshotMaker


logger = logging.getLogger(__name__)


class ReleaseDescriptionVideoEntry:
    def __init__(self, mediaInfo, numberOfScreenshotsToTake=5):
        self.MediaInfo = mediaInfo
        self.NumberOfScreenshotsToTake = numberOfScreenshotsToTake
        self.Screenshots = []
        self.ScaleSize = None

    def HaveScreenshots(self):
        return len(self.Screenshots) > 0

    def ToReleaseDescription(self):
        releaseDescription = ""
        releaseDescription += self.MediaInfo.FormattedMediaInfo

        if self.HaveScreenshots():
            for screenshot in self.Screenshots:
                releaseDescription += "\n\n[img=%s]" % screenshot

        return releaseDescription


class ReleaseDescriptionFormatter:
    def __init__(
        self,
        releaseInfo,
        videoFiles,
        additionalFiles,
        outputImageDirectory,
        makeScreenshots=True,
    ):
        self.ReleaseInfo = releaseInfo
        self.VideoFiles = videoFiles
        self.AdditionalFiles = additionalFiles
        self.OutputImageDirectory = outputImageDirectory
        self.MakeScreenshots = makeScreenshots
        self.VideoEntries = []
        self.MainMediaInfo = None

        self.__GetMediaInfo()
        self.__TakeAndUploadScreenshots()

    def __GetMediaInfoHandleDvdImage(self):
        # Get all IFOs.
        ifos = []
        for file in self.AdditionalFiles:
            if file.suffix == ".IFO":
                mediaInfo = MediaInfo(
                    logger,
                    file,
                    self.ReleaseInfo.GetReleaseUploadPath(),
                )
                ifos.append(mediaInfo)

        # Use the longest by duration.
        ifo = sorted(ifos, key=lambda x: x.DurationInSec, reverse=True)[0]
        if ifo.DurationInSec <= 0:
            raise PtpUploaderException(
                "None of the IFOs have duration. MediaInfo is probably too old."
            )

        if not ifo.Path.name.endswith("_0.IFO"):
            raise PtpUploaderException(
                "Unsupported VIDEO_TS layout. The longest IFO is '%s' with duration '%s'."
                % (ifo.Path, ifo.DurationInSec)
            )

        # Get the next VOB.
        vobPath = Path(str(ifo.Path).replace("_0.IFO", "_1.VOB"))
        if not vobPath.is_file():
            raise PtpUploaderException(
                "Unsupported VIDEO_TS layout. Can't find the next VOB for IFO '%s'."
                % ifo.Path
            )

        vobMediaInfo = MediaInfo(
            logger, vobPath, self.ReleaseInfo.GetReleaseUploadPath()
        )
        self.MainMediaInfo = vobMediaInfo
        self.VideoEntries.append(
            ReleaseDescriptionVideoEntry(ifo, numberOfScreenshotsToTake=0)
        )
        self.VideoEntries.append(ReleaseDescriptionVideoEntry(vobMediaInfo))

    def __GetMediaInfoHandleNonDvdImage(self):
        self.VideoFiles = ScreenshotMaker.SortVideoFiles(self.VideoFiles)
        mediaInfos = MediaInfo.ReadAndParseMediaInfos(
            logger,
            self.VideoFiles,
            self.ReleaseInfo.GetReleaseUploadPath(),
        )
        self.MainMediaInfo = mediaInfos[0]

        # Make less screenshots if there are more than one videos.
        mediaInfoCount = len(mediaInfos)
        numberOfScreenshotsToTake = 5
        if mediaInfoCount == 2:
            numberOfScreenshotsToTake = 3
        elif mediaInfoCount > 2:
            numberOfScreenshotsToTake = 2

        for i in range(mediaInfoCount):
            self.VideoEntries.append(
                ReleaseDescriptionVideoEntry(mediaInfos[i], numberOfScreenshotsToTake)
            )

    def __GetMediaInfo(self):
        if self.ReleaseInfo.IsDvdImage():
            self.__GetMediaInfoHandleDvdImage()
        else:
            self.__GetMediaInfoHandleNonDvdImage()

    def __TakeAndUploadScreenshots(self):
        if not self.MakeScreenshots:
            return

        for videoEntry in self.VideoEntries:
            path = str(
                videoEntry.MediaInfo.Path
            )  # Need to make sure any Path objects can be used as keys
            if videoEntry.NumberOfScreenshotsToTake <= 0:
                continue

            screenshotMaker = ScreenshotMaker(logger, path)
            videoEntry.ScaleSize = screenshotMaker.GetScaleSize()

            if (
                path not in self.ReleaseInfo.Screenshots
                or not self.ReleaseInfo.Screenshots[path]
            ):
                self.ReleaseInfo.Screenshots[
                    path
                ] = screenshotMaker.TakeAndUploadScreenshots(
                    self.OutputImageDirectory,
                    videoEntry.MediaInfo.DurationInSec,
                    videoEntry.NumberOfScreenshotsToTake,
                )
                self.ReleaseInfo.save()
            videoEntry.Screenshots = self.ReleaseInfo.Screenshots[path]

    def Format(self, includeReleaseName):
        logger.info("Making release description")
        releaseDescription = ""

        if includeReleaseName:
            releaseDescription = (
                "[size=4][b]%s[/b][/size]\n\n" % self.ReleaseInfo.ReleaseName
            )

        for i, entry in enumerate(self.VideoEntries):
            if i > 0:
                releaseDescription += "\n\n"

            releaseDescription += entry.ToReleaseDescription()

        if len(self.ReleaseInfo.ReleaseNotes) > 0:
            releaseDescription += "\n\n%s" % self.ReleaseInfo.ReleaseNotes

        return releaseDescription

    def GetMainMediaInfo(self):
        return self.MainMediaInfo
