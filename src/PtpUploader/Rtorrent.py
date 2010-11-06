from Globals import Globals;
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
		Globals.Logger.info( "Initializing PyroScope." );
				
		load_config.ConfigLoader().load();
		self.proxy = config.engine.open();
	
	# downloadPath is the final path. Suggested directory name from torrent won't be added to it.
	# Returns with the info hash of the torrent.
	def AddTorrent(self, torrentPath, downloadPath):
		Globals.Logger.info( "Initiating the download of torrent '%s' with rTorrent to '%s'." % ( torrentPath, downloadPath ) );
		
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
					
	# downloadPath is the final path. Suggested directory name from torrent won't be added to it.
	def AddTorrentAndWaitTillDownloadFinishes(self, torrentPath, downloadPath):
		infoHash = self.AddTorrent( torrentPath, downloadPath );
		
		# TODO: not the most sophisticated way.
		# Even a watch dir with Pyinotify would be better probably. rTorrent could write the info hash to a directory watched by us. 
		Globals.Logger.info( "Waiting till rTorrent finishes downloading torrent with info hash '%s'." % infoHash );
		while True:
			time.sleep( 30 ); # Sleep 30 seconds between polls.
			completed = self.proxy.d.get_complete( infoHash );
			if completed == 1:
				break;
			
	# Fast resume file is created beside the source torrent with "fast resume " prefix.
	# downloadPath must already contain the data.
	# downloadPath is the final path. Suggested directory name from torrent won't be added to it.
	def AddTorrentSkipHashCheck(self, torrentPath, downloadPath):
		Globals.Logger.info( "Adding torrent '%s' without hash checking to rTorrent to '%s'." % ( torrentPath, downloadPath ) );		
		
		sourceDirectory, sourceFilename = os.path.split( torrentPath );
		sourceFilename = "fast resume " + sourceFilename;
		destinationTorrentPath = os.path.join( sourceDirectory, sourceFilename );
		shutil.copyfile( torrentPath, destinationTorrentPath );
		
		args = [ Settings.ChtorPath, "-H", downloadPath, destinationTorrentPath ];
		errorCode = subprocess.call( args );
		if errorCode != 0:
			raise PtpUploaderException( "Process execution '%s' returned with error code '%s'." % ( args, errorCode ) );			
		
		self.AddTorrent( destinationTorrentPath, downloadPath );