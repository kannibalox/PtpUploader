from .Tool.Unrar import Unrar

from .Helper import GetFileListFromTorrent
from .Settings import Settings

import os
import json


class IncludedFileItemState:
    Ignore = 0
    Include = 1


class IncludedFileItem:
    def __init__(self, name):
        self.Name = name  # Path separator is always a "/".
        self.DefaultState = self.__GetDefaultState()
        self.State = self.DefaultState

    def __GetDefaultState(self):
        path = self.Name.lower()

        # Ignore special root directories.
        # !sample is used in HDBits releases.
        # Extras must be uploaded separately on PTP.
        if (
            path.startswith("proof/")
            or path.startswith("sample/")
            or path.startswith("!sample/")
            or path.startswith("samples/")
            or path.startswith("extra/")
            or path.startswith("extras/")
        ):
            return IncludedFileItemState.Ignore

        name = os.path.basename(path)
        if Settings.IsFileOnIgnoreList(name):
            return IncludedFileItemState.Ignore

        if Settings.HasValidVideoExtensionToUpload(
            name
        ) or Settings.HasValidAdditionalExtensionToUpload(name):
            return IncludedFileItemState.Include
        elif Unrar.IsFirstRar(name):
            return IncludedFileItemState.Include
        else:
            return IncludedFileItemState.Ignore

    def IsDefaultIgnored(self):
        return self.DefaultState == IncludedFileItemState.Ignore

    def IsDefaultIncluded(self):
        return self.DefaultState == IncludedFileItemState.Include

    def IsIgnored(self):
        return self.State == IncludedFileItemState.Ignore

    def IsIncluded(self):
        return self.State == IncludedFileItemState.Include


class IncludedFileList:
    def __init__(self):
        self.Files = []  # Contains IncludedFileItems.

    def __GetFile(self, path):
        pathLower = path.lower()
        for file in self.Files:
            if file.Name.lower() == pathLower:
                return file

        return None

    def IsIgnored(self, path):
        file = self.__GetFile(path)
        return file and file.IsIgnored()

    def IsIncluded(self, path):
        file = self.__GetFile(path)
        return file and file.IsIncluded()

    def FromTorrent(self, torrentFilePath):
        self.Files = []
        fileList = GetFileListFromTorrent(torrentFilePath)
        for file in fileList:
            self.Files.append(IncludedFileItem(file))

    def __FromDirectoryInternal(self, path, baseRelativePath):
        entries = os.listdir(path)
        for entry in entries:
            absolutePath = os.path.join(path, entry)
            relativePath = entry
            if len(baseRelativePath) > 0:
                relativePath = baseRelativePath + "/" + entry

            if os.path.isdir(absolutePath):
                self.__FromDirectoryInternal(absolutePath, relativePath)
            elif os.path.isfile(absolutePath):
                self.Files.append(IncludedFileItem(relativePath))

    def FromDirectory(self, path):
        self.Files = []
        self.__FromDirectoryInternal(path, "")

    def ApplyCustomizationFromJson(self, jsonString):
        if len(jsonString) <= 0:
            return

        # Key contains the path, value contains the include state (as bool).
        dictionary = json.loads(jsonString)
        for path, include in list(dictionary.items()):
            file = self.__GetFile(path)
            if file is None:
                file = IncludedFileItem(path)
                self.Files.append(file)

            if include:
                file.State = IncludedFileItemState.Include
            else:
                file.State = IncludedFileItemState.Ignore
