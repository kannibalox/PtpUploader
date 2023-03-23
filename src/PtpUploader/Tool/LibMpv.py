import subprocess

from PtpUploader.PtpUploaderException import PtpUploaderException


class LibMpv:
    def __init__(self, logger, inputVideoPath):
        self.Logger = logger
        self.InputVideoPath = inputVideoPath
        self.ScaleSize = None

    def MakeScreenshotInPng(self, timeInSeconds, outputPngPath):
        import mpv

        self.Logger.info(
            "Making screenshot with libmpv from '%s' to '%s'."
            % (self.InputVideoPath, outputPngPath)
        )

        args = {
            "audio": "no",
            "screenshot-format": "png",
            "screenshot-png-compression": "9",
            "start": str(int(timeInSeconds)),
            "sub": "no",
            "vf": "lavfi=[scale='max(iw,iw*sar)':'max(ih/sar,ih)']",
            "vo": "null",
        }
        player = mpv.MPV(input_default_bindings=False, input_vo_keyboard=False, **args)

        @player.property_observer("video-frame-info")
        def time_observer(_name, value):
            if value is not None:
                if value["picture-type"] == "I":
                    player.frame_step()
                    img = player.screenshot_raw()
                    img.save(outputPngPath)
                    self.Logger.info("Saved to %s", outputPngPath)
                    player.quit(0)

        player.play(self.InputVideoPath)
        player.wait_for_playback()
        del player
