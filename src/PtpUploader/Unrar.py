from PtpUploaderException import PtpUploaderException;
from Settings import Settings;

import fnmatch;
import os;
import subprocess;

# Supported:
# - .rar
# - .001
# - .part01.rar
class Unrar:
	@staticmethod
	def Extract(rarPath, destinationPath):
		args = [ Settings.UnrarPath, 'x', rarPath, destinationPath ];
		errorCode = subprocess.call( args );
		if errorCode != 0:
			raise PtpUploaderException( "CProcess execution '%s' returned with error code '%s'." % ( args, errorCode ) );			

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