from MyGlobals import MyGlobals
from PtpUploaderException import PtpUploaderException;
from Settings import Settings;

from pyrocore.util import bencode, load_config, metafile;
from pyrocore import config;

import os;
import shutil;
import subprocess;
import time;
import xmlrpclib;

class Rtorrent:
	def __init__(self):
		MyGlobals.Logger.info( "Initializing PyroScope." )
				
		load_config.ConfigLoader().load()
		self.proxy = config.engine.open()

	# downloadPath is the final path. Suggested directory name from torrent won't be added to it.
	# Returns with the info hash of the torrent.
	def AddTorrent(self, logger, torrentPath, downloadPath):
		logger.info( "Initiating the download of torrent '%s' with rTorrent to '%s'." % ( torrentPath, downloadPath ) );
		
		file = open( torrentPath, "rb" );
		contents = xmlrpclib.Binary( file.read() );
		file.close();
		
		torrentData = bencode.bread( torrentPath ); 
		metafile.check_meta( torrentData );
		infoHash = metafile.info_hash( torrentData );
		
		self.proxy.load_raw( contents );
		self.proxy.d.set_directory_base( infoHash, downloadPath );
		self.proxy.d.start( infoHash );
		
		return infoHash;

	# Fast resume file is created beside the source torrent with "fast resume " prefix.
	# downloadPath must already contain the data.
	# downloadPath is the final path. Suggested directory name from torrent won't be added to it.
	# Returns with the info hash of the torrent.
	def AddTorrentSkipHashCheck(self, logger, torrentPath, downloadPath):
		logger.info( "Adding torrent '%s' without hash checking to rTorrent to '%s'." % ( torrentPath, downloadPath ) );		
		
		sourceDirectory, sourceFilename = os.path.split( torrentPath );
		sourceFilename = "fast resume " + sourceFilename;
		destinationTorrentPath = os.path.join( sourceDirectory, sourceFilename );
		shutil.copyfile( torrentPath, destinationTorrentPath );
		
		args = [ Settings.ChtorPath, "-H", downloadPath, destinationTorrentPath ];
		errorCode = subprocess.call( args );
		if errorCode != 0:
			raise PtpUploaderException( "Process execution '%s' returned with error code '%s'." % ( args, errorCode ) );			
		
		return self.AddTorrent( logger, destinationTorrentPath, downloadPath );
		
	def IsTorrentFinished(self, logger, infoHash):
		# TODO: this try catch block is here because xmlrpclib throws an exception when it timeouts or when the torrent with the given info hash doesn't exists.
		# The latter error most likely will cause stuck downloads so we should add some logic here to cancel an upload. For example: if it haven't download a single byte in ten minutes we can cancel it.

		try:
			# TODO: not the most sophisticated way.
			# Even a watch dir with Pyinotify would be better probably. rTorrent could write the info hash to a directory watched by us. 
			completed = self.proxy.d.get_complete( infoHash );
			return completed == 1
		except Exception:
			logger.exception( "Got exception while trying to check torrent's completion status. Info hash: '%s'." % infoHash );

		return False
	
	# rTorrent can't download torrents with fast resume information in them, so we clean the torrents before starting the download.
	# This can happen if the uploader uploaded the wrong torrent to the tracker.
	def CleanTorrentFile(self, logger, torrentPath):
		logger.info( "Cleaning torrent file '%s'." % torrentPath )		
		
		args = [ Settings.ChtorPath, "--clean", torrentPath ]
		errorCode = subprocess.call( args )
		if errorCode != 0:
			raise PtpUploaderException( "Process execution '%s' returned with error code '%s'." % ( args, errorCode ) )