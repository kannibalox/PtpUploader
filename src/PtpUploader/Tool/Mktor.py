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
        # We should be safe to allow the existing torrent to be used,
        # even when/if file selection is re-implemented, all the filesystem
        # manipulation has to be performed before we reach this API.
        # If it changes, at that point we can reset the torrentPath
        # and let it get rebuilt here.
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
