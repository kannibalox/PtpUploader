from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.ReleaseNameParser import ReleaseNameParser
from PtpUploader.Source.SourceBase import SourceBase


class Torrent(SourceBase):
    def __init__(self):
        SourceBase.__init__(self)

        self.Name = "torrent"
        self.NameInSettings = "TorrentFileSource"

    def IsEnabled(self):
        return True

    def PrepareDownload(self, logger, releaseInfo):
        # TODO: support for uploads from torrent without specifying IMDb id and reading it from NFO. (We only get IMDb id when the download is finished.)

        # TODO: support for new movies without IMDB id
        if (not releaseInfo.ImdbId) and (not releaseInfo.PtpId):
            raise PtpUploaderException("Doesn't contain IMDb ID.")

        releaseNameParser = ReleaseNameParser(releaseInfo.ReleaseName)
        releaseNameParser.GetSourceAndFormat(releaseInfo)
        if releaseNameParser.Scene:
            releaseInfo.SetSceneRelease()
