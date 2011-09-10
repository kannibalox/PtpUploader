from IncludedFileList import IncludedFileList
from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor

import os

class SourceBase:
	def LoadSettings(self, settings):
		self.Username = settings.GetDefault( self.NameInSettings, "Username", "" )
		self.Password = settings.GetDefault( self.NameInSettings, "Password", "" )
		self.AutomaticJobFilter = settings.GetDefault( self.NameInSettings, "AutomaticJobFilter", "" )

		# In case of invalid settings use the site's default.
		maximumParallelDownloads = int( settings.GetDefault( self.NameInSettings, "MaximumParallelDownloads", "0" ) )
		if maximumParallelDownloads > 0:
			self.MaximumParallelDownloads = maximumParallelDownloads

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