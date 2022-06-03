import os
import re
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
        # Get resolution and pixel aspect ratio from FFmpeg.
        args = [Settings.FfmpegPath, "-i", self.InputVideoPath]
        proc: subprocess.CompletedProcess = subprocess.run(args, capture_output=True)
        result: str = proc.stderr.decode("utf-8", "ignore")

        # Formatting can be one of the following. PAR can be SAR too.
        # Stream #0.0(eng): Video: h264, yuv420p, 1280x544, PAR 1:1 DAR 40:17, 24 tbr, 1k tbn, 48 tbc
        # Stream #0.0[0x1e0]: Video: mpeg2video, yuv420p, 720x480 [PAR 8:9 DAR 4:3], 7500 kb/s, 29.97 tbr, 90k tbn, 59.94 tbc
        match = re.search(r"(\d+)x(\d+), [SP]AR \d+:\d+ DAR (\d+):(\d+)", result)
        if match is None:
            match = re.search(r"(\d+)x(\d+) \[[SP]AR \d+:\d+ DAR (\d+):(\d+)", result)
        if match is None:
            return

        width: int = int(match.group(1))
        height: int = int(match.group(2))
        darX: int = int(match.group(3))
        darY: int = int(match.group(4))
        # We ignore invalid resolutions, invalid aspect ratios and aspect ratio 1:1.
        if (
            width <= 0
            or height <= 0
            or darX <= 0
            or darY <= 0
            or (darX == 1 and darY == 1)
        ):
            return

        # If we are a DVD, sometimes the DAR can get messed up between the VOB and IFO
        # We'll use the mediainfo to draw our conclusions from instead
        ifoPath = Path(self.InputVideoPath[:-5] + "0.IFO")
        if ifoPath.exists():
            self.Logger.debug("Fetching DAR information from '%s'", ifoPath)
            m = MediaInfo(self.Logger, ifoPath, "")
            try:
                darX = float(m.DAR)
                darY = 1
            except ValueError:
                try:
                    darX = int(m.DAR.split(":")[0].strip())
                    darY = int(m.DAR.split(":")[1].strip())
                except (ValueError, IndexError):
                    pass

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

            self.ScaleSize = f"{newWidth}x{height}"
        else:
            # Resize height
            newHeight = (width * darY) / darX
            newHeight = int(newHeight)
            if abs(newHeight - height) <= 1:
                return

            # For FFmpeg frame size must be a multiple of 2.
            if (newHeight % 2) != 0:
                newHeight += 1

            self.ScaleSize = f"{width}x{newHeight}"

    def MakeScreenshotInPng(self, timeInSeconds, outputPngPath):
        self.Logger.info(
            "Making screenshot with ffmpeg from '%s' to '%s'."
            % (self.InputVideoPath, outputPngPath)
        )

        # -an: disable audio
        # -sn: disable subtitle
        # There is no way to set PNG compression level. :(
        args = []
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
            "-pix_fmt",
            "rbg24",
            "-y",
            outputPngPath,
        ]
        if self.ScaleSize is not None:
            self.Logger.info(
                "Pixel aspect ratio wasn't 1:1, scaling video to resolution: '%s'."
                % self.ScaleSize
            )
            args += [
                "-s",
                self.ScaleSize,
            ]
        args += ["-y", outputPngPath]
        errorCode = subprocess.call(args)
        if errorCode != 0:
            raise PtpUploaderException(
                "Process execution '%s' returned with error code '%s'."
                % (args, errorCode)
            )
