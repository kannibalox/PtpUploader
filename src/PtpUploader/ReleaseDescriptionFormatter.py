import logging

from pathlib import Path

from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import config
from PtpUploader.Tool import BdInfo
from PtpUploader.Tool.MediaInfo import MediaInfo, MediaInfoException
from PtpUploader.Tool.ScreenshotMaker import ScreenshotMaker


logger = logging.getLogger(__name__)


class ReleaseDescriptionVideoEntry:
    def __init__(self, info, numberOfScreenshotsToTake=None, bdinfo=None):
        if numberOfScreenshotsToTake is None:
            numberOfScreenshotsToTake = config.uploader.max_screenshots
        self.MediaInfo = info
        self.BdInfo = bdinfo
        self.NumberOfScreenshotsToTake = numberOfScreenshotsToTake
        self.Screenshots = []
        self.ScaleSize = None

    def HaveScreenshots(self):
        return len(self.Screenshots) > 0

    def ToReleaseDescription(self):
        releaseDescription = ""
        if self.BdInfo:
            releaseDescription += self.BdInfo
        else:
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
            file = Path(file)
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

        vobMediaInfo = None
        for vob in sorted(ifo.Path.parent.glob(str(ifo.Path.name[:-5]) + "*.VOB")):
            # Get the next VOB and try to parse its mediainfo
            if str(vob).endswith("0.VOB"):
                continue
            try:
                vobMediaInfo = MediaInfo(
                    logger, vob, self.ReleaseInfo.GetReleaseUploadPath()
                )
                break
            except MediaInfoException:
                pass

        if vobMediaInfo is None:
            raise PtpUploaderException(
                "Unsupported VIDEO_TS layout. Can't find the next VOB for IFO '%s'."
                % ifo.Path
            )
        self.MainMediaInfo = vobMediaInfo
        self.VideoEntries.append(
            ReleaseDescriptionVideoEntry(ifo, numberOfScreenshotsToTake=0)
        )
        self.VideoEntries.append(ReleaseDescriptionVideoEntry(vobMediaInfo))

    def __GetMediaInfoHandleBlurayImage(self):
        # Get all m2ts streams
        m2ts = []
        for file in self.VideoFiles:
            file = Path(file)
            if file.suffix == ".m2ts":
                try:
                    mediaInfo = MediaInfo(
                        logger,
                        file,
                        self.ReleaseInfo.GetReleaseUploadPath(),
                    )
                    m2ts.append(mediaInfo)
                except MediaInfoException:
                    # Discard any non-movie mediainfos
                    pass

        # Use the largest by real size. Mediainfo gets funky with duration/size for
        # m2ts files.
        m2ts = sorted(m2ts, key=lambda x: x.RealFileSize, reverse=True)[0]
        self.MainMediaInfo = m2ts
        path = self.ReleaseInfo.GetReleaseUploadPath()
        if path not in self.ReleaseInfo.BdInfo:
            self.ReleaseInfo.BdInfo[path] = BdInfo.run(path)

        self.VideoEntries.append(
            ReleaseDescriptionVideoEntry(
                m2ts,
                config.uploader.max_screenshots,
                bdinfo=self.ReleaseInfo.BdInfo[path],
            )
        )

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
        numberOfScreenshotsToTake = config.uploader.max_screenshots
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
        elif self.ReleaseInfo.IsBlurayImage():
            self.__GetMediaInfoHandleBlurayImage()
        else:
            self.__GetMediaInfoHandleNonDvdImage()

    def __TakeAndUploadScreenshots(self):
        if not self.MakeScreenshots:
            return

        # Mediainfo will never return the right duration without more
        # magic than it's worth implementing, we'll just use BDInfo
        if self.ReleaseInfo.IsBlurayImage():
            for videoEntry in self.VideoEntries:
                path = str(videoEntry.MediaInfo.Path)
                _, duration = BdInfo.get_longest_playlist(
                    self.ReleaseInfo.GetReleaseUploadPath()
                )
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
                        duration,
                        videoEntry.NumberOfScreenshotsToTake,
                    )
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
                # self.ReleaseInfo.save() # TODO: Rework ReleaseInfoMaker to allow this
            videoEntry.Screenshots = self.ReleaseInfo.Screenshots[path]

    def Format(self, includeReleaseName):
        logger.info("Making release description")
        releaseDescription = ""

        if includeReleaseName:
            releaseDescription = (
                "[size=4][b]%s[/b][/size]\n\n" % self.ReleaseInfo.ReleaseName
            )

        if len(self.ReleaseInfo.ReleaseNotes) > 0:
            releaseDescription += "%s\n\n" % self.ReleaseInfo.ReleaseNotes

        for i, entry in enumerate(self.VideoEntries):
            if i > 0:
                releaseDescription += "\n\n"

            releaseDescription += entry.ToReleaseDescription()

        return releaseDescription

    def GetMainMediaInfo(self):
        return self.MainMediaInfo
