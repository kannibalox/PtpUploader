import configparser
import fnmatch
import os
import os.path
import re
import shutil
import logging

from pathlib import Path

logger = logging.getLogger(__name__)


class Settings:
    @staticmethod
    def MakeListFromExtensionString(extensions: str):
        # Make sure everything is in lower case in the settings.
        return [i.strip().lower() for i in extensions.split(",")]

    # This makes a list of TagList.
    # Eg.: "A B, C, D E" will become [ [ "A", "B" ], [ "C" ], [ "D", "E" ] ]
    @staticmethod
    def MakeListOfListsFromString(extensions: str):
        return [i.split(" ") for i in Settings.MakeListFromExtensionString(extensions)]

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
    def GetAnnouncementWatchPath() -> Path:
        return Path(Settings.WorkingPath, "announcement")

    @staticmethod
    def GetAnnouncementInvalidPath() -> Path:
        return Path(Settings.WorkingPath, "announcement/invalid")

    @staticmethod
    def GetJobLogPath() -> Path:
        return Path(Settings.WorkingPath, "log/job")

    @staticmethod
    def GetTemporaryPath() -> Path:
        return Path(Settings.WorkingPath, "temporary")

    @staticmethod
    def GetDatabaseFilePath() -> Path:
        return Path(Settings.WorkingPath, "database.sqlite")

    @staticmethod
    def __LoadSceneGroups(path):
        groups = []
        with open(path, "r") as handle:
            for line in handle.readlines():
                groupName = line.strip().lower()
                if groupName:
                    groups.append(groupName)
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
        settingsDirectory, _ = os.path.split(
            __file__
        )  # __file__ contains the full path of the current running module
        settingsPath = os.path.join(settingsDirectory, "Settings.ini")
        defaultSettingsPath = os.path.join(settingsDirectory, "Settings.example.ini")
        configParser.read(defaultSettingsPath)

        if not os.path.isfile(settingsPath):
            settingsPath = os.path.expanduser("~/.config/ptpuploader/settings.ini")
        logger.info(
            "Loading settings from '%s'.", settingsPath
        )  # MyGlobals.Logger is not initalized yet.
        configParser.read(settingsPath)

        Settings.VideoExtensionsToUpload = Settings.MakeListFromExtensionString(
            configParser.get("Settings", "VideoExtensionsToUpload")
        )
        Settings.AdditionalExtensionsToUpload = Settings.MakeListFromExtensionString(
            configParser.get(
                "Settings",
                "AdditionalExtensionsToUpload",
            )
        )
        Settings.TorrentClient = None
        Settings.IgnoreFile = Settings.MakeListFromExtensionString(
            configParser.get("Settings", "IgnoreFile")
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
        Settings.MediaInfoPath = Settings.__GetPath(
            "Settings", "MediaInfoPath", "mediainfo"
        )
        Settings.MplayerPath = Settings.__GetPath("Settings", "MplayerPath", "mplayer")
        Settings.MpvPath = Settings.__GetPath("Settings", "MpvPath", "mpv")
        Settings.UnrarPath = Settings.__GetPath("Settings", "UnrarPath", "unrar")
        Settings.ImageMagickConvertPath = Settings.__GetPath(
            "Settings", "ImageMagickConvertPath", "convert"
        )

        Settings.WorkingPath = os.getenv("PTPUP_WORKDIR") or os.path.expanduser(
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

        scene_file = Path(
            os.path.expanduser("~/.config/ptpuploader"), "scene_groups.txt"
        )
        if not scene_file.exists():
            scene_file = Path(settingsDirectory, "SceneGroups.txt")
        Settings.SceneReleaserGroup = Settings.__LoadSceneGroups(scene_file)

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

        Settings.AntiCsrfToken = None  # Stored after logging in
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

        # Create required directories.
        Settings.GetAnnouncementInvalidPath().mkdir(parents=True, exist_ok=True)
        Settings.GetJobLogPath().mkdir(parents=True, exist_ok=True)
        Settings.GetTemporaryPath().mkdir(parents=True, exist_ok=True)

    @staticmethod
    def GetTorrentClient():
        if Settings.TorrentClient is None:
            if Settings.TorrentClientName.lower() == "transmission":
                from PtpUploader.Tool.Transmission import Transmission

                Settings.TorrentClient = Transmission(
                    Settings.TorrentClientAddress, Settings.TorrentClientPort
                )
            else:
                from PtpUploader.Tool.Rtorrent import Rtorrent

                Settings.TorrentClient = Rtorrent()
        return Settings.TorrentClient

    @staticmethod
    def VerifyPaths():
        logger.info("Checking paths")

        if shutil.which(Settings.MediaInfoPath) is None:
            logger.critical(
                "Mediainfo not found with command '%s'!", Settings.MediaInfoPath
            )
            return False

        if (
            shutil.which(Settings.MpvPath) is None
            and shutil.which(Settings.MplayerPath) is None
            and shutil.which(Settings.FfmpegPath) is None
        ):
            logger.critical("At least one of mpv, mplayer or ffmpeg is required!")
            return False

        # Optional
        if Settings.UnrarPath and shutil.which(Settings.UnrarPath):
            logger.error("Unrar path is set but not found: %s", Settings.UnrarPath)
        if Settings.ImageMagickConvertPath and shutil.which(
            Settings.ImageMagickConvertPath
        ):
            logger.error(
                "ImageMagick path is set but not found: %s",
                Settings.ImageMagickConvertPath,
            )

        return True
