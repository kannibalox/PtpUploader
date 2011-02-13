from PtpUploaderException import PtpUploaderException
from Settings import Settings

import fnmatch
import os
import subprocess
import uuid

# Supported:
# - .rar
# - .001
# - .part01.rar
class Unrar:
	# Because there is no easy way to tell if there will be an overwrite upon extraction, we make a temporary directory into the destination path then move the extracted files out of there.
	@staticmethod
	def Extract(rarPath, destinationPath):
		# Create the temporary folder.
		tempPath = os.path.join( destinationPath, str( uuid.uuid1() ) )
		if os.path.exists( tempPath ):
			raise PtpUploaderException( "Temporary path '%s' already exists." % tempPath )
		os.mkdir( tempPath )

		# Extract RAR to the temporary folder.
		args = [ Settings.UnrarPath, 'x', rarPath, tempPath ]
		errorCode = subprocess.call( args )
		if errorCode != 0:
			raise PtpUploaderException( "CProcess execution '%s' returned with error code '%s'." % ( args, errorCode ) )

		# Move everything out from the temporary folder to its destination.		
		files = os.listdir( tempPath )
		for file in files:
			tempFilePath = os.path.join( tempPath, file )
			destinationFilePath = os.path.join( destinationPath, file )
			if os.path.exists( destinationFilePath ):
				raise PtpUploaderException( "Can't move file '%s' to '%s' because destination already exists." % ( tempFilePath, destinationFilePath ) )				

			os.rename( tempFilePath, destinationFilePath )

		os.rmdir( tempPath )

	@staticmethod
	def IsFirstRar(path):
		path = path.lower();
		if fnmatch.fnmatch( path, "*.001" ):
			return True;
		
		if fnmatch.fnmatch( path, "*.rar" ):
			if fnmatch.fnmatch( path, "*.part01.rar" ) or fnmatch.fnmatch( path, "*.part001.rar" ):
				return True;
			if not fnmatch.fnmatch( path, "*.part*.rar" ):
				return True;

		return False;

	@staticmethod
	def GetRars(path):
		entries = os.listdir( path );
		files = [];
		
		for entry in entries:
			if Unrar.IsFirstRar( entry ):
				filePath = os.path.join( path, entry );
				if os.path.isfile( filePath ):
					files.append( filePath );

		return files;