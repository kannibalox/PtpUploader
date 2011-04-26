from MyGlobals import MyGlobals
from PtpUploaderException import PtpUploaderException
from Settings import Settings
from Tool.Unrar import Unrar

import fnmatch
import os

class ReleaseExtractorInternal:
	def __init__(self, sourcePath, destinationPath, handleSceneFolders = False):
		self.SourcePath = sourcePath
		self.DestinationPath = destinationPath
		self.HandleSceneFolders = handleSceneFolders
		self.DestinationPathCreated = False

	def __MakeDestinationDirectory(self):
		if not self.DestinationPathCreated:
			if os.path.exists( self.DestinationPath ):
				if not os.path.isdir( self.DestinationPath ):
					raise PtpUploaderException( "Can't make destination directory '%s' because path already exists." % self.DestinationPath )
			else:
				os.makedirs( self.DestinationPath )

			self.DestinationPathCreated = True

		return self.DestinationPath

	def Extract(self):
		# Extract RARs.
		rars = Unrar.GetRars( self.SourcePath )
		for rar in rars:
			if not Settings.IsFileOnIgnoreList( rar ):
				Unrar.Extract( rar, self.__MakeDestinationDirectory() )

		entries = os.listdir( self.SourcePath )
		for entryName in entries:
			entryPath = os.path.join( self.SourcePath, entryName )
			if os.path.isdir( entryPath ):
				self.__HandleDirectory( entryName, entryPath )
			elif os.path.isfile( entryPath ):
				self.__HandleFile( entryName, entryPath )
		
	def __HandleDirectory(self, entryName, entryPath):
		entryLower = entryName.lower()
		if self.HandleSceneFolders and ( fnmatch.fnmatch( entryLower, "cd*" ) or entryLower == "sub" or entryLower == "subs" or entryLower == "subtitle" or entryLower == "subtitles" ):
			# Special scene folders in the root will be extracted without making a directory for them in the destination.
			releaseExtractor = ReleaseExtractorInternal( entryPath, self.DestinationPath )
			releaseExtractor.Extract()
		elif self.HandleSceneFolders and ( entryLower == "sample" or entryLower == "proof" ):
			# We don't need these.
			# (The if is nicer this way than combining this and the next block.)
			pass
		else:
			# Handle other directories normally.
			destinationDirectoryPath = os.path.join( self.DestinationPath, entryName )
			releaseExtractor = ReleaseExtractorInternal( entryPath, destinationDirectoryPath )
			releaseExtractor.Extract()

	def __HandleFile(self, entryName, entryPath):
		if Settings.IsFileOnIgnoreList( entryPath ):
			return

		if ( not Settings.HasValidVideoExtensionToUpload( entryPath ) ) and ( not Settings.HasValidAdditionalExtensionToUpload( entryPath ) ):
		 	return

		# Make hard link from supported files.
		destinationFilePath = os.path.join( self.__MakeDestinationDirectory(), entryName )
		if os.path.exists( destinationFilePath ):
			raise PtpUploaderException( "Can't make link from file '%s' to '%s' because destination already exists." % ( entryPath, destinationFilePath ) )

		os.link( entryPath, destinationFilePath )		

class ReleaseExtractor:
	# Makes sure that path only contains supported extensions.
	# Return with a tuple of list of the video files and the number of total files.
	@staticmethod
	def ValidateDirectory(logger, path):
		logger.info( "Validating directory '%s'." % path )
			
		videos = []
		fileCount = 0
		for root, dirs, files in os.walk( path ):
			for file in files:
				filePath = os.path.join( root, file )
				logger.info( "Found file '%s'." % filePath )
				fileCount += 1
				if Settings.HasValidVideoExtensionToUpload( filePath ):
					logger.info( "Found video file '%s'." % filePath )
					videos.append( filePath )
				elif not Settings.HasValidAdditionalExtensionToUpload( filePath ):
					raise PtpUploaderException( "File '%s' has unsupported extension." % filePath )

		return videos, fileCount

	# Extracts RAR files and creates hard links from supported files from the source to the destination directory.
	# Except of special scene folders (CD*, Subs) in the root, the directory hierarchy is kept.  
	@staticmethod
	def Extract(sourcePath, destinationPath):
		releaseExtractor = ReleaseExtractorInternal( sourcePath, destinationPath, handleSceneFolders = True )
		releaseExtractor.Extract()

		# Extract and delete RARs at the destination directory. Subtitles in scene releases usually are compressed twice. Yup, it is stupid.
		rars = Unrar.GetRars( destinationPath )
		for rar in rars:
			Unrar.Extract( rar, destinationPath )
			os.remove( rar )