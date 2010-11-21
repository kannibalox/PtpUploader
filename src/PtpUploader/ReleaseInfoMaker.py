from Source.Manual import Manual

from AnnouncementWatcher import *
from MakeTorrent import MakeTorrent
from MediaInfo import MediaInfo
from ReleaseInfo import ReleaseInfo
from Rtorrent import Rtorrent
from ScreenshotMaker import ScreenshotMaker
from Settings import Settings

import os

class ReleaseInfoMaker:
	def __init__(self, path):
		self.Path = path
		self.ReleaseName = None
		self.WorkingDirectory = None
		self.TorrentDataPath = None
		self.VideoFiles = []

	def CollectVideoFiles(self):
		if os.path.isdir( self.Path ):
			# Make sure that path doesn't ends with a trailing slash or else os.path.split would return with wrong values.
			self.Path = self.Path.rstrip( "\\/" )

			# If path is a directory we search for video files.
			files = os.listdir( self.Path );
			for file in files:
				filePath = os.path.join( self.Path, file );
				if os.path.isfile( filePath ) and Settings.HasValidVideoExtensionToUpload( filePath ):
					self.VideoFiles.append( filePath );

			if len( self.VideoFiles ) <= 0:
				print "Path '%s' doesn't contains any videos!" % self.Path
				return False

			# We use the parent directory of the path as the working directory.
			# Release name will be the directory's name. Eg. it will be "anything" for "/something/anything"
			self.WorkingDirectory, self.ReleaseName = os.path.split( self.Path )
			self.TorrentDataPath = self.Path
		elif os.path.isfile( self.Path ):
			self.VideoFiles.append( self.Path )
			
			# We use same the directory where the file is as the working directory.
			# Release name will be the file's name.
			self.WorkingDirectory, self.ReleaseName = os.path.split( self.Path )
			self.TorrentDataPath = self.WorkingDirectory
		else:
			print "Path '%s' doesn't exists!" % self.Path
			return False

		return True

	def MakeReleaseInfo(self, createTorrent):
		if not self.CollectVideoFiles():
			return
		
		# Make sure the files we are generating are not present.

		screenshotPath = os.path.join( self.WorkingDirectory, "screenshot.png" )
		if os.path.exists( screenshotPath ):
			print "Can't create screenshot because '%s' already exists!" % screenshotPath
			return
		
		releaseDescriptionFilePath = os.path.join( self.WorkingDirectory, "release description.txt" )
		if os.path.exists( releaseDescriptionFilePath ):
			print "Can't create release description because '%s' already exists!" % releaseDescriptionFilePath
			return

		torrentName = "PTP " + self.ReleaseName + ".torrent";
		torrentPath = os.path.join( self.WorkingDirectory, torrentName );
		if createTorrent and os.path.exists( torrentPath ):
			print "Can't create torrent because '%s' already exists!" % uploadTorrentPath
			return

		# Get the media info.
		mediaInfos = MediaInfo.ReadAndParseMediaInfos( self.VideoFiles )

		# Take and upload screenshots.
		uploadedScreenshots = ScreenshotMaker.TakeAndUploadScreenshots( self.VideoFiles[ 0 ], screenshotPath, mediaInfos[ 0 ].DurationInSec )

		# Make the release description.
		manualSource = Manual()
		announcement = Announcement( announcementFilePath = "", source = manualSource, id = "", self.ReleaseName )
		releaseInfo = ReleaseInfo( announcement, imdbId = "" )
		releaseInfo.PtpUploadInfo.FormatReleaseDescription( releaseInfo, uploadedScreenshots, mediaInfos, releaseDescriptionFilePath )

		# Create the torrent
		if createTorrent:
			MakeTorrent.Make( self.Path, torrentPath )
			rtorrent = Rtorrent()
			rtorrent.AddTorrentSkipHashCheck( torrentPath, self.TorrentDataPath )