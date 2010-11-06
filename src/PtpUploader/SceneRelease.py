from Globals import Globals;
from NfoParser import NfoParser;
from PtpUploaderException import PtpUploaderException;
from Settings import Settings;
from Unrar import Unrar;

import fnmatch; 
import os;

class SceneRelease:
	def __init__(self, path):
		self.Path = path;
		self.Nfo = "";

	# return: value[ "cds" ] = CD1, CD2, ... if presents
	# value[ "subtitle" ] = subtitle directory if presents
	# value[ "nfo" ] = nfo path
	@staticmethod
	def GetImportantDirectories(path):
		cds = [];
		subtitle = None;
		nfoPath = None;
		
		entries = os.listdir( path );
		for entry in entries:
			entryPath = os.path.join( path, entry );
			entryLower = entry.lower();

			if os.path.isdir( entryPath ):
				if fnmatch.fnmatch( entryLower, "cd*" ):
					cds.append( entryPath );
				elif fnmatch.fnmatch( entryLower, "subs" ):
					subtitle = entryPath;
			elif os.path.isfile( entryPath ):
				if fnmatch.fnmatch( entryLower, "*.nfo" ):
					nfoPath = entryPath;
		
		return { "cds": cds, "subtitle": subtitle, "nfo": nfoPath };
	
	def ExtractVideos(self, cds, destination):
		if ( len( cds ) == 0 ):
			cds.append( self.Path );
		
		Globals.Logger.info( "Extracting videos from %s to '%s'." % ( cds, destination ) );
		
		for directory in cds:
			rars = Unrar.GetRars( directory );
			if len( rars ) == 1:
				Unrar.Extract( rars[ 0 ], destination );
			elif len( rars ) > 1:
				raise PtpUploaderException( "Directory '%s' contains more than one RAR." % directory );
			else:
				raise PtpUploaderException( "Directory '%s' doesn't contains any RAR files." % directory );
	
	# Subtitles may contain the uncut version too.
	def ExtractSubtitle(self, subtitlePath, destination):
		if subtitlePath is None:
			return;
				
		Globals.Logger.info( "Extracting subtitle from '%s' to '%s'." % ( subtitlePath, destination ) );
		
		rars = Unrar.GetRars( subtitlePath );
		if len( rars ) == 0:
			raise PtpUploaderException( "Subtitle directory '%s' exists but doesn't contains any RAR files." % subtitlePath );
		
		for rar in rars:
			Unrar.Extract( rar, destination );

		rars = Unrar.GetRars( destination );
		for rar in rars:
			Unrar.Extract( rar, destination );
			os.remove( rar );

	def Extract(self, destination):
		Globals.Logger.info( "Extracting release from '%s' to '%s'." % ( self.Path, destination ) );
		
		# Get the main files.
		directories = self.GetImportantDirectories( self.Path );
		cds = directories[ "cds" ];
		subtitleDirectory = directories[ "subtitle" ];
		nfoPath = directories[ "nfo" ];

		# Read the NFO file.
		if nfoPath is None:
			raise PtpUploaderException( "Can't find NFO in directory '%s'." % self.Path );
		
		self.Nfo = NfoParser.ReadNfoFileToUnicode( nfoPath ); 

		self.ExtractVideos( cds, destination );
		self.ExtractSubtitle( subtitleDirectory, destination );

		# Make sure it only contains video and subtitle files with supported extensions and no directories.
		videos = [];
		subtitles = [];
		files = os.listdir( destination );
		for file in files:
			filePath = os.path.join( destination, file );
			if os.path.isdir( filePath ):
				raise PtpUploaderException( "Directory '%s' contains a directory '%s'." % ( destination, file ) );
			elif Settings.HasValidVideoExtensionToUpload( filePath ):
				videos.append( filePath );
			elif Settings.HasValidSubtitleExtensionToUpload( filePath ):
				subtitles.append( filePath );
			else:
				raise PtpUploaderException( "File '%s' has unsupported extension." % filePath );