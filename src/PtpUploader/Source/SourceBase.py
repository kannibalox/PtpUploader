from Job.FinishedJobPhase import FinishedJobPhase

from IncludedFileList import IncludedFileList
from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor
from Settings import Settings

import os
import shutil

class SourceBase:
	def __init__(self):
		self.MaximumParallelDownloads = 1

	def LoadSettings(self, settings):
		self.Username = settings.GetDefault( self.NameInSettings, "Username", "" )
		self.Password = settings.GetDefault( self.NameInSettings, "Password", "" )
		self.AutomaticJobFilter = settings.GetDefault( self.NameInSettings, "AutomaticJobFilter", "" )

		# Do not allow bogus settings.
		maximumParallelDownloads = int( settings.GetDefault( self.NameInSettings, "MaximumParallelDownloads", "1" ) )
		if maximumParallelDownloads > 0:
			self.MaximumParallelDownloads = maximumParallelDownloads

		self.StopAutomaticJob = settings.GetDefault( self.NameInSettings, "StopAutomaticJob", "" ).lower()
		self.StopAutomaticJobIfThereAreMultipleVideos = settings.GetDefault( self.NameInSettings, "StopAutomaticJobIfThereAreMultipleVideos", "" ).lower()

	def IsEnabled(self):
		return True

	def Login(self):
		pass

	def PrepareDownload(self, logger, releaseInfo):
		pass

	def CheckCoverArt(self, logger, releaseInfo):
		# If it exists on PTP then we don't need a cover.
		if ( not releaseInfo.IsCoverArtUrlSet() ) and ( not releaseInfo.HasPtpId() ):
			raise PtpUploaderException( "Cover art is not set." )

	def DownloadTorrent(self, logger, releaseInfo, path):
		pass

	# fileList must be an instance of IncludedFileList.
	def CheckFileList(self, releaseInfo, fileList):
		releaseInfo.Logger.info( "Checking the contents of the release." )

		if releaseInfo.IsDvdImage():
			return

		# Check if the release contains multiple non-ignored videos.
		numberOfVideoFiles = 0
		for file in fileList.Files:
			if file.IsIncluded() and Settings.HasValidVideoExtensionToUpload( file.Name ):
				numberOfVideoFiles += 1

		if numberOfVideoFiles > 1:
			raise PtpUploaderException( "Release contains multiple video files." )

	def IsDownloadFinished(self, logger, releaseInfo, rtorrent):
		return rtorrent.IsTorrentFinished( logger, releaseInfo.SourceTorrentInfoHash )

	def GetCustomUploadPath(self, logger, releaseInfo):
		return ""

	def CreateUploadDirectory(self, releaseInfo):
		uploadDirectory = releaseInfo.GetReleaseUploadPath()
		releaseInfo.Logger.info( "Creating upload directory at '%s'." % uploadDirectory )
		
		if os.path.exists( uploadDirectory ):
			raise PtpUploaderException( "Upload directory '%s' already exists." % uploadDirectory )	

		os.makedirs( uploadDirectory )

	def ExtractRelease(self, logger, releaseInfo, includedFileList):
		ReleaseExtractor.Extract( logger, releaseInfo.GetReleaseDownloadPath(), releaseInfo.GetReleaseUploadPath(), includedFileList )

	def ReadNfo(self, releaseInfo):
		releaseInfo.Nfo = NfoParser.FindAndReadNfoFileToUnicode( releaseInfo.GetReleaseDownloadPath() )

	# Must returns with a tuple consisting of the list of video files and the list of additional files.
	def ValidateExtractedRelease(self, releaseInfo, includedFileList):
		videoFiles, additionalFiles = ReleaseExtractor.ValidateDirectory( releaseInfo.Logger, releaseInfo.GetReleaseUploadPath(), includedFileList )
		if len( videoFiles ) < 1:
			raise PtpUploaderException( "Upload path '%s' doesn't contain any video files." % releaseInfo.GetReleaseUploadPath() )

		return videoFiles, additionalFiles

	def GetIncludedFileList(self, releaseInfo):
		includedFileList = IncludedFileList()
		
		if os.path.isfile( releaseInfo.SourceTorrentFilePath ):
			includedFileList.FromTorrent( releaseInfo.SourceTorrentFilePath )

		return includedFileList

	@staticmethod
	def __DeleteDirectoryIfEmpyOrContainsOnlyEmptyDirectories(path):
		if not os.path.isdir( path ):
			return

		for ( dirPath, dirNames, fileNames ) in os.walk( path ):
			for file in fileNames:
				return

		shutil.rmtree( path )

	def Delete(self, releaseInfo, rtorrent, deleteSourceData, deleteUploadData):
		# Only delete if the release directory has been created by this job.
		# (This is needed because of the releases with the same name. This way deleting the second one won't delete the release directory of the first.)
		if not releaseInfo.IsJobPhaseFinished( FinishedJobPhase.Download_CreateReleaseDirectory ):
			return

		if deleteSourceData:
			# Delete the source torrent file.
			if releaseInfo.IsSourceTorrentFilePathSet() and os.path.isfile( releaseInfo.SourceTorrentFilePath ):
				os.remove( releaseInfo.SourceTorrentFilePath )

			# Delete the source torrent from rTorrent.
			if len( releaseInfo.SourceTorrentInfoHash ) > 0:
				rtorrent.DeleteTorrent( releaseInfo.Logger, releaseInfo.SourceTorrentInfoHash )

			# Delete the data of the source torrent.
			if os.path.isdir( releaseInfo.GetReleaseDownloadPath() ):
				shutil.rmtree( releaseInfo.GetReleaseDownloadPath() )

		if deleteUploadData:
			# Delete the uploaded torrent file.
			if releaseInfo.IsUploadTorrentFilePathSet() and os.path.isfile( releaseInfo.UploadTorrentFilePath ):
				os.remove( releaseInfo.UploadTorrentFilePath )

			# Delete the uploaded torrent from rTorrent.
			if len( releaseInfo.UploadTorrentInfoHash ) > 0:
				rtorrent.DeleteTorrent( releaseInfo.Logger, releaseInfo.UploadTorrentInfoHash )

			# Delete the data of the uploaded torrent.
			if os.path.isdir( releaseInfo.GetReleaseUploadPath() ):
				shutil.rmtree( releaseInfo.GetReleaseUploadPath() )

		if deleteSourceData and deleteUploadData:
			SourceBase.__DeleteDirectoryIfEmpyOrContainsOnlyEmptyDirectories( releaseInfo.GetReleaseRootPath() )

		os.remove( releaseInfo.GetLogFilePath() )

	def GetTemporaryFolderForImagesAndTorrent(self, releaseInfo):
		return releaseInfo.GetReleaseRootPath() 

	def IsSingleFileTorrentNeedsDirectory(self, releaseInfo):
		return True
	
	def IncludeReleaseNameInReleaseDescription(self):
		return True

	def GetIdFromUrl(self, url):
		return ""

	def GetUrlFromId(self, id):
		return ""