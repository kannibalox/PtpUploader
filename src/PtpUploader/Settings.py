from .MyGlobals import MyGlobals
from .TagList import TagList

import codecs
import configparser
import fnmatch
import os
import os.path
import re
import subprocess


class Settings(object):
    @staticmethod
    def MakeListFromExtensionString(extensions):
        # Make sure everything is in lower case in the settings.
        extensions = extensions.lower()

        # If extensions is empty then we need an empty list. Splitting an empty string with a specified separator returns [''].
        extensions = extensions.strip()
        if len(extensions) > 0:
            list = extensions.split(",")
            for i in range(len(list)):
                list[i] = list[i].strip()

            return list
        else:
            return []

    # This makes a list of TagList.
    # Eg.: "A B, C, D E" will become [ [ "A", "B" ], [ "C" ], [ "D", "E" ] ]
    @staticmethod
    def MakeListOfListsFromString(extensions):
        list = Settings.MakeListFromExtensionString(extensions)
        for i in range(len(list)):
            list[i] = TagList(list[i].split(" "))

        return list

    @staticmethod
    def __HasValidExtensionToUpload(path, extensions):
        tempPath = path.lower()
        for extension in extensions:
            if fnmatch.fnmatch(tempPath, "*." + extension):
                return True

        return False

    @staticmethod
    def HasValidVideoExtensionToUpload(path):
        return Settings.__HasValidExtensionToUpload(
            path, Settings.VideoExtensionsToUpload
        )

    @staticmethod
    def HasValidAdditionalExtensionToUpload(path):
        return Settings.__HasValidExtensionToUpload(
            path, Settings.AdditionalExtensionsToUpload
        )

    @staticmethod
    def IsFileOnIgnoreList(path):
        path = os.path.basename(path)  # We only filter the filenames.
        path = path.lower()
        for ignoreFile in Settings.IgnoreFile:
            if re.match(ignoreFile, path) is not None:
                return True
        return False

    @staticmethod
    def GetAnnouncementWatchPath():
        return os.path.join(Settings.WorkingPath, "announcement")

    @staticmethod
    def GetAnnouncementInvalidPath():
        return os.path.join(Settings.WorkingPath, "announcement/invalid")

    @staticmethod
    def GetJobLogPath():
        return os.path.join(Settings.WorkingPath, "log/job")

    @staticmethod
    def GetTemporaryPath():
        return os.path.join(Settings.WorkingPath, "temporary")

    @staticmethod
    def GetDatabaseFilePath():
        return os.path.join(Settings.WorkingPath, "database.sqlite")

    @staticmethod
    def IsMplayerEnabled():
        return len(Settings.MplayerPath) > 0

    @staticmethod
    def IsMpvEnabled():
        return len(Settings.MpvPath) > 0

    @staticmethod
    def __LoadSceneGroups(path):
        groups = []
        file = open(path, "r")
        for line in file:
            groupName = line.strip()
            if len(groupName) > 0:
                groupName = groupName.lower()
                groups.append(groupName)
        file.close()
        return groups

    @staticmethod
    def __GetDefault(configParser, section, option, default, raw=False):
        try:
            return configParser.get(section, option, raw=raw)
        except configparser.NoOptionError:
            return default

    @staticmethod
    def GetDefault(section, option, default, raw=False):
        try:
            return Settings.configParser.get(section, option, raw=raw)
        except (configparser.NoOptionError, configparser.NoSectionError):
            return default

    @staticmethod
    def __GetPath(section, option, default=""):
        path = Settings.GetDefault(section, option, default)
        return os.path.expanduser(path)

    @staticmethod
    def LoadSettings():
        Settings.configParser = configParser = configparser.ConfigParser()

        # Load Settings.ini from the same directory where PtpUploader is.
        settingsDirectory, moduleFilename = os.path.split(
            __file__
        )  # __file__ contains the full path of the current running module
        settingsPath = os.path.join(settingsDirectory, "Settings.ini")
        if not os.path.isfile(settingsPath):
            settingsPath = os.path.expanduser("~/.config/ptpuploader/settings.ini")
        print(
            ("Loading settings from '%s'." % settingsPath)
        )  # MyGlobals.Logger is not initalized yet.
        fp = codecs.open(settingsPath, "r", "utf-8-sig")
        configParser.readfp(fp)
        fp.close()

        Settings.VideoExtensionsToUpload = Settings.MakeListFromExtensionString(
            configParser.get("Settings", "VideoExtensionsToUpload")
        )
        Settings.AdditionalExtensionsToUpload = Settings.MakeListFromExtensionString(
            Settings.__GetDefault(
                configParser,
                "Settings",
                "AdditionalExtensionsToUpload",
                "bup, idx, ifo, srt, sub",
            )
        )
        Settings.IgnoreFile = Settings.MakeListFromExtensionString(
            Settings.__GetDefault(configParser, "Settings", "IgnoreFile", "")
        )
        Settings.PtpAnnounceUrl = configParser.get("Settings", "PtpAnnounceUrl")
        Settings.PtpUserName = configParser.get("Settings", "PtpUserName")
        Settings.PtpPassword = configParser.get("Settings", "PtpPassword")

        Settings.ImageHost = Settings.__GetDefault(
            configParser, "Settings", "ImageHost", "ptpimg.me"
        ).lower()
        Settings.PtpImgApiKey = Settings.__GetDefault(
            configParser, "Settings", "PtpImgApiKey", ""
        )
        Settings.OnSuccessfulUpload = Settings.__GetDefault(
            configParser, "Settings", "OnSuccessfulUpload", "", raw=True
        )

        Settings.FfmpegPath = Settings.__GetPath("Settings", "FfmpegPath")
        Settings.MediaInfoPath = Settings.__GetPath("Settings", "MediaInfoPath")
        Settings.MplayerPath = Settings.__GetPath("Settings", "MplayerPath")
        Settings.MpvPath = Settings.__GetPath("Settings", "MpvPath")
        Settings.UnrarPath = Settings.__GetPath("Settings", "UnrarPath")
        Settings.ImageMagickConvertPath = Settings.__GetPath(
            "Settings", "ImageMagickConvertPath"
        )

        Settings.WorkingPath = os.path.expanduser(
            configParser.get("Settings", "WorkingPath")
        )

        Settings.AllowReleaseTag = Settings.MakeListOfListsFromString(
            Settings.__GetDefault(configParser, "Settings", "AllowReleaseTag", "")
        )
        Settings.IgnoreReleaseTag = Settings.MakeListOfListsFromString(
            Settings.__GetDefault(configParser, "Settings", "IgnoreReleaseTag", "")
        )
        Settings.IgnoreReleaseTagAfterYear = Settings.MakeListOfListsFromString(
            Settings.__GetDefault(
                configParser, "Settings", "IgnoreReleaseTagAfterYear", ""
            )
        )
        Settings.IgnoreReleaserGroup = Settings.MakeListFromExtensionString(
            Settings.__GetDefault(configParser, "Settings", "IgnoreReleaserGroup", "")
        )
        Settings.SceneReleaserGroup = Settings.__LoadSceneGroups(
            os.path.join(
                os.path.expanduser("~/.config/ptpuploader"), "scene_groups.txt"
            )
        )

        Settings.WebServerAddress = Settings.__GetDefault(
            configParser, "Settings", "WebServerAddress", ""
        )
        Settings.WebServerAddress = Settings.WebServerAddress.replace("http://", "")
        Settings.WebServerAddress = Settings.WebServerAddress.replace("https://", "")

        Settings.WebServerUsername = Settings.__GetDefault(
            configParser, "Settings", "WebServerUsername", "admin"
        )
        Settings.WebServerPassword = Settings.__GetDefault(
            configParser, "Settings", "WebServerPassword", ""
        )
        Settings.WebServerSslCertificatePath = Settings.__GetPath(
            "Settings", "WebServerSslCertificatePath"
        )
        Settings.WebServerSslPrivateKeyPath = Settings.__GetPath(
            "Settings", "WebServerSslPrivateKeyPath"
        )
        Settings.WebServerFileTreeInitRoot = Settings.__GetPath(
            "Settings", "WebServerFileTreeInitRoot", "~"
        )

        Settings.GreasemonkeyTorrentSenderPassword = Settings.__GetDefault(
            configParser, "Settings", "GreasemonkeyTorrentSenderPassword", ""
        )
        Settings.OpenJobPageLinksInNewTab = Settings.__GetDefault(
            configParser, "Settings", "OpenJobPageLinksInNewTab", "0"
        )
        Settings.OverrideScreenshots = (
            int(
                Settings.__GetDefault(
                    configParser, "Settings", "OverrideScreenshots", "0"
                )
            )
            != 0
        )
        Settings.ForceDirectorylessSingleFileTorrent = (
            int(
                Settings.__GetDefault(
                    configParser, "Settings", "MakeTorrentWithoutDirectory", "0"
                )
            )
            != 0
        )
        Settings.PersonalRip = (
            int(Settings.__GetDefault(configParser, "Settings", "PersonalRip", "0"))
            != 0
        )
        Settings.ReleaseNotes = Settings.__GetDefault(
            configParser, "Settings", "ReleaseNotes", ""
        ).strip()
        Settings.SkipDuplicateChecking = (
            int(
                Settings.__GetDefault(
                    configParser, "Settings", "SkipDuplicateChecking", "0"
                )
            )
            != 0
        )

        Settings.SizeLimitForAutoCreatedJobs = (
            float(
                Settings.__GetDefault(
                    configParser, "Settings", "SizeLimitForAutoCreatedJobs", "0"
                )
            )
            * 1024
            * 1024
            * 1024
        )
        Settings.StopIfSynopsisIsMissing = Settings.__GetDefault(
            configParser, "Settings", "StopIfSynopsisIsMissing", ""
        )
        Settings.StopIfCoverArtIsMissing = Settings.__GetDefault(
            configParser, "Settings", "StopIfCoverArtIsMissing", ""
        )
        Settings.StopIfImdbRatingIsLessThan = Settings.__GetDefault(
            configParser, "Settings", "StopIfImdbRatingIsLessThan", ""
        )
        Settings.StopIfImdbVoteCountIsLessThan = Settings.__GetDefault(
            configParser, "Settings", "StopIfImdbVoteCountIsLessThan", ""
        )
        Settings.MediaInfoTimeOut = int(
            Settings.__GetDefault(configParser, "Settings", "MediaInfoTimeOut", "60")
        )

        Settings.TorrentClientName = Settings.__GetDefault(
            configParser, "Settings", "TorrentClient", "rTorrent"
        )
        Settings.TorrentClientAddress = Settings.__GetDefault(
            configParser, "Settings", "TorrentClientAddress", "127.0.0.1"
        )
        Settings.TorrentClientPort = Settings.__GetDefault(
            configParser, "Settings", "TorrentClientPort", "9091"
        )

        # Create the announcement directory.
        # Invalid announcement directory is within the announcement directory, so we don't have to make the announcement directory separately.
        announcementPath = Settings.GetAnnouncementInvalidPath()
        if not os.path.exists(announcementPath):
            os.makedirs(announcementPath)

        # Create the log directory.
        # Job log directory is within the log directory, so we don't have to make the log directory separately.
        jobLogPath = Settings.GetJobLogPath()
        if not os.path.exists(jobLogPath):
            os.makedirs(jobLogPath)

        # Create the temporary directory.
        temporaryPath = Settings.GetTemporaryPath()
        if not os.path.exists(temporaryPath):
            os.makedirs(temporaryPath)

    @staticmethod
    def __VerifyProgramPath(programName, arguments):
        if len(arguments[0]) <= 0:
            MyGlobals.Logger.error("%s isn't set in the settings!" % programName)
            return False

        try:
            proc = subprocess.Popen(
                arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = proc.communicate()
            errorCode = proc.wait()
        except OSError as e:
            MyGlobals.Logger.error(
                "%s isn't set properly in the settings!" % programName
            )
            MyGlobals.Logger.error(
                "Execution of %s at '%s' caused an exception. Error message: '%s'."
                % (programName, arguments[0], str(e))
            )
            return False

        return True

    @staticmethod
    def VerifyPaths():
        MyGlobals.Logger.info("Checking paths")

        if not Settings.__VerifyProgramPath(
            "MediaInfo", [Settings.MediaInfoPath, "--version"]
        ):
            return False

        if Settings.IsMpvEnabled():
            if not Settings.__VerifyProgramPath("mpv", [Settings.MpvPath]):
                return False
        elif Settings.IsMplayerEnabled():
            if not Settings.__VerifyProgramPath("mplayer", [Settings.MplayerPath]):
                return False
        else:
            if not Settings.__VerifyProgramPath(
                "ffmpeg", [Settings.FfmpegPath, "--help"]
            ):
                return False

        # Optional
        if len(Settings.UnrarPath) > 0 and (
            not Settings.__VerifyProgramPath("unrar", [Settings.UnrarPath])
        ):
            return False

        # Optional
        if len(Settings.ImageMagickConvertPath) > 0 and (
            not Settings.__VerifyProgramPath(
                "ImageMagick Convert", [Settings.ImageMagickConvertPath, "--version"]
            )
        ):
            return False

        return True
