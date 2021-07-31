from ..MyGlobals import MyGlobals
from ..PtpUploaderException import PtpUploaderException
from ..Settings import Settings

import transmissionrpc


class Transmission:
    def __init__(self, address, port):
        MyGlobals.Logger.info("Initializing transmissionrpc.")
        self.transmission = transmissionrpc.Client(address, port)

    # downloadPath is the final path. Suggested directory name from torrent won't be added to it.
    # Returns with the info hash of the torrent.
    def AddTorrent(self, logger=None, torrentPath=None, downloadPath=None):
        logger.info(
            "Initiating the download of torrent '%s' with Transmission to '%s'."
            % (torrentPath, downloadPath)
        )
        torrent = self.transmission.add_torrent(torrentPath, download_dir=downloadPath)
        return torrent.hashString

    # Transmission doesn't allow hash check skipping...
    def AddTorrentSkipHashCheck(self, logger, torrentPath, downloadPath):
        logger.info(
            "Adding torrent '%s' without hash checking (not really) to Transmission to '%s'."
            % (torrentPath, downloadPath)
        )
        hashString = self.AddTorrent(logger, torrentPath, downloadPath)
        return hashString

    def IsTorrentFinished(self, logger, infoHash):
        try:
            # TODO: not the most sophisticated way.
            # Even a watch dir with Pyinotify would be better probably. rTorrent could write the info hash to a directory watched by us.
            # completed = self.proxy.d.get_complete( infoHash );
            if self.transmission.get_torrent(infoHash).doneDate > 0:
                return True
        except Exception:
            logger.exception(
                "Got exception while trying to check torrent's completion status. Info hash: '%s'."
                % infoHash
            )

        return False

    # It doesn't delete the data.
    def DeleteTorrent(self, logger, infoHash):
        try:
            self.transmission.stop_torrent(infoHash)
            self.transmission.remove_torrent(infoHash, delete_data=False)
        except Exception:
            logger.exception(
                "Got exception while trying to delete torrent. Info hash: '%s'."
                % infoHash
            )

    # Transmission doesn't have any problems with this.. so just skip
    def CleanTorrentFile(self, logger, torrentPath):
        # logger.info( "Cleaning torrent file '%s'... nah" % torrentPath )
        pass
