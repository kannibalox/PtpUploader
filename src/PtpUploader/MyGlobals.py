from PtpSubtitle import PtpSubtitle

import cookielib
import datetime
import logging
import os
import sys
import uuid

class MyGlobalsClass:
	def __init__(self):
		self.CookieJar = None
		self.Logger = None
		self.PtpUploader = None
		self.SourceFactory = None
		self.PtpSubtitle = None
		self.TorrentClient = None

	def InitializeGlobals(self, workingPath):
		self.InitializeLogger( workingPath )
		self.CookieJar = cookielib.CookieJar()
		self.PtpSubtitle = PtpSubtitle()

		# The basic authentication based login wasn't always working on the upload for the AJAX torrent uploading.
		# It didn't send the Authentication header for some reason.
		# So instead of that we use this token based authentication there...
		# We can't use cookie based authenticatinon because PtpUploader is mostly used on shared host, and
		# unfortunately, cookies do not provide isolation by port ( http://stackoverflow.com/a/16328399 ).
		self.PostAuthToken = str( uuid.uuid1() ) + str( uuid.uuid4() )

	# workingPath from Settings.WorkingPath.
	def InitializeLogger(self, workingPath):
		# This will create the log directory too.
		announcementLogDirPath = os.path.join( workingPath, "log/announcement" )
		if not os.path.isdir( announcementLogDirPath ):
			os.makedirs( announcementLogDirPath )
		
		logDirPath = os.path.join( workingPath, "log" )

		logDate = datetime.datetime.now().strftime( "%Y.%m.%d. - %H_%M_%S" )
		logPath = os.path.join( logDirPath, logDate + ".txt" )
		
		self.Logger = logging.getLogger( 'PtpUploader' )
		
		# file
		handler = logging.FileHandler( logPath )
		formatter = logging.Formatter ( "[%(asctime)s] %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S" )
		handler.setFormatter( formatter )
		self.Logger.addHandler( handler )
		
		# stdout
		console = logging.StreamHandler( sys.stdout )
		console.setFormatter( formatter )
		self.Logger.addHandler( console )
		
		self.Logger.setLevel( logging.INFO )

	# Inline imports are used here to avoid unnecessary dependencies.
	def GetTorrentClient( self ):
		if self.TorrentClient is None:
			from Settings import Settings

			if Settings.TorrentClientName.lower() == "transmission":
				from Tool.Transmission import Transmission

				self.TorrentClient = Transmission( Settings.TorrentClientAddress, Settings.TorrentClientPort )
			else:
				from Tool.Rtorrent import Rtorrent

				self.TorrentClient = Rtorrent()

		return self.TorrentClient

MyGlobals = MyGlobalsClass()