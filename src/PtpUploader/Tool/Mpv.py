import subprocess

from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import Settings


class Mpv:
    def __init__(self, logger, inputVideoPath):
        self.Logger = logger
        self.InputVideoPath = inputVideoPath
        self.ScaleSize = None

    def MakeScreenshotInPng(self, timeInSeconds, outputPngPath):
        self.Logger.info(
            "Making screenshot with mpv from '%s' to '%s'."
            % (self.InputVideoPath, outputPngPath)
        )

        args = [
            Settings.MpvPath,
            "--no-config",
            "--no-audio",
            "--no-sub",
            "--start=" + str(int(timeInSeconds)),
            "--frames=1",
            "--screenshot-format=png",
            "--screenshot-png-compression=9",  # doesn't seem to be working
            "--vf=lavfi=[scale='max(iw,iw*sar)':'max(ih/sar,ih)']",
            "--o=" + outputPngPath,
            self.InputVideoPath,
        ]

        errorCode = subprocess.call(args)
        if errorCode != 0:
            raise PtpUploaderException(
                "Process execution '%s' returned with error code '%s'."
                % (args, errorCode)
            )
