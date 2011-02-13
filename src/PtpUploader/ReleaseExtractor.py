from Globals import Globals
from PtpUploaderException import PtpUploaderException
from Settings import Settings
from Tool.Unrar import Unrar

import fnmatch
import os

class ReleaseExtractor:
	# Makes sure that path only contains video and subtitle files with supported extensions and no directories.
	# Return with a tuple of list of the video files and the number of total files.
	@staticmethod
	def ValidateDirectory(path):	
		videos = [];
		files = os.listdir( path );
		for file in files:
			filePath = os.path.join( path, file );
			if os.path.isdir( filePath ):
				raise PtpUploaderException( "Directory '%s' contains a directory '%s'." % ( path, file ) );
			elif Settings.HasValidVideoExtensionToUpload( filePath ):
				videos.append( filePath );
			elif not Settings.HasValidSubtitleExtensionToUpload( filePath ):
				raise PtpUploaderException( "File '%s' has unsupported extension." % filePath );
			
		return videos, len( files );

	@staticmethod
	def __ExtractDirectory(sourcePath, destinationPath):
		# Extract RARs.
		rars = Unrar.GetRars( sourcePath )
		for rar in rars:
			Unrar.Extract( rar, destinationPath )

		# Make hard link from supported files.
		files = os.listdir( sourcePath )
		for file in files:
			filePath = os.path.join( sourcePath, file );
			if os.path.isfile( filePath ) and ( Settings.HasValidVideoExtensionToUpload( filePath ) or Settings.HasValidSubtitleExtensionToUpload( filePath ) ):
				destinationFilePath = os.path.join( destinationPath, file )
				if os.path.exists( destinationFilePath ):
					raise PtpUploaderException( "Can't make link from file '%s' to '%s' because destination already exists." % ( filePath, destinationFilePath ) )

				os.link( filePath, destinationFilePath )

	# Extracts RAR files and creates hard links from supported files from the source to the destination directory.
	# Returns with the path of the NFO file or None.
	@staticmethod
	def Extract(sourcePath, destinationPath):
		nfoPath = None

		ReleaseExtractor.__ExtractDirectory( sourcePath, destinationPath )

		# Look for and extract common directories like CD1, CD2, etc. and the subtitle directory.
		entries = os.listdir( sourcePath )
		for entry in entries:
			entryPath = os.path.join( sourcePath, entry );
			entryLower = entry.lower()

			if os.path.isdir( entryPath ):
				if fnmatch.fnmatch( entryLower, "cd*" ):
					ReleaseExtractor.__ExtractDirectory( entryPath, destinationPath )
				elif entryLower == "sub" or entryLower == "subs" or entryLower == "subtitle" or entryLower == "subtitles":
					ReleaseExtractor.__ExtractDirectory( entryPath, destinationPath )
			elif os.path.isfile( entryPath ):
				if fnmatch.fnmatch( entryLower, "*.nfo" ):
					nfoPath = entryPath

		# Extract and delete RARs at the destination directory. Subtitles in scene releases usually are compressed twice. Yup, it is stupid.
		rars = Unrar.GetRars( destinationPath )
		for rar in rars:
			Unrar.Extract( rar, destinationPath )
			os.remove( rar )

		return nfoPath