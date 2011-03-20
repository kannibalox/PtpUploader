from Job.JobRunningState import JobRunningState
from Tool.MakeTorrent import MakeTorrent
from Tool.MediaInfo import MediaInfo
from Tool.ScreenshotMaker import ScreenshotMaker

from Database import Database
from ImageUploader import ImageUploader
from Ptp import Ptp
from PtpUploaderException import *
from ReleaseExtractor import ReleaseExtractor
from Settings import Settings

import os
import subprocess

class Upload:
	def __init__(self, releaseInfo, rtorrent):
		self.ReleaseInfo = releaseInfo
		self.Rtorrent = rtorrent
		self.VideoFiles = []
		self.TotalFileCount = 0
		self.MediaInfos = []
		self.UploadedScreenshots = []
		self.ScaleSize = ""
		self.UploadTorrentPath = ""

	def __CreateUploadPath(self):
		self.ReleaseInfo.AnnouncementSource.RenameRelease( self.ReleaseInfo.Logger, self.ReleaseInfo )
		uploadPath = self.ReleaseInfo.GetReleaseUploadPath()
		self.ReleaseInfo.Logger.info( "Creating upload path at '%s'." % uploadPath )
		os.makedirs( uploadPath )

	def __ExtractRelease(self):
		self.ReleaseInfo.AnnouncementSource.ExtractRelease( self.ReleaseInfo.Logger, self.ReleaseInfo )
		self.VideoFiles, self.TotalFileCount = ReleaseExtractor.ValidateDirectory( self.ReleaseInfo.GetReleaseUploadPath() )
		if len( self.VideoFiles ) < 1:
			raise PtpUploaderException( "Upload path '%s' doesn't contains any video files." % self.ReleaseInfo.GetReleaseUploadPath() )

	def __GetMediaInfo(self):
		self.VideoFiles = ScreenshotMaker.SortVideoFiles( self.VideoFiles )
		self.MediaInfos = MediaInfo.ReadAndParseMediaInfos( self.ReleaseInfo.Logger, self.VideoFiles )
		self.ReleaseInfo.GetDataFromMediaInfo( self.MediaInfos[ 0 ] )

	def __TakeAndUploadScreenshots(self):
		screenshotPath = os.path.join( self.ReleaseInfo.GetReleaseRootPath(), "screenshot.png" )
		screenshotMaker = ScreenshotMaker( self.ReleaseInfo.Logger, self.VideoFiles[ 0 ] )
		self.UploadedScreenshots = screenshotMaker.TakeAndUploadScreenshots( screenshotPath, self.MediaInfos[ 0 ].DurationInSec )
		self.ScaleSize = screenshotMaker.ScaleSize 
		
	def __MakeReleaseDescription(self):
		releaseDescriptionFilePath = os.path.join( self.ReleaseInfo.GetReleaseRootPath(), "release description.txt" )
		includeReleaseName = self.ReleaseInfo.AnnouncementSource.IncludeReleaseNameInReleaseDescription() 
		self.ReleaseInfo.FormatReleaseDescription( self.ReleaseInfo.Logger, self.ReleaseInfo, self.UploadedScreenshots, self.ScaleSize, self.MediaInfos, includeReleaseName, releaseDescriptionFilePath )

	def __MakeTorrent(self):
		# We save it into a separate folder to make sure it won't end up in the upload somehow. :)
		uploadTorrentName = "PTP " + self.ReleaseInfo.ReleaseName + ".torrent"
		self.UploadTorrentPath = os.path.join( self.ReleaseInfo.GetReleaseRootPath(), uploadTorrentName )
		# Make torrent with the parent directory's name included if there is more than one file or requested by the source (it is a scene release).
		if self.TotalFileCount > 1 or self.ReleaseInfo.AnnouncementSource.IsSingleFileTorrentNeedsDirectory():
			MakeTorrent.Make( self.ReleaseInfo.Logger, self.ReleaseInfo.GetReleaseUploadPath(), self.UploadTorrentPath )
		else: # Create the torrent including only the single video file.
			MakeTorrent.Make( self.ReleaseInfo.Logger, self.VideoFiles[ 0 ], self.UploadTorrentPath )

	def __CheckIfExistsOnPtp(self):
		movieOnPtpResult = None

		# TODO: this is temporary here. We should support it everywhere.
		# If we are not logged in here that could mean that the download took a lot of time and the user got logged out for some reason. 
		Ptp.Login()

		if self.ReleaseInfo.HasPtpId():
			# If we already got the PTP id then we only need the existing formats if this not a forced upload.
			if not self.ReleaseInfo.IsForceUpload():
				movieOnPtpResult = Ptp.GetMoviePageOnPtp( self.ReleaseInfo.Logger, self.ReleaseInfo.PtpId )
		else:
			movieOnPtpResult = Ptp.GetMoviePageOnPtpByImdbId( self.ReleaseInfo.Logger, self.ReleaseInfo.GetImdbId() )
			self.ReleaseInfo.PtpId = movieOnPtpResult.PtpId
		
		if not self.ReleaseInfo.IsForceUpload():
			# If this is not a forced upload then we have to check (again) if is it already on PTP.
			existingRelease = movieOnPtpResult.IsReleaseExists( self.ReleaseInfo )
			if existingRelease is not None:
				self.ReleaseInfo.Logger.info( "Somebody has already uploaded the release '%s' to PTP while we were working on it. Skipping upload because of format '%s'." % ( self.ReleaseInfo.ReleaseName, existingRelease ) )
				return False
			
		return True

	def __RehostPoster(self):
		# If this movie has no page yet on PTP then we will need the cover, so we rehost the image to an image hoster.
		if self.ReleaseInfo.HasPtpId() or ( not self.ReleaseInfo.IsCoverArtUrlSet() ):
			return

		# Rehost the image only if not already on an image hoster.
		url = self.ReleaseInfo.CoverArtUrl
		if url.find( "ptpime.me" ) != -1 or url.find( "imageshack.us" ) != -1 or url.find( "photobucket.com" ) != -1:
			return

		self.ReleaseInfo.CoverArtUrl = ImageUploader.Upload( imageUrl = url )

	def __StartTorrent(self):
		# Add torrent without hash checking.
		self.Rtorrent.AddTorrentSkipHashCheck( self.ReleaseInfo.Logger, self.UploadTorrentPath, self.ReleaseInfo.GetReleaseUploadPath() )

	def __UploadMovie(self):
		self.ReleaseInfo.PtpId = Ptp.UploadMovie( self.ReleaseInfo.Logger, self.ReleaseInfo, self.UploadTorrentPath )
		self.ReleaseInfo.Logger.info( "'%s' has been successfully uploaded to PTP." % self.ReleaseInfo.ReleaseName )

	def __FinishUpload(self):
		self.ReleaseInfo.JobRunningState = JobRunningState.Finished
		Database.DbSession.commit()

		# Execute command on successful upload.
		if len( Settings.OnSuccessfulUpload ) <= 0:
			return

		uploadedTorrentUrl = "http://passthepopcorn.me/torrents.php?id=" + self.ReleaseInfo.PtpId
		command = Settings.OnSuccessfulUpload % { "releaseName": self.ReleaseInfo.ReleaseName, "uploadedTorrentUrl": uploadedTorrentUrl } 
		subprocess.Popen( command, shell = True )

	def Work(self):
		self.__CreateUploadPath()
		self.__ExtractRelease()
		self.__GetMediaInfo()
		self.__TakeAndUploadScreenshots()
		self.__MakeReleaseDescription()
		self.__MakeTorrent()
		
		if not self.__CheckIfExistsOnPtp():
			return False

		self.__RehostPoster()
		self.__StartTorrent()
		self.__UploadMovie()
		self.__FinishUpload()

		return True
	
	@staticmethod
	def DoWork(releaseInfo, rtorrent):
		try:
			upload = Upload( releaseInfo, rtorrent )
			return upload.Work()
		except Exception, e:
			releaseInfo.JobRunningState = JobRunningState.Failed
			Database.DbSession.commit()
			
			e.Logger = releaseInfo.Logger
			raise