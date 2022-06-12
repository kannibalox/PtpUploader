import argparse
import os

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PtpUploader.web.settings")
django.setup()

from PtpUploader import release_extractor
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.ReleaseDescriptionFormatter import ReleaseDescriptionFormatter
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Settings import Settings
from PtpUploader.Tool import Mktor


class ReleaseInfoMaker:
    def __init__(self, path):
        self.Path = path
        self.ReleaseName = None
        self.WorkingDirectory = None
        self.TorrentDataPath = None
        self.VideoFiles = []
        self.AdditionalFiles = []

    def CollectVideoFiles(self):
        self.Path = os.path.abspath(self.Path)

        if os.path.isdir(self.Path):
            # Make sure that path doesn't ends with a trailing slash or else os.path.split would return with wrong values.
            self.Path = self.Path.rstrip("\\/")

            (
                self.VideoFiles,
                self.AdditionalFiles,
            ) = release_extractor.find_allowed_files(
                self.Path,
            )
            if len(self.VideoFiles) <= 0:
                print("Path '%s' doesn't contain any videos!" % self.Path)
                return False

            # We use the parent directory of the path as the working directory.
            # Release name will be the directory's name. Eg. it will be "anything" for "/something/anything"
            self.WorkingDirectory, self.ReleaseName = os.path.split(self.Path)
            self.TorrentDataPath = self.Path
        elif os.path.isfile(self.Path):
            self.VideoFiles.append(self.Path)

            # We use same the directory where the file is as the working directory.
            # Release name will be the file's name without extension.
            self.WorkingDirectory, self.ReleaseName = os.path.split(self.Path)
            self.ReleaseName, _ = os.path.splitext(self.ReleaseName)
            self.TorrentDataPath = self.WorkingDirectory
        else:
            print("Path '%s' doesn't exist!" % self.Path)
            return False

        return True

    def MarkAsDvdImageIfNeeded(self, releaseInfo):
        for file in self.AdditionalFiles:
            if file.lower().endswith(".ifo"):
                releaseInfo.Codec = "DVD5"
                # Make sure that ReleaseDescriptionFormatter will recognize this as a DVD image.
                if not releaseInfo.IsDvdImage():
                    raise PtpUploaderException(
                        "Codec is set to DVD5, yet release info says that this is not a DVD image."
                    )

                return

    def MarkAsBlurayImageIfNeeded(self, releaseInfo):
        if os.path.isdir(self.Path) and "BDMV" in os.listdir(self.Path):
            releaseInfo.Codec = "BD25"

    def SaveReleaseDescriptionFile(
        self, logger, releaseDescriptionFilePath, createScreens
    ):
        releaseInfo = ReleaseInfo()
        releaseInfo.Logger = logger
        releaseInfo.ReleaseName = self.ReleaseName
        releaseInfo.ReleaseUploadPath = self.TorrentDataPath
        self.MarkAsDvdImageIfNeeded(releaseInfo)
        self.MarkAsBlurayImageIfNeeded(releaseInfo)

        outputImageDirectory = self.WorkingDirectory
        releaseDescriptionFormatter = ReleaseDescriptionFormatter(
            releaseInfo,
            self.VideoFiles,
            self.AdditionalFiles,
            outputImageDirectory,
            createScreens,
        )
        releaseDescription = releaseDescriptionFormatter.Format(includeReleaseName=True)

        with open(releaseDescriptionFilePath, "w") as handle:
            handle.write(releaseDescription)

    def MakeReleaseInfo(self, createTorrent=True, createScreens=True):
        logger = MyGlobals.Logger

        if not self.CollectVideoFiles():
            return

        # Make sure the files we are generating are not present.

        releaseDescriptionFilePath = os.path.join(
            self.WorkingDirectory,
            "PTP " + self.ReleaseName + ".release description.txt",
        )
        if os.path.exists(releaseDescriptionFilePath):
            print(
                "Can't create release description because '%s' already exists!"
                % releaseDescriptionFilePath
            )
            return

        torrentName = "PTP " + self.ReleaseName + ".torrent"
        torrentPath = os.path.join(self.WorkingDirectory, torrentName)
        if createTorrent and os.path.exists(torrentPath):
            print("Can't create torrent because '%s' already exists!" % torrentPath)
            return

        # Save the release description.
        self.SaveReleaseDescriptionFile(
            logger, releaseDescriptionFilePath, createScreens
        )

        # Create the torrent
        if createTorrent:
            Mktor.Make(logger, self.Path, torrentPath)
            MyGlobals.GetTorrentClient().AddTorrentSkipHashCheck(
                logger, torrentPath, self.TorrentDataPath
            )


def run():
    parser = argparse.ArgumentParser(
        description="PtpUploader Release Description Maker by TnS"
    )

    parser.add_argument(
        "--notorrent", action="store_true", help="skip creating and seeding the torrent"
    )
    parser.add_argument(
        "--noscreens",
        action="store_true",
        help="skip creating and uploading screenshots",
    )
    parser.add_argument("path", nargs=1, help="The file or directory to use")

    args = parser.parse_args()

    Settings.LoadSettings()
    MyGlobals.InitializeGlobals(Settings.WorkingPath)

    releaseInfoMaker = ReleaseInfoMaker(args.path[0])
    releaseInfoMaker.MakeReleaseInfo(
        createTorrent=(not args.notorrent), createScreens=(not args.noscreens)
    )


if __name__ == "__main__":
    run()
