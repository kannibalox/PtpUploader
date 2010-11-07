from Globals import Globals;
from PtpUploaderException import PtpUploaderException;
from Settings import Settings;

import fnmatch; 
import os;

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

	# Creates hard links from all supported files from the source to the destination directory.
	# Used for non scene releases.
	@staticmethod
	def Extract(sourcePath, destinationPath):
		files = os.listdir( sourcePath );
		for file in files:
			filePath = os.path.join( sourcePath, file );
			if os.path.isdir( filePath ): # We ignore the directories.
				continue;
			elif Settings.HasValidVideoExtensionToUpload( filePath ) or Settings.HasValidSubtitleExtensionToUpload( filePath ):
				destinationFilePath = os.path.join( destinationPath, file );				
				os.link( filePath, destinationFilePath );