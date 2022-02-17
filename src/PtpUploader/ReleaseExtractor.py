import fnmatch
import os

from pathlib import Path

from unidecode import unidecode

from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import Settings
from PtpUploader.Tool.Unrar import Unrar


def validate_directory(releaseInfo):
    path = Path(releaseInfo.GetReleaseUploadPath())
    video_files = []
    addtl_files = []
    for child in path.rglob("*"):
        if child.is_file():
            if child.suffix.lower().strip(".") in Settings.VideoExtensionsToUpload:
                video_files.append(child)
            elif (
                child.suffix.lower().strip(".") in Settings.AdditionalExtensionsToUpload
            ):
                addtl_files.append(child)
    return video_files, addtl_files


class ReleaseExtractorInternal:
    def __init__(
        self,
        sourcePath,
        relativeSourcePath,
        destinationPath,
        includedFileList,
        topLevelDirectoriesToIgnore=[],
        handleSceneFolders=False,
    ):
        self.SourcePath = sourcePath
        self.RelativeSourcePath = relativeSourcePath  # Must be separated with "/".
        self.DestinationPath = destinationPath
        self.IncludedFileList = includedFileList
        self.TopLevelDirectoriesToIgnore = topLevelDirectoriesToIgnore  # Used only for PTP directory when extracting inplace (for File source).
        self.HandleSceneFolders = handleSceneFolders
        self.DestinationPathCreated = False

    def __MakeDestinationDirectory(self):
        if not self.DestinationPathCreated:
            if os.path.exists(self.DestinationPath):
                if not os.path.isdir(self.DestinationPath):
                    raise PtpUploaderException(
                        "Can't make destination directory '%s' because path already exists."
                        % self.DestinationPath
                    )
            else:
                os.makedirs(self.DestinationPath)

            self.DestinationPathCreated = True

        return self.DestinationPath

    def Extract(self):
        # Extract RARs.
        rars = Unrar.GetRars(self.SourcePath)
        for rar in rars:
            entryName = os.path.basename(rar)
            if self.IncludedFileList.IsIncluded(
                self.__MakeRelativeSourcePath(entryName)
            ):
                Unrar.Extract(rar, self.__MakeDestinationDirectory())

        entries = os.listdir(self.SourcePath)
        for entryName in entries:
            entryPath = os.path.join(self.SourcePath, entryName)
            if os.path.isdir(entryPath):
                self.__HandleDirectory(entryName, entryPath)
            elif os.path.isfile(entryPath):
                self.__HandleFile(entryName, entryPath)

    def __IsDirectoryOnTheIgnoreList(self, directoryName):
        return directoryName in self.TopLevelDirectoriesToIgnore

    def __MakeRelativeSourcePath(self, name):
        if len(self.RelativeSourcePath) > 0:
            return self.RelativeSourcePath + "/" + name
        else:
            return name

    def __HandleDirectory(self, entryName, entryPath):
        entryLower = entryName.lower()
        if self.HandleSceneFolders and (
            fnmatch.fnmatch(entryLower, "cd*")
            or entryLower == "sub"
            or entryLower == "subs"
            or entryLower == "subtitle"
            or entryLower == "subtitles"
        ):
            # Special scene folders in the root will be extracted without making a directory for them in the destination.
            releaseExtractor = ReleaseExtractorInternal(
                entryPath,
                self.__MakeRelativeSourcePath(entryName),
                self.DestinationPath,
                self.IncludedFileList,
            )
            releaseExtractor.Extract()
        elif self.__IsDirectoryOnTheIgnoreList(entryLower):
            # We don't need these.
            # (The if is nicer this way than combining this and the next block.)
            pass
        else:
            # Handle other directories normally.
            destinationDirectoryPath = os.path.join(self.DestinationPath, entryName)
            releaseExtractor = ReleaseExtractorInternal(
                entryPath,
                self.__MakeRelativeSourcePath(entryName),
                destinationDirectoryPath,
                self.IncludedFileList,
            )
            releaseExtractor.Extract()

    def __HandleFile(self, entryName, entryPath):
        if self.IncludedFileList.IsIgnored(
            self.__MakeRelativeSourcePath(entryName)
        ) or Unrar.IsFirstRar(entryName):
            return

        # Make hard link from supported files.
        destinationFilePath = os.path.join(
            self.__MakeDestinationDirectory(), unidecode(entryName)
        )
        if os.path.exists(destinationFilePath):
            if os.path.samefile(entryPath, destinationFilePath):
                return
            else:
                raise PtpUploaderException(
                    "Can't make link from file '%s' to '%s' because destination already exists."
                    % (entryPath, destinationFilePath)
                )
        os.link(entryPath, destinationFilePath)


class ReleaseExtractor:
    @staticmethod
    def __ValidateDirectoryInternal(
        logger,
        path,
        baseRelativePath,
        includedFileList,
        throwExceptionForUnsupportedFiles,
        videos,
        additionalFiles,
    ):
        entries = os.listdir(path)
        for entry in entries:
            absolutePath = os.path.join(path, entry)
            relativePath = entry
            if len(baseRelativePath) > 0:
                relativePath = baseRelativePath + "/" + entry

            if os.path.isdir(absolutePath):
                ReleaseExtractor.__ValidateDirectoryInternal(
                    logger,
                    absolutePath,
                    relativePath,
                    includedFileList,
                    throwExceptionForUnsupportedFiles,
                    videos,
                    additionalFiles,
                )
            elif os.path.isfile(absolutePath):
                if Settings.HasValidVideoExtensionToUpload(entry):
                    videos.append(absolutePath)
                # Here we are checking the IncludedFileList for included files because with that it is possible to include unsupported files.
                elif Settings.HasValidAdditionalExtensionToUpload(
                    entry
                ) or includedFileList.IsIncluded(relativePath):
                    additionalFiles.append(absolutePath)
                elif throwExceptionForUnsupportedFiles:
                    raise PtpUploaderException(
                        "File '%s' has unsupported extension." % absolutePath
                    )

    # Makes sure that path only contains supported extensions.
    # Returns with a tuple of list of the video files and the list of additional files.
    @staticmethod
    def ValidateDirectory(
        logger, path, includedFileList, throwExceptionForUnsupportedFiles=True
    ):
        logger.info("Validating directory '%s'." % path)

        videos = []
        additionalFiles = []
        ReleaseExtractor.__ValidateDirectoryInternal(
            logger,
            path,
            "",
            includedFileList,
            throwExceptionForUnsupportedFiles,
            videos,
            additionalFiles,
        )
        return videos, additionalFiles

    # Extracts RAR files and creates hard links from supported files from the source to the destination directory.
    # Except of special scene folders (CD*, Subs) in the root, the directory hierarchy is kept.
    @staticmethod
    def Extract(
        logger,
        sourcePath,
        destinationPath,
        includedFileList,
        topLevelDirectoriesToIgnore=[],
    ):
        logger.info(
            "Extracting directory '%s' to '%s'." % (sourcePath, destinationPath)
        )

        releaseExtractor = ReleaseExtractorInternal(
            sourcePath,
            "",
            destinationPath,
            includedFileList,
            topLevelDirectoriesToIgnore,
            handleSceneFolders=True,
        )
        releaseExtractor.Extract()

        # Extract and delete RARs at the destination directory. Subtitles in scene releases usually are compressed twice. Yup, it is stupid.
        rars = Unrar.GetRars(destinationPath)
        for rar in rars:
            Unrar.Extract(rar, destinationPath)
            os.remove(rar)
