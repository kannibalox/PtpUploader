import os

from PtpUploader.PtpUploaderException import *
from PtpUploader.ScreenshotList import ScreenshotList
from PtpUploader.Settings import Settings
from PtpUploader.Tool.MediaInfo import MediaInfo
from PtpUploader.Tool.ScreenshotMaker import ScreenshotMaker


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
            if file.lower().endswith(".ifo"):
                mediaInfo = MediaInfo(
                    self.ReleaseInfo.Logger,
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

        ifoPathLower = ifo.Path.lower()
        if not ifoPathLower.endswith("_0.ifo"):
            raise PtpUploaderException(
                "Unsupported VIDEO_TS layout. The longest IFO is '%s' with duration '%s'."
                % (ifo.Path, ifo.DurationInSec)
            )

        # Get the next VOB.
        # (This could be a simple replace but Linux's filesystem is case-sensitive...)
        vobPath = None
        ifoPathLower = ifoPathLower.replace("_0.ifo", "_1.vob")
        for file in self.VideoFiles:
            if file.lower() == ifoPathLower:
                vobPath = file
                break

        if vobPath is None:
            raise PtpUploaderException(
                "Unsupported VIDEO_TS layout. Can't find the next VOB for IFO '%s'."
                % ifo.Path
            )

        vobMediaInfo = MediaInfo(
            self.ReleaseInfo.Logger, vobPath, self.ReleaseInfo.GetReleaseUploadPath()
        )
        self.MainMediaInfo = vobMediaInfo
        self.VideoEntries.append(
            ReleaseDescriptionVideoEntry(ifo, numberOfScreenshotsToTake=0)
        )
        self.VideoEntries.append(ReleaseDescriptionVideoEntry(vobMediaInfo))

    def __GetMediaInfoHandleNonDvdImage(self):
        self.VideoFiles = ScreenshotMaker.SortVideoFiles(self.VideoFiles)
        mediaInfos = MediaInfo.ReadAndParseMediaInfos(
            self.ReleaseInfo.Logger,
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

    def __TakeAndUploadScreenshotsForEntry(self, screenshotList, videoEntry):
        if videoEntry.NumberOfScreenshotsToTake <= 0:
            return

        screenshotMaker = ScreenshotMaker(
            self.ReleaseInfo.Logger, videoEntry.MediaInfo.Path
        )
        videoEntry.ScaleSize = screenshotMaker.GetScaleSize()

        screenshots = screenshotList.GetScreenshotsByName(videoEntry.MediaInfo.Path)
        if screenshots is None:
            screenshots = screenshotMaker.TakeAndUploadScreenshots(
                self.OutputImageDirectory,
                videoEntry.MediaInfo.DurationInSec,
                videoEntry.NumberOfScreenshotsToTake,
            )
            screenshotList.SetScreenshots(videoEntry.MediaInfo.Path, screenshots)

        videoEntry.Screenshots = screenshots

    def __TakeAndUploadScreenshots(self):
        if not self.MakeScreenshots:
            return

        screenshotList = ScreenshotList()
        screenshotList.LoadFromString(self.ReleaseInfo.Screenshots)

        for videoEntry in self.VideoEntries:
            self.__TakeAndUploadScreenshotsForEntry(screenshotList, videoEntry)

        self.ReleaseInfo.Screenshots = screenshotList.GetAsString()

    def Format(self, includeReleaseName):
        self.ReleaseInfo.Logger.info("Making release description")
        releaseDescription = ""

        if includeReleaseName:
            releaseDescription = (
                "[size=4][b]%s[/b][/size]\n\n" % self.ReleaseInfo.ReleaseName
            )

        for i in range(len(self.VideoEntries)):
            entry = self.VideoEntries[i]

            if i > 0:
                releaseDescription += "\n\n"

            releaseDescription += entry.ToReleaseDescription()

        if len(self.ReleaseInfo.ReleaseNotes) > 0:
            releaseDescription += "\n\n%s" % self.ReleaseInfo.ReleaseNotes

        return releaseDescription

    def GetMainMediaInfo(self):
        return self.MainMediaInfo
