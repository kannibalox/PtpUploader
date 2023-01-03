import os
import shutil
import time
import xmlrpc.client as xmlrpc_client

import pyrosimple

from pyrosimple.util.metafile import Metafile
from pyrosimple.util.rpc import HashNotFound

from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderException import PtpUploaderException


class Rtorrent:
    def __init__(self, address):
        MyGlobals.Logger.info("Initializing PyroScope.")
        if address:
            engine = pyrosimple.connect(address)
        else:
            engine = pyrosimple.connect()
        self.proxy = engine.open()

    # downloadPath is the final path. Suggested directory name from torrent won't be added to it.
    # Returns with the info hash of the torrent.
    def AddTorrent(self, logger, torrentPath, downloadPath):
        logger.info(
            "Initiating the download of torrent '%s' with rTorrent to '%s'."
            % (torrentPath, downloadPath)
        )

        metafile = Metafile.from_file(torrentPath)
        metafile.check_meta()

        contents = xmlrpc_client.Binary(metafile.bencode())
        infoHash = metafile.info_hash()

        self.proxy.load.raw_start(
            "",
            contents,
            f'd.directory_base.set="{downloadPath}"',
            "d.custom.set=ptpuploader,true",
        )

        # If load_raw is slow then set_directory_base throws an exception (Fault: <Fault -501: 'Could not find info-hash.'>),
        # so we retry adding the torrent some delay.
        maximumTries = 15
        while True:
            try:
                self.proxy.d.hash(infoHash)
                break
            except HashNotFound:
                if maximumTries > 1:
                    maximumTries -= 1
                    time.sleep(2)  # Two seconds.
                else:
                    raise

        return infoHash

    # Fast resume file is created beside the source torrent with "fast resume " prefix.
    # downloadPath must already contain the data.
    # downloadPath is the final path. Suggested directory name from torrent won't be added to it.
    # Returns with the info hash of the torrent.
    def AddTorrentSkipHashCheck(self, logger, torrentPath, downloadPath):
        logger.info(
            "Adding torrent '%s' without hash checking to rTorrent to '%s'."
            % (torrentPath, downloadPath)
        )

        sourceDirectory, sourceFilename = os.path.split(torrentPath)
        sourceFilename = "fast resume " + sourceFilename
        destinationTorrentPath = os.path.join(sourceDirectory, sourceFilename)

        if os.path.exists(destinationTorrentPath):
            raise PtpUploaderException(
                "Can't create fast resume torrent because path '%s' already exists."
                % destinationTorrentPath
            )

        shutil.copyfile(torrentPath, destinationTorrentPath)

        metafile = Metafile.from_file(destinationTorrentPath)
        metafile.add_fast_resume(downloadPath)
        metafile.save(destinationTorrentPath)

        infoHash = ""
        try:
            infoHash = self.AddTorrent(logger, destinationTorrentPath, downloadPath)
        finally:
            # We always remove the fast resume torrent regardless of result of adding the torrent to rTorrent.
            # This ensures that even if adding to rTorent fails, then resuming the job will work.
            os.remove(destinationTorrentPath)

        return infoHash

    def IsTorrentFinished(self, logger, infoHash):
        # TODO: this try catch block is here because xmlrpclib throws an exception when it timeouts or when the torrent with the given info hash doesn't exists.
        # The latter error most likely will cause stuck downloads so we should add some logic here to cancel an upload. For example: if it haven't download a single byte in ten minutes we can cancel it.

        try:
            # TODO: not the most sophisticated way.
            # Even a watch dir with Pyinotify would be better probably. rTorrent could write the info hash to a directory watched by us.
            return self.proxy.d.complete(infoHash) == 1
        except HashNotFound as e:
            raise e  # Raise this up to the web UI
        except Exception as e:
            logger.exception(
                "Got exception while trying to check torrent's completion status. hash: '%s', error: '%s'",
                infoHash,
                e,
            )

        return False

    # It doesn't delete the data.
    def DeleteTorrent(self, logger, infoHash):
        try:
            self.proxy.d.stop(infoHash)
            self.proxy.d.erase(infoHash)
        except Exception:
            logger.exception(
                "Got exception while trying to delete torrent. Info hash: '%s'."
                % infoHash
            )

    # rTorrent can't download torrents with fast resume information in them, so we clean the torrents before starting the download.
    # This can happen if the uploader uploaded the wrong torrent to the tracker.
    def CleanTorrentFile(self, logger, torrentPath):
        logger.info("Cleaning torrent file '%s'." % torrentPath)

        metafile = Metafile.from_file(torrentPath)
        metafile.clean_meta()
        metafile.save(torrentPath)
