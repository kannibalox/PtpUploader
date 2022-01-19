import subprocess
from pathlib import Path

from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import Settings
from PtpUploader.Tool.MediaInfo import MediaInfo


class Ffmpeg:
    def __init__(self, logger, inputVideoPath):
        self.Logger = logger
        self.InputVideoPath = inputVideoPath
        self.ScaleSize = None

        self.__CalculateSizeAccordingToAspectRatio()

    def __CalculateSizeAccordingToAspectRatio(self):
        # Some DVDs are badly made, so the DAR needs to be determined from the IFO
        # rather than the VOB.
        ifoPath = self.InputVideoPath[:-5] + "0.IFO"
        if Path(ifoPath).exists():
            m = MediaInfo(self.Logger, ifoPath, "")
        else:
            m = MediaInfo(self.Logger, self.InputVideoPath, "")

        width = m.Width
        height = m.Height
        darX = int(m.DAR.split(":")[0].strip())
        darY = int(m.DAR.split(":")[1].strip())

        # We ignore invalid resolutions, invalid aspect ratios and aspect ratio 1:1.
        if any(i <= 0 for i in (width, height, darX, darY)) or (
            darX == 1 and darY == 1
        ):
            return

        # Choose whether we resize height or width.
        if (float(darX) / darY) >= (float(width) / height):
            # Resize width
            newWidth = (height * darX) / darY
            newWidth = int(newWidth)
            if abs(newWidth - width) <= 1:
                return

            # For FFmpeg frame size must be a multiple of 2.
            if (newWidth % 2) != 0:
                newWidth += 1

            self.ScaleSize = "%sx%s" % (newWidth, height)
        else:
            # Resize height
            newHeight = (width * darY) / darX
            newHeight = int(newHeight)
            if abs(newHeight - height) <= 1:
                return

            # For FFmpeg frame size must be a multiple of 2.
            if (newHeight % 2) != 0:
                newHeight += 1

            self.ScaleSize = "%sx%s" % (width, newHeight)

    def MakeScreenshotInPng(self, timeInSeconds, outputPngPath):
        self.Logger.info(
            "Making screenshot with ffmpeg from '%s' to '%s'."
            % (self.InputVideoPath, outputPngPath)
        )

        # -an: disable audio
        # -sn: disable subtitle
        # There is no way to set PNG compression level. :(
        time = str(int(timeInSeconds))
        args = [
            Settings.FfmpegPath,
            "-an",
            "-sn",
            "-ss",
            time,
            "-i",
            self.InputVideoPath,
            "-vcodec",
            "png",
            "-vframes",
            "1",
            "-y",
        ]
        if self.ScaleSize:
            self.Logger.info(
                "Pixel aspect ratio isn't 1:1, scaling video to resolution: '%s'."
                % self.ScaleSize
            )
            args.append(
                [
                    "-s",
                    self.ScaleSize,
                ]
            )
        args.append([outputPngPath])

        errorCode = subprocess.call(args)
        if errorCode != 0:
            raise PtpUploaderException(
                "Process execution '%s' returned with error code '%s'."
                % (args, errorCode)
            )
