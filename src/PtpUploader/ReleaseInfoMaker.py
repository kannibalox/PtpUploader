from Source.Manual import Manual
from AnnouncementWatcher import *
from MediaInfo import MediaInfo
from ReleaseInfo import ReleaseInfo
from ScreenshotMaker import ScreenshotMaker

import os

class ReleaseInfoMaker:
	@staticmethod
	def MakeReleaseInfo(path):
		# TODO: add support for directories
		if not os.path.isfile( path ):
			print "File '%s' doesn't exists!" % path
			return

		releasePath = os.path.dirname( path )
		screenshotPath = os.path.join( releasePath, "screenshot.png" );
		if os.path.exists( screenshotPath ):
			print "Can't create screenshot because '%s' already exists!" % screenshotPath
			return
		
		releaseDescriptionFilePath = os.path.join( releasePath, "release description.txt" );
		if os.path.exists( releaseDescriptionFilePath ):
			print "Can't create release description because '%s' already exists!" % releaseDescriptionFilePath
			return

		videoFiles = [ path ]

		# Get the media info.
		mediaInfos = MediaInfo.ReadAndParseMediaInfos( videoFiles );

		# Take and upload screenshots.
		uploadedScreenshots = ScreenshotMaker.TakeAndUploadScreenshots( videoFiles[ 0 ], screenshotPath, mediaInfos[ 0 ].DurationInSec );

		# Make the release description.
		manualSource = Manual()
		announcement = Announcement( announcementFilePath = "", source = manualSource, id = "", releaseName = path )
		releaseInfo = ReleaseInfo( announcement, imdbId = "" ) 
		releaseInfo.PtpUploadInfo.FormatReleaseDescription( releaseInfo, uploadedScreenshots, mediaInfos, releaseDescriptionFilePath );