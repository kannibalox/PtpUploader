import os

from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import Settings
from pyrocore.util import metafile


def Make(logger, path, torrentPath):
    def Callback(meta):
        meta["info"]["source"] = "PTP"

    logger.info("Making torrent from '%s' to '%s'." % (path, torrentPath))
    torrent = metafile.Metafile(torrentPath, datapath=path)

    if os.path.exists(torrentPath):
        raise PtpUploaderException(
            "Can't create torrent because path '%s' already exists." % torrentPath
        )

    torrent.create(
        path,
        Settings.PtpAnnounceUrl,
        created_by="PtpUploader",
        private=True,
        progress=None,
        callback=Callback,
    )
