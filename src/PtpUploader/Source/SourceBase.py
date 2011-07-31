from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor

import os

class SourceBase:
	@staticmethod
	def IsEnabled():
		return True

	@staticmethod
	def Login():
		pass
	
	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		pass

	@staticmethod
	def CheckCoverArt(logger, releaseInfo):
		# If it exists on PTP then we don't need a cover.
		if ( not releaseInfo.IsCoverArtUrlSet() ) and ( not releaseInfo.HasPtpId() ):
			raise PtpUploaderException( "Cover art is not set." )

	@staticmethod
	def DownloadTorrent(logger, releaseInfo, path):
		pass
	
	@staticmethod
	def IsDownloadFinished(logger, releaseInfo, rtorrent):
		return rtorrent.IsTorrentFinished( logger, releaseInfo.SourceTorrentInfoHash )

	@staticmethod
	def GetCustomUploadPath(logger, releaseInfo):
		return ""

	@staticmethod
	def CreateUploadDirectory(releaseInfo):
		uploadDirectory = releaseInfo.GetReleaseUploadPath()
		releaseInfo.Logger.info( "Creating upload directory at '%s'." % uploadDirectory )
		
		if os.path.exists( uploadDirectory ):
			raise PtpUploaderException( "Upload directory '%s' already exists." % uploadDirectory )	

		os.makedirs( uploadDirectory )

	@staticmethod
	def ExtractRelease(logger, releaseInfo):
		ReleaseExtractor.Extract( logger, releaseInfo.GetReleaseDownloadPath(), releaseInfo.GetReleaseUploadPath() )

	@staticmethod
	def ReadNfo(releaseInfo):
		releaseInfo.Nfo = NfoParser.FindAndReadNfoFileToUnicode( releaseInfo.GetReleaseDownloadPath() )

	# Must returns with a tuple consisting of the list of video files and the list of additional files.
	@staticmethod
	def ValidateExtractedRelease(releaseInfo):
		videoFiles, additionalFiles = ReleaseExtractor.ValidateDirectory( releaseInfo.Logger, releaseInfo.GetReleaseUploadPath() )
		if len( videoFiles ) < 1:
			raise PtpUploaderException( "Upload path '%s' doesn't contains any video files." % releaseInfo.GetReleaseUploadPath() )

		return videoFiles, additionalFiles
	
	@staticmethod
	def GetTemporaryFolderForImagesAndTorrent(releaseInfo):
		return releaseInfo.GetReleaseRootPath() 

	@staticmethod
	def IsSingleFileTorrentNeedsDirectory(releaseInfo):
		return True
	
	@staticmethod
	def IncludeReleaseNameInReleaseDescription():
		return True

	@staticmethod
	def GetIdFromUrl(url):
		return ""

	@staticmethod
	def GetUrlFromId(id):
		return ""	