from ..Helper import GetPathSize
from ..PtpUploaderException import PtpUploaderException
from ..Settings import Settings

from pyrobase import bencode
from pyrocore.util import metafile

import os
import subprocess

# mktorrent is not working properly under Windows.
class MakeTorrent:
	@staticmethod
	def Make(logger, path, torrentPath):
		logger.info( "Making torrent from '%s' to '%s'." % ( path, torrentPath ) )
		
		if os.path.exists( torrentPath ):
			raise PtpUploaderException( "Can't create torrent because path '%s' already exists." % torrentPath )
		
		sourceSize = GetPathSize( path )

		# Optimal piece size should be automatically calculated by mktorrent...
		pieceSize = "-l 19" # 512 KB
		if sourceSize > ( 16 * 1024 * 1024 * 1024 ):
			pieceSize = "-l 24" # 16 MB
		elif sourceSize > ( 8 * 1024 * 1024 * 1024 ):
			pieceSize = "-l 23" # 8 MB
		elif sourceSize > ( 4 * 1024 * 1024 * 1024 ):
			pieceSize = "-l 22" # 4 MB
		elif sourceSize > ( 2 * 1024 * 1024 * 1024 ):
			pieceSize = "-l 21" # 2 MB
		elif sourceSize > ( 1 * 1024 * 1024 * 1024 ):
			pieceSize = "-l 20" # 1 MB

		args = [ Settings.MktorrentPath, '-a', Settings.PtpAnnounceUrl, '-p', pieceSize, '-o', torrentPath, path ]
		errorCode = subprocess.call( args )
		if errorCode != 0:
			args[ 2 ] = "OMITTED" # Do not log the announce URL, so it less likely gets posted in the forums.
			raise PtpUploaderException( "Process execution '%s' returned with error code '%s'." % ( args, errorCode ) )

		# Torrents with exactly the same content and piece size get the same info hash regardless of the announcement URL.
		# To make sure that our new torrent will have unique info hash we add a unused key to the info section of the metadata.
		# Another way would be to use a different piece size, but this solution is much more elegant.
		# See: http://wiki.theory.org/BitTorrentSpecification#Metainfo_File_Structure 
		metainfo = bencode.bread( torrentPath )
		metafile.assign_fields( metainfo, [ 'info.source=PTP' ] )
		bencode.bwrite( torrentPath, metainfo )
