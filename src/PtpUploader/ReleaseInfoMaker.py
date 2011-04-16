from Tool.MakeTorrent import MakeTorrent
from Tool.MediaInfo import MediaInfo
from Tool.Rtorrent import Rtorrent
from Tool.ScreenshotMaker import ScreenshotMaker

from MyGlobals import MyGlobals
from ReleaseDescriptionFormatter import ReleaseDescriptionFormatter
from ReleaseInfo import ReleaseInfo
from Settings import Settings

import codecs
import os
import sys

class ReleaseInfoMaker:
	def __init__(self, path):
		self.Path = path
		self.ReleaseName = None
		self.WorkingDirectory = None
		self.TorrentDataPath = None
		self.VideoFiles = []

	def CollectVideoFiles(self):
		self.Path = os.path.abspath( self.Path )
		
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

			self.VideoFiles = ScreenshotMaker.SortVideoFiles( self.VideoFiles )

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

	def SaveReleaseDescripionFile(self, logger, releaseDescriptionFilePath, screenshots, screenshotMaker, mediaInfos):
		releaseInfo = ReleaseInfo()
		releaseInfo.Logger = logger
		releaseInfo.ReleaseName = self.ReleaseName
		releaseInfo.SetScreenshotList( screenshots )
		releaseDescription = ReleaseDescriptionFormatter.Format( releaseInfo, screenshotMaker.ScaleSize, mediaInfos, includeReleaseName = True )

		releaseDescriptionFile = codecs.open( releaseDescriptionFilePath, encoding = "utf-8", mode = "w" )
		releaseDescriptionFile.write( releaseDescription )
		releaseDescriptionFile.close()

	def MakeReleaseInfo(self, createTorrent):
		logger = MyGlobals.Logger
		
		if not self.CollectVideoFiles():
			return
		
		# Make sure the files we are generating are not present.

		screenshotPath = os.path.join( self.WorkingDirectory, "screenshot" )
		screenshotPathWithExtension = screenshotPath + ".png"
		if os.path.exists( screenshotPathWithExtension ):
			print "Can't create screenshot because '%s' already exists!" % screenshotPathWithExtension
			return

		if len( Settings.ImageMagickConvertPath ) > 0:
			screenshotPathWithExtension = screenshotPath + ".jpg"
			if os.path.exists( screenshotPathWithExtension ):
				print "Can't create screenshot because '%s' already exists!" % screenshotPathWithExtension
				return
		
		releaseDescriptionFilePath = os.path.join( self.WorkingDirectory, "release description.txt" )
		if os.path.exists( releaseDescriptionFilePath ):
			print "Can't create release description because '%s' already exists!" % releaseDescriptionFilePath
			return

		torrentName = "PTP " + self.ReleaseName + ".torrent";
		torrentPath = os.path.join( self.WorkingDirectory, torrentName );
		if createTorrent and os.path.exists( torrentPath ):
			print "Can't create torrent because '%s' already exists!" % torrentPath
			return

		# Get the media info.
		mediaInfos = MediaInfo.ReadAndParseMediaInfos( logger, self.VideoFiles )

		# Take and upload screenshots.
		screenshotMaker = ScreenshotMaker( logger, self.VideoFiles[ 0 ] )
		screenshots = screenshotMaker.TakeAndUploadScreenshots( screenshotPath, mediaInfos[ 0 ].DurationInSec )

		# Save the release description.
		self.SaveReleaseDescripionFile( logger, releaseDescriptionFilePath, screenshots, screenshotMaker, mediaInfos )

		# Create the torrent
		if createTorrent:
			MakeTorrent.Make( logger, self.Path, torrentPath )
			rtorrent = Rtorrent()
			rtorrent.AddTorrentSkipHashCheck( logger, torrentPath, self.TorrentDataPath )

if __name__ == '__main__':
	print "PtpUploader Release Description Maker by TnS"
	print "Usage:"
	print "\"ReleaseInfoMaker.py <target directory or filename>\" creates the release description and starts seeding the torrent."
	print "\"ReleaseInfoMaker.py --notorrent <target directory or filename>\" creates the release description."
	print ""

	Settings.LoadSettings()
	MyGlobals.InitializeGlobals( Settings.WorkingPath )

	if len( sys.argv ) == 2:
		releaseInfoMaker = ReleaseInfoMaker( sys.argv[ 1 ] )
		releaseInfoMaker.MakeReleaseInfo( createTorrent = True )
	elif len( sys.argv ) == 3 and sys.argv[ 1 ] == "--notorrent":
		releaseInfoMaker = ReleaseInfoMaker( sys.argv[ 2 ] )
		releaseInfoMaker.MakeReleaseInfo( createTorrent = False )