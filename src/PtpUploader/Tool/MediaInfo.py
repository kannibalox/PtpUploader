import re
import subprocess
import sys
import threading
import traceback

from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import Settings


class MediaInfo:
    # removePathFromCompleteName: this part will be removed from the path listed at "Complete Name". If removePathFromCompleteName is empty then it will be left as it is.
    def __init__(self, logger, path, removePathFromCompleteName):
        self.Path = path
        self.RemovePathFromCompleteName = removePathFromCompleteName
        self.FormattedMediaInfo = ""
        self.DurationInSec = 0
        self.Container = ""
        self.Codec = ""
        self.Width = 0
        self.Height = 0
        self.VideoWritingLibrary = ""
        self.Subtitles = []

        self.MediaInfoArgs = [Settings.MediaInfoPath, self.Path]
        self.MediaInfoProcess = None
        self.MediaInfoStdOut = ""
        self.ThreadExceptionMessage = None

        self.__ParseMediaInfo(logger)
        self.__ValidateParsedMediaInfo()

    def __MediaInfoThread(self):
        try:
            self.MediaInfoProcess = subprocess.Popen(
                self.MediaInfoArgs, stdout=subprocess.PIPE
            )
            self.MediaInfoStdOut, stderr = self.MediaInfoProcess.communicate()
        except Exception as e:
            self.ThreadExceptionMessage = traceback.format_exception_only(
                sys.exc_info()[0], sys.exc_info()[1]
            )

    # Returns with the output of MediaInfo.
    def __ReadMediaInfo(self, logger):
        logger.info("Reading media info from '%s'." % self.Path)

        # MediaInfo is buggy on some videos and takes a lot of time to finish. We limit this time to the user specified maximum.
        thread = threading.Thread(target=self.__MediaInfoThread)
        thread.start()
        if Settings.MediaInfoTimeOut > 0:
            thread.join(Settings.MediaInfoTimeOut)
        else:
            thread.join()

        if thread.isAlive():
            try:
                self.MediaInfoProcess.terminate()
            finally:
                thread.join()
                raise PtpUploaderException(
                    "Execution of MediaInfo command '%s' failed to finish in 60 seconds."
                    % self.MediaInfoArgs
                )

        if self.ThreadExceptionMessage is not None:
            logger.error(
                "Original exception in __MediaInfoThread: %s"
                % self.ThreadExceptionMessage
            )
            raise PtpUploaderException(
                "Got exception while trying to run MediaInfo command '%s'."
                % self.MediaInfoArgs
            )

        if self.MediaInfoProcess.returncode != 0:
            raise PtpUploaderException(
                "Execution of MediaInfo command '%s' returned with error code '%s'."
                % (self.MediaInfoArgs, self.MediaInfoProcess.returncode)
            )

        return self.MediaInfoStdOut.decode("utf-8", "ignore")

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
        mediaPropertyValue = mediaPropertyValue.replace("pixels", "")
        mediaPropertyValue = mediaPropertyValue.replace(" ", "")
        # Resolution may contain space, so remove. Eg.: 1 280
        return int(mediaPropertyValue)

    # Matches duration in the following format. All units and spaces are optional.
    # 1h 2min 3s
    # 1h2mn3s
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

        duration = 0
        if match.group(1):
            duration += int(match.group(1)) * 60 * 60
        if match.group(2):
            duration += int(match.group(2)) * 60
        if match.group(3):
            duration += int(match.group(3))

        return duration

    def __MakeCompleteNameRelative(self, path):
        if len(self.RemovePathFromCompleteName) > 0:
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
                elif section == "Video":
                    if mediaPropertyName == "Codec ID":
                        self.Codec = mediaPropertyValue.lower()
                    elif mediaPropertyName == "Width":
                        self.Width = MediaInfo.__ParseSize(mediaPropertyValue)
                    elif mediaPropertyName == "Height":
                        self.Height = MediaInfo.__ParseSize(mediaPropertyValue)
                    elif mediaPropertyName == "Writing library":
                        self.VideoWritingLibrary = mediaPropertyValue.lower()
                elif section.startswith("Text #") or section == "Text":
                    if mediaPropertyName == "Language":
                        self.Subtitles.append(mediaPropertyValue)

            self.FormattedMediaInfo += line + "\n"

        self.FormattedMediaInfo = self.FormattedMediaInfo.strip()

    def __ValidateParsedMediaInfo(self):
        if len(self.Container) <= 0:
            raise PtpUploaderException("MediaInfo returned with no container.")

        # IFOs and VOBs don't have codec.
        if len(self.Codec) <= 0 and (not self.IsIfo()) and (not self.IsVob()):
            raise PtpUploaderException("MediaInfo returned with no codec.")

        # IFOs may have zero duration.
        if self.DurationInSec <= 0 and (not self.IsIfo()):
            raise PtpUploaderException(
                "MediaInfo returned with invalid duration: '%s'." % self.DurationInSec
            )

        if self.Width <= 0:
            raise PtpUploaderException(
                "MediaInfo returned with invalid width: '%s'." % self.Width
            )

        if self.Height <= 0:
            raise PtpUploaderException(
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
        return self.Codec == "divx" or self.Codec == "dx50" or self.Codec == "div3"

    def IsXvid(self):
        return self.Codec == "xvid"

    def IsX264(self):
        return self.Codec == "x264" or (
            (self.Codec == "v_mpeg4/iso/avc" or self.Codec == "avc1")
            and self.VideoWritingLibrary.find("x264 core") == 0
        )

    def IsH264(self):
        return (
            self.Codec == "v_mpeg4/iso/avc" or self.Codec == "avc1"
        ) and self.VideoWritingLibrary.find("x264 core") == -1

    def IsVc1(self):
        return self.Codec == "wvc1" or self.Codec == "v_ms/vfw/fourcc / wvc1"

    def IsMpeg2Codec(self):
        return self.Codec == "v_mpeg2"
