from Globals import Globals;
from PtpUploaderException import PtpUploaderException;
from Settings import Settings;

import os;
import subprocess;

# mktorrent is not working properly under Windows.
class MakeTorrent:
	@staticmethod
	def Make(path, torrentPath):
		Globals.Logger.info( "Making torrent from '%s' to '%s'." % ( path, torrentPath ) );
		sourceSize = MakeTorrent.GetSourceSize( path );

		# Optimal piece size should be automatically calculated by mktorrent...			
		# Use 512 KB piece size as default.
		# Use 4 MB piece size for torrents that are longer than 4 GB.
		pieceSize = "-l 19";
		if sourceSize > ( 4 * 1024 * 1024 * 1024 ):
			pieceSize = "-l 22";
		
		args = [ Settings.MktorrentPath, '-a', Settings.PtpAnnounceUrl, '-p', pieceSize, '-o', torrentPath, path ];
		errorCode = subprocess.call( args );
		if errorCode != 0:
			raise PtpUploaderException( "Process execution '%s' returned with error code '%s'." % ( args, errorCode ) );			

	@staticmethod
	def GetSourceSize(path):
		if os.path.isfile( path ):
			return os.path.getsize( path );
		
		totalSize = 0;
		for ( dirPath, dirNames, fileNames ) in os.walk( path ):
			for file in fileNames:
				filePath = os.path.join( dirPath, file );
				totalSize += os.path.getsize( filePath );

		return totalSize;

	