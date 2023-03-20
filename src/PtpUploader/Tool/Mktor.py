import os
from pathlib import Path
import re
from pathlib import Path
from typing import List, Optional

from pyrosimple.util.metafile import Metafile

from PtpUploader.Settings import config


def Make(logger, path, torrentPath, includedFileList: Optional[List[str]] = None):
    logger.info("Making torrent from '%s' to '%s'." % (path, torrentPath))

    ignore = []
    path = Path(path)
    print(includedFileList)
    if includedFileList:
        for subpath in path.rglob("*"):
            if not subpath.is_file():
                continue
            subpath = subpath.relative_to(path)
            print(subpath)
            if subpath not in includedFileList:
                print(str(subpath))
                ignore.append(re.compile('^'+str(subpath)+'$'))
    if os.path.exists(torrentPath):
        # We should be safe to allow the existing torrent to be used,
        # even when/if file selection is re-implemented, all the filesystem
        # manipulation has to be performed before we reach this API.
        # If it changes, at that point we can reset the torrentPath
        # and let it get rebuilt here.

        # Ignore the result of this method, we just want to check that files haven't changed/moved
        metafile = Metafile.from_file(torrentPath)
        metafile.add_fast_resume(path)
        logger.info("Using existing torrent file at '%s'.", torrentPath)
    else:
        logger.info("Making torrent from '%s' to '%s'.", path, torrentPath)
        print(ignore)
        metafile = Metafile.from_path(
            Path(path),
            config.ptp.announce_url,
            created_by="PtpUploader",
            private=True,
            progress=None,
            whitelist=includedFileList,
        )
        metafile["info"]["source"] = "PTP"
        metafile.save(Path(torrentPath))
