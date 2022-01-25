import os

import bencode
from pyrosimple.util import metafile

from PtpUploader.Settings import Settings


def Make(logger, path, torrentPath):
    def callback(meta):
        meta["info"]["source"] = "PTP"

    logger.info("Making torrent from '%s' to '%s'." % (path, torrentPath))
    torrent = metafile.Metafile(torrentPath, datapath=path)

    if os.path.exists(torrentPath):
        with open(torrentPath, "rb") as fh:
            # Ignore the result of this method, we just want to check that files haven't changed/moved
            metafile.add_fast_resume(bencode.decode(fh.read()), path)
            logger.info("Using existing torrent file at '%s'.", torrentPath)
    else:
        logger.info("Making torrent from '%s' to '%s'.", path, torrentPath)
        torrent.create(
            path,
            Settings.PtpAnnounceUrl,
            created_by="PtpUploader",
            private=True,
            progress=None,
            callback=callback,
        )
