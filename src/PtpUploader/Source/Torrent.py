from .SourceBase import SourceBase

from ..PtpUploaderException import PtpUploaderException
from ..ReleaseNameParser import ReleaseNameParser


class Torrent(SourceBase):
    def __init__(self):
        SourceBase.__init__(self)

        self.Name = "torrent"
        self.NameInSettings = "TorrentFileSource"

    def PrepareDownload(self, logger, releaseInfo):
        # TODO: support for uploads from torrent without specifying IMDb id and reading it from NFO. (We only get IMDb id when the download is finished.)

        # TODO: support for new movies without IMDB id
        if (not releaseInfo.HasImdbId()) and (not releaseInfo.HasPtpId()):
            raise PtpUploaderException("Doesn't contain IMDb ID.")

        releaseNameParser = ReleaseNameParser(releaseInfo.ReleaseName)
        releaseNameParser.GetSourceAndFormat(releaseInfo)
        if releaseNameParser.Scene:
            releaseInfo.SetSceneRelease()
