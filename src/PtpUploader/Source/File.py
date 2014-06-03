from Source.SourceBase import SourceBase

from Helper import GetPathSize
from IncludedFileList import IncludedFileList
from MyGlobals import MyGlobals
from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor
from ReleaseNameParser import ReleaseNameParser

import os
import shutil

class File(SourceBase):
	UploadDirectoryName = "PTP"

	def __init__(self):
		SourceBase.__init__( self )

		self.Name = "file"
		self.NameInSettings = "FileSource"
	
	def PrepareDownload(self, logger, releaseInfo):
		path = releaseInfo.GetReleaseDownloadPath()
		
		if os.path.isdir( path ):
			releaseInfo.SourceIsAFile = False
		elif os.path.isfile( path ):
			releaseInfo.SourceIsAFile = True
		else:
			raise PtpUploaderException( "Source '%s' doesn't exist." % path )

		releaseInfo.Size = GetPathSize( path )

		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		releaseNameParser.GetSourceAndFormat( releaseInfo )
		if releaseNameParser.Scene: 
			releaseInfo.SetSceneRelease()
			
	def CheckFileList(self):
		pass

	def IsDownloadFinished( self, logger, releaseInfo, torrentClient ):
		return True

	def GetCustomUploadPath(self, logger, releaseInfo):
		path = releaseInfo.GetReleaseDownloadPath()
		if releaseInfo.SourceIsAFile:
			# In case of single files the parent directory of the file will be the upload directory. 
			path, fileName = os.path.split( path )
		else:
			path = os.path.join( path, File.UploadDirectoryName )
			path = os.path.join( path, releaseInfo.ReleaseName )
			
		return path

	def CreateUploadDirectory(self, releaseInfo):
		if not releaseInfo.SourceIsAFile:
			SourceBase.CreateUploadDirectory( self, releaseInfo )
	
	def ExtractRelease(self, logger, releaseInfo, includedFileList):
		if not releaseInfo.SourceIsAFile:
			# Add the top level PTP directory to the ignore list because that is where we extract the release.
			topLevelDirectoriesToIgnore = [ File.UploadDirectoryName.lower() ]
			ReleaseExtractor.Extract( logger, releaseInfo.GetReleaseDownloadPath(), releaseInfo.GetReleaseUploadPath(), includedFileList, topLevelDirectoriesToIgnore )

	def ReadNfo(self, releaseInfo):
		if releaseInfo.SourceIsAFile:
			# Try to read the NFO with the same name as the video file but with nfo extension.
			basePath, fileName = os.path.split( releaseInfo.GetReleaseDownloadPath() )
			fileName, extension = os.path.splitext( fileName )
			nfoPath = os.path.join( basePath, fileName ) + ".nfo"
			if os.path.isfile( nfoPath ):
				releaseInfo.Nfo = NfoParser.ReadNfoFileToUnicode( nfoPath )
		else:
			SourceBase.ReadNfo( self, releaseInfo )

	def ValidateExtractedRelease(self, releaseInfo, includedFileList):
		if releaseInfo.SourceIsAFile:
			return [ releaseInfo.GetReleaseDownloadPath() ], []
		else:
			return SourceBase.ValidateExtractedRelease( self, releaseInfo, includedFileList )
	
	def GetIncludedFileList(self, releaseInfo):
		includedFileList = IncludedFileList()

		path = releaseInfo.GetReleaseDownloadPath()
		if os.path.isdir( path ):
			includedFileList.FromDirectory( path )

		return includedFileList

	@staticmethod
	def __DeleteDirectoryWithoutTheUploadDirectory(path):
		if not os.path.isdir( path ):
			return

		entries = os.listdir( path )
		for entry in entries:
			if entry == UploadDirectoryName:
				continue

			absolutePath = os.path.join( path, entry )

			if os.path.isdir( absolutePath ):
				shutil.rmtree( absolutePath )
			elif os.path.isfile( absolutePath ):
				os.remove( absolutePath )

	def Delete( self, releaseInfo, torrentClient, deleteSourceData, deleteUploadData ):
		# We have to make sure to not to delete source if it is single file because no hard link is being made in this case.
		# Also see how GetCustomUploadPath works.
		sourceIsAFile = None
		path = releaseInfo.GetReleaseDownloadPath()
		if os.path.isdir( path ):
			sourceIsAFile = False
		elif os.path.isfile( path ):
			sourceIsAFile = True

		# Delete source folder without the PTP directory.
		if deleteSourceData:
			if sourceIsAFile == False:
				File.__DeleteDirectoryWithoutTheUploadDirectory( releaseInfo.GetReleaseDownloadPath() )

		if deleteUploadData:
			# Delete the uploaded torrent file.
			if releaseInfo.IsUploadTorrentFilePathSet() and os.path.isfile( releaseInfo.UploadTorrentFilePath ):
				os.remove( releaseInfo.UploadTorrentFilePath )

			# Delete the uploaded torrent from the torrent client.
			if len( releaseInfo.UploadTorrentInfoHash ) > 0:
				torrentClient.DeleteTorrent( releaseInfo.Logger, releaseInfo.UploadTorrentInfoHash )

			# Delete the data of the uploaded torrent.
			# If it is a single file then upload path is its parent directory, so it would be unfortunate to delete. (See GetCustomUploadPath.)
			if sourceIsAFile == False and os.path.isdir( releaseInfo.GetReleaseUploadPath() ):
				shutil.rmtree( releaseInfo.GetReleaseUploadPath() )

		if deleteSourceData and deleteUploadData:
			if sourceIsAFile == True:
				os.remove( releaseInfo.GetReleaseDownloadPath() )

	def GetTemporaryFolderForImagesAndTorrent(self, releaseInfo):
		if releaseInfo.SourceIsAFile:
			return releaseInfo.GetReleaseUploadPath()
		else:
			return os.path.join( releaseInfo.GetReleaseDownloadPath(), File.UploadDirectoryName )
	
	def IsSingleFileTorrentNeedsDirectory(self, releaseInfo):
		return not releaseInfo.SourceIsAFile
