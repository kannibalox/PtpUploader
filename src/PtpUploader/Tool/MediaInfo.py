import re
import subprocess

from pathlib import Path

from PtpUploader.Helper import GetSizeFromText
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import Settings, config


class MediaInfoException(PtpUploaderException):
    pass


class MediaInfo:
    # removePathFromCompleteName: this part will be removed from the path listed at "Complete Name". If removePathFromCompleteName is empty then it will be left as it is.
    def __init__(self, logger, path, removePathFromCompleteName):
        self.Path = path
        self.RemovePathFromCompleteName = removePathFromCompleteName
        self.FormattedMediaInfo = ""
        self.DurationInSec = 0
        self.Container = ""
        self.Codec = ""
        # Mediainfo can possibly return a larger file size than
        # the one actually being read. RealFileSize reflects the
        # size on disk, while FileSize is parsed from the output.
        self.FileSize: int = 0
        self.RealFileSize: int = 0
        self.Width: int = 0
        self.Height: int = 0
        self.DAR: str = ""
        self.VideoWritingLibrary = ""
        self.Subtitles = []

        self.MediaInfoArgs = [config.tools.mediainfo.path, self.Path]

        self.__ParseMediaInfo(logger)
        self.__ValidateParsedMediaInfo()

    # Returns with the output of MediaInfo.
    def __ReadMediaInfo(self, logger):
        logger.info("Reading media info from '%s'." % self.Path)

        # MediaInfo is buggy on some videos and takes a lot of time to finish. We limit this time to the user specified maximum.
        proc = subprocess.run(
            self.MediaInfoArgs,
            timeout=config.tools.mediainfo.timeout,
            capture_output=True,
            check=True,
        )
        self.RealFileSize = Path(self.Path).stat().st_size
        return proc.stdout.decode("utf-8", "ignore")

    # removePathFromCompleteName: see MediaInfo's constructor
    # Returns with the media infos for all files in videoFiles.
    @staticmethod
    def ReadAndParseMediaInfos(logger, videoFiles, removePathFromCompleteName):
        mediaInfos = []
        for video in videoFiles:
            mediaInfo = MediaInfo(logger, video, removePathFromCompleteName)
            mediaInfos.append(mediaInfo)

        return mediaInfos

    @staticmethod
    def __ParseSize(mediaPropertyValue):
        return int(mediaPropertyValue.replace("pixels", "").replace(" ", ""))

    # Matches duration in the following format. All units and spaces are optional.
    # 1h 2min 3s
    # 1h2mn3s
    # 900 ms
    @staticmethod
    def __GetDurationInSec(duration):
        # Nice regular expression. :)
        # r means to do not unescape the string
        # ?: means to do not store that group capture
        duration = duration.replace("mn", "min")
        duration = duration.replace(" ", "")
        match = re.match(r"(?:(\d+)h)?(?:(\d+)min)?(?:(\d+)s)?", duration)
        if not match:
            return 0

        # It's returned milliseconds, but we're dealing in seconds
        if duration.endswith("ms"):
            duration = 1
        else:
            duration = 0
        if match.group(1):
            duration += int(match.group(1)) * 60 * 60
        if match.group(2):
            duration += int(match.group(2)) * 60
        if match.group(3):
            duration += int(match.group(3))

        return duration

    def __MakeCompleteNameRelative(self, path):
        if self.RemovePathFromCompleteName:
            removePathFromCompleteName = self.RemovePathFromCompleteName.replace(
                "\\", "/"
            )
            if not removePathFromCompleteName.endswith("/"):
                removePathFromCompleteName += "/"

            path = path.replace("\\", "/")
            path = path.replace(removePathFromCompleteName, "")

        return path

    def __ParseMediaInfo(self, logger):
        # We can't simply store mediaInfoText in self.FormattedMediaInfo because the "Complete name" property gets modified.
        # (By removing the full path if needed.)
        mediaInfoText = self.__ReadMediaInfo(logger)

        section = ""
        for line in mediaInfoText.splitlines():
            if line.find(":") == -1:
                if len(line) > 0:
                    section = line
            else:
                mediaPropertyName, separator, mediaPropertyValue = line.partition(": ")
                originalMediaPropertyName = mediaPropertyName
                mediaPropertyName = mediaPropertyName.strip()

                if section == "General":
                    if mediaPropertyName == "Complete name":
                        line = (
                            originalMediaPropertyName
                            + separator
                            + self.__MakeCompleteNameRelative(mediaPropertyValue)
                        )
                    elif mediaPropertyName == "Format":
                        self.Container = mediaPropertyValue.lower()
                    elif mediaPropertyName == "Duration":
                        self.DurationInSec = MediaInfo.__GetDurationInSec(
                            mediaPropertyValue
                        )
                    elif mediaPropertyName == "File size":
                        self.FileSize = GetSizeFromText(mediaPropertyValue)
                elif section == "Video":
                    if mediaPropertyName == "Codec ID":
                        self.Codec = mediaPropertyValue.lower()
                    elif mediaPropertyName == "Width":
                        self.Width = MediaInfo.__ParseSize(mediaPropertyValue)
                    elif mediaPropertyName == "Height":
                        self.Height = MediaInfo.__ParseSize(mediaPropertyValue)
                    elif mediaPropertyName == "Writing library":
                        self.VideoWritingLibrary = mediaPropertyValue.lower()
                    elif mediaPropertyName == "Display aspect ratio":
                        self.DAR = mediaPropertyValue.lower().strip()
                elif section.startswith("Text #") or section == "Text":
                    if mediaPropertyName == "Language":
                        self.Subtitles.append(mediaPropertyValue)

            self.FormattedMediaInfo += line + "\n"

        self.FormattedMediaInfo = self.FormattedMediaInfo.strip()

    def __ValidateParsedMediaInfo(self):
        if len(self.Container) <= 0:
            raise MediaInfoException("MediaInfo returned with no container.")

        # IFOs and VOBs don't have codec.
        if len(self.Codec) <= 0 and (not self.IsIfo()) and (not self.IsVob()):
            raise MediaInfoException("MediaInfo returned with no codec.")

        # IFOs may have zero duration.
        if self.DurationInSec <= 0 and (not self.IsIfo()):
            raise MediaInfoException(
                "MediaInfo returned with invalid duration: '%s'." % self.DurationInSec
            )

        if self.Width <= 0:
            raise MediaInfoException(
                "MediaInfo returned with invalid width: '%s'." % self.Width
            )

        if self.Height <= 0:
            raise MediaInfoException(
                "MediaInfo returned with invalid height: '%s'." % self.Height
            )

    def IsAvi(self):
        return self.Container == "avi"

    def IsIfo(self):
        return self.Container == "dvd video"

    def IsMkv(self):
        return self.Container == "matroska"

    def IsMp4(self):
        return self.Container == "mpeg-4"

    def IsVob(self):
        return self.Container == "mpeg-ps"

    def IsDivx(self):
        return self.Codec in ["divx", "dx50", "div3"]

    def IsXvid(self):
        return self.Codec == "xvid"

    def IsX264(self):
        return self.Codec == "x264" or (
            (self.Codec in ["v_mpeg4/iso/avc", "avc1", "h264"])
            and self.VideoWritingLibrary.find("x264 core") == 0
        )

    def IsH264(self):
        return (
            self.Codec in ["v_mpeg4/iso/avc", "avc1", "h264"]
        ) and self.VideoWritingLibrary.find("x264 core") == -1

    def IsVc1(self):
        return self.Codec in ["wvc1", "v_ms/vfw/fourcc / wvc1"]

    def IsMpeg2Codec(self):
        return self.Codec == "v_mpeg2"
