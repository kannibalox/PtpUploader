import os
import re
import subprocess

from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import Settings


class Mplayer:
    NoAutoSubParameterSupported = None

    def __init__(self, logger, inputVideoPath):
        Mplayer.DetectNoAutoSubParameterSupport()

        self.Logger = logger
        self.InputVideoPath = inputVideoPath
        self.ScaleSize = None

        self.__CalculateSizeAccordingToAspectRatio()

    # The noautosub parameter is not present in all version of MPlayer, and it returns with error code if it is specified.
    @staticmethod
    def DetectNoAutoSubParameterSupport():
        if Mplayer.NoAutoSubParameterSupported is not None:
            return

        args = [Settings.MplayerPath, "-noautosub"]
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        errorCode = proc.wait()
        Mplayer.NoAutoSubParameterSupported = errorCode == 0

    # We could get this info when making the first screenshot, but ScaleSize is not stored in the database and screenshots are not made again when resuming a job.
    def __CalculateSizeAccordingToAspectRatio(self):
        args = [
            Settings.MplayerPath,
            "-identify",
            "-vo",
            "null",
            "-frames",
            "1",
            "-nosound",
            "-nosub",
            "-nolirc",
        ]
        if Mplayer.NoAutoSubParameterSupported:
            args.append("-noautosub")
        args.append(self.InputVideoPath)

        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        errorCode = proc.wait()
        if errorCode != 0:
            raise PtpUploaderException(
                "Process execution '%s' returned with error code '%s'."
                % (args, errorCode)
            )

        result = stdout.decode("utf-8", "ignore")

        # VO: [null] 1280x720 => 1280x720 RGB 24-bit
        match = re.search(r"VO: \[null\] (\d+)x(\d+) => (\d+)x(\d+).+", result)
        if match is None:
            raise PtpUploaderException("Can't read video size from MPlayer's output.")

        width = int(match.group(1))
        height = int(match.group(2))
        outputWidth = int(match.group(3))
        outputHeight = int(match.group(4))
        if width <= 0 or height <= 0 or outputWidth <= 0 or outputHeight <= 0:
            raise PtpUploaderException("Can't read video size from MPlayer's output.")

        if outputWidth != width or outputHeight != height:
            self.ScaleSize = "%sx%s" % (outputWidth, outputHeight)

    def MakeScreenshotInPng(self, timeInSeconds, outputDirectory):
        self.Logger.info(
            "Making screenshot with MPlayer from '%s' to '%s'."
            % (self.InputVideoPath, outputDirectory)
        )

        outputPngPath = os.path.join(outputDirectory, "00000001.png")
        if os.path.exists(outputPngPath):
            raise PtpUploaderException(
                "Can't create screenshot because file '%s' already exists."
                % outputPngPath
            )

        # mplayer -ss 101 -vo png:z=9:outdir="/home/tnsuser/temp/a b/" -frames 1 -vf scale=0:0 -nosound -nosub -noautosub -nolirc a.vob
        # outdir is not working with the Windows version of MPlayer, so for the sake of easier testing we set the output directory with by setting the current working directory.
        # -vf scale=0:0 -- use display aspect ratio
        time = str(int(timeInSeconds))
        args = [
            Settings.MplayerPath,
            "-ss",
            time,
            "-vo",
            "png:z=9",
            "-frames",
            "1",
            "-vf",
            "scale=0:0",
            "-nosound",
            "-nosub",
            "-nolirc",
        ]
        if Mplayer.NoAutoSubParameterSupported:
            args.append("-noautosub")
        args.append(self.InputVideoPath)

        errorCode = subprocess.call(args, cwd=outputDirectory)
        if errorCode != 0:
            raise PtpUploaderException(
                "Process execution '%s' returned with error code '%s'."
                % (args, errorCode)
            )

        return outputPngPath
