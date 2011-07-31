from Source.SourceBase import SourceBase

from MyGlobals import MyGlobals
from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor
from ReleaseNameParser import ReleaseNameParser

import os

class File(SourceBase):
	UploadDirectoryName = "PTP"

	def __init__(self):
		self.Name = "file"
		self.MaximumParallelDownloads = 1
	
	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		if os.path.isdir( releaseInfo.GetReleaseDownloadPath() ):
			releaseInfo.SourceIsAFile = False
		elif os.path.isfile( releaseInfo.GetReleaseDownloadPath() ):
			releaseInfo.SourceIsAFile = True
		else:
			raise PtpUploaderException( "Source '%s' doesn't exist." % releaseInfo.GetReleaseDownloadPath() )

		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		releaseNameParser.GetSourceAndFormat( releaseInfo )
		if releaseNameParser.Scene: 
			releaseInfo.SetSceneRelease()
			
	@staticmethod
	def IsDownloadFinished(logger, releaseInfo, rtorrent):
		return True

	@staticmethod
	def GetCustomUploadPath(logger, releaseInfo):
		path = releaseInfo.GetReleaseDownloadPath()
		if releaseInfo.SourceIsAFile:
			# In case of single files the parent directory of the file will be the upload directory. 
			path, fileName = os.path.split( path )
		else:
			path = os.path.join( path, File.UploadDirectoryName )
			path = os.path.join( path, releaseInfo.ReleaseName )
			
		return path

	@staticmethod
	def CreateUploadDirectory(releaseInfo):
		if not releaseInfo.SourceIsAFile:
			SourceBase.CreateUploadDirectory( releaseInfo )
	
	@staticmethod
	def ExtractRelease(logger, releaseInfo):
		if not releaseInfo.SourceIsAFile:
			# Add the top level PTP directory to the ignore list because that is where we extract the release.
			topLevelDirectoriesToIgnore = [ File.UploadDirectoryName.lower() ]
			ReleaseExtractor.Extract( logger, releaseInfo.GetReleaseDownloadPath(), releaseInfo.GetReleaseUploadPath(), topLevelDirectoriesToIgnore )

	@staticmethod
	def ReadNfo(releaseInfo):
		if releaseInfo.SourceIsAFile:
			# Try to read the NFO with the same name as the video file but with nfo extension.
			basePath, fileName = os.path.split( releaseInfo.GetReleaseDownloadPath() )
			fileName, extension = os.path.splitext( fileName )
			nfoPath = os.path.join( basePath, fileName ) + ".nfo"
			if os.path.isfile( nfoPath ):
				releaseInfo.Nfo = NfoParser.ReadNfoFileToUnicode( nfoPath )
		else:
			SourceBase.ReadNfo( releaseInfo )

	@staticmethod
	def ValidateExtractedRelease(releaseInfo):
		if releaseInfo.SourceIsAFile:
			return [ releaseInfo.GetReleaseDownloadPath() ], []
		else:
			return SourceBase.ValidateExtractedRelease( releaseInfo )
	
	@staticmethod
	def GetTemporaryFolderForImagesAndTorrent(releaseInfo):
		if releaseInfo.SourceIsAFile:
			return releaseInfo.GetReleaseUploadPath()
		else:
			return os.path.join( releaseInfo.GetReleaseDownloadPath(), File.UploadDirectoryName )
	
	@staticmethod
	def IsSingleFileTorrentNeedsDirectory(releaseInfo):
		return not releaseInfo.SourceIsAFile