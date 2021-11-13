import functools
import os
import shutil

from PtpUploader.ImageHost.ImageUploader import ImageUploader
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import Settings
from PtpUploader.Tool.Ffmpeg import Ffmpeg
from PtpUploader.Tool.ImageMagick import ImageMagick
from PtpUploader.Tool.Mplayer import Mplayer
from PtpUploader.Tool.Mpv import Mpv


class ScreenshotMaker:
    def __init__(self, logger, inputVideoPath):
        self.Logger = logger

        self.InternalScreenshotMaker = None

        # TODO: Why is this conditional being done up here just to repeat it further down?
        if shutil.which(Settings.MpvPath):
            self.InternalScreenshotMaker = Mpv(logger, inputVideoPath)
        elif shutil.which(Settings.MplayerPath):
            self.InternalScreenshotMaker = Mplayer(logger, inputVideoPath)
        elif shutil.which(Settings.FfmpegPath):
            self.InternalScreenshotMaker = Ffmpeg(logger, inputVideoPath)
        if self.InternalScreenshotMaker is None:
            raise PtpUploaderException("No screenshot tool found")

    def GetScaleSize(self):
        return self.InternalScreenshotMaker.ScaleSize

    def __MakeUsingMplayer(self, timeInSeconds, outputImageDirectory):
        return self.InternalScreenshotMaker.MakeScreenshotInPng(
            timeInSeconds, outputImageDirectory
        )

    def __MakeUsingMpv(self, timeInSeconds, outputImageDirectory):
        outputPngPath = os.path.join(outputImageDirectory, "00000001.png")
        self.InternalScreenshotMaker.MakeScreenshotInPng(timeInSeconds, outputPngPath)
        return outputPngPath

    def __MakeUsingFfmpeg(self, timeInSeconds, outputImageDirectory):
        outputPngPath = os.path.join(outputImageDirectory, "00000001.png")
        self.InternalScreenshotMaker.MakeScreenshotInPng(timeInSeconds, outputPngPath)
        return outputPngPath

    # Returns with the URL of the uploaded image.
    def __TakeAndUploadScreenshot(self, timeInSeconds, outputImageDirectory):
        screenshotPath = None

        try:
            if shutil.which(Settings.MpvPath):
                screenshotPath = self.__MakeUsingMpv(
                    timeInSeconds, outputImageDirectory
                )
            elif shutil.which(Settings.MplayerPath):
                screenshotPath = self.__MakeUsingMplayer(
                    timeInSeconds, outputImageDirectory
                )
            elif shutil.which(Settings.FfmpegPath):
                screenshotPath = self.__MakeUsingFfmpeg(
                    timeInSeconds, outputImageDirectory
                )

            if Settings.ImageMagickConvertPath and shutil.which(
                Settings.ImageMagickConvertPath
            ):
                ImageMagick.OptimizePng(self.Logger, screenshotPath)

            imageUrl = ImageUploader.Upload(self.Logger, imagePath=screenshotPath)
        finally:
            try:
                if screenshotPath is not None:
                    os.remove(screenshotPath)
            except FileNotFoundError:
                pass

        return imageUrl

    # Takes maximum five screenshots from the first 30% of the video.
    # Returns with the URLs of the uploaded images.
    def TakeAndUploadScreenshots(
        self, outputImageDirectory, durationInSec, numberOfScreenshotsToTake
    ):
        urls = []

        if numberOfScreenshotsToTake > 5:
            numberOfScreenshotsToTake = 5

        for i in range(numberOfScreenshotsToTake):
            position = 0.10 + (i * 0.05)
            urls.append(
                self.__TakeAndUploadScreenshot(
                    int(durationInSec * position), outputImageDirectory
                )
            )

        return urls

    # We sort video files by their size (less than 50 MB difference is ignored) and by their name.
    # Sorting by name is needed to ensure that the screenshot is taken from the first video to avoid spoilers when a release contains multiple videos.
    # Sorting by size is needed to ensure that we don't take the screenshots from the sample or extras included.
    # Ignoring less than 50 MB differnece is needed to make sure that CD1 will be sorted before CD2 even if CD2 is larger than CD1 by 49 MB.
    @staticmethod
    def SortVideoFiles(files):
        class SortItem:
            def __init__(self, path):
                self.Path = path
                self.LowerPath = str(path).lower()
                self.Size = os.path.getsize(path)

            @staticmethod
            def Compare(item1, item2):
                ignoreSizeDifference = 50 * 1024 * 1024
                sizeDifference = item1.Size - item2.Size
                if abs(sizeDifference) > ignoreSizeDifference:
                    if item1.Size > item2.Size:
                        return -1
                    else:
                        return 1

                if item1.LowerPath < item2.LowerPath:
                    return -1
                elif item1.LowerPath > item2.LowerPath:
                    return 1
                else:
                    return 0

        filesToSort = []
        for file in files:
            item = SortItem(file)
            filesToSort.append(item)

        filesToSort.sort(key=functools.cmp_to_key(SortItem.Compare))

        files = []
        for item in filesToSort:
            files.append(item.Path)

        return files
