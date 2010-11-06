from Globals import Globals;

import ConfigParser;
import fnmatch;
import os;

class Settings(object):
	@staticmethod
	def MakeListFromExtensionString(extensions):
		if len( extensions ) == 0:
			return [];
		
		extensions = extensions.replace( " ", "" );
		return extensions.split( "," );
	
	@staticmethod
	def HasValidExtensionToUpload(path, extensions):
		tempPath = path.lower();
		for extension in extensions:
			if fnmatch.fnmatch( tempPath, "*." + extension ):
				return True;
			
		return False;
	
	@staticmethod
	def HasValidVideoExtensionToUpload(path):
		return Settings.HasValidExtensionToUpload( path, Settings.VideoExtensionsToUpload );

	@staticmethod
	def HasValidSubtitleExtensionToUpload(path):
		return Settings.HasValidExtensionToUpload( path, Settings.SubtitleExtensionsToUpload );

	@staticmethod
	def GetAnnouncementWatchPath():
		return os.path.join( Settings.WorkingPath, "announcement" );

	@staticmethod
	def GetProcessedAnnouncementPath():
		return os.path.join( Settings.WorkingPath, "announcement/processed" );
		
	@staticmethod
	def LoadSettings():
		configParser = ConfigParser.ConfigParser();
		configParser.optionxform = str; # Make option names case sensitive.
		
		# Load Settings.ini from the same directory where PtpUploader is.
		settingsDirectory, moduleFilename = os.path.split( __file__ ); # __file__ contains the full path of the current running module
		settingsPath = os.path.join( settingsDirectory, "Settings.ini" );
		fp = open( settingsPath, "r" );
		configParser.readfp( fp );
		fp.close();
	
		Settings.VideoExtensionsToUpload = Settings.MakeListFromExtensionString( configParser.get( "Settings", "VideoExtensionsToUpload" ) );
		Settings.SubtitleExtensionsToUpload = Settings.MakeListFromExtensionString( configParser.get( "Settings", "SubtitleExtensionsToUpload" ) );
		Settings.PtpAnnounceUrl = configParser.get( "Settings", "PtpAnnounceUrl" );
		Settings.PtpUserName = configParser.get( "Settings", "PtpUserName" );
		Settings.PtpPassword = configParser.get( "Settings", "PtpPassword" );
		Settings.GftUserName = configParser.get( "Settings", "GftUserName" );
		Settings.GftPassword = configParser.get( "Settings", "GftPassword" );
		Settings.ImgurApiKey = configParser.get( "Settings", "ImgurApiKey" );

		Settings.ChtorPath = configParser.get( "Settings", "ChtorPath" );
		Settings.FfmpegPath = configParser.get( "Settings", "FfmpegPath" );
		Settings.MediaInfoPath = configParser.get( "Settings", "MediaInfoPath" );
		Settings.MktorrentPath = configParser.get( "Settings", "MktorrentPath" );
		Settings.UnrarPath = configParser.get( "Settings", "UnrarPath" );
		
		Settings.WorkingPath = configParser.get( "Settings", "WorkingPath" );
		
		Settings.AllowRelease = Settings.MakeListFromExtensionString( configParser.get( "Settings", "AllowRelease" ) );
		Settings.IgnoreRelease = Settings.MakeListFromExtensionString( configParser.get( "Settings", "IgnoreRelease" ) );
		Settings.IgnoreReleaseTag = Settings.MakeListFromExtensionString( configParser.get( "Settings", "IgnoreReleaseTag" ) );
		Settings.IgnoreReleaserGroup = Settings.MakeListFromExtensionString( configParser.get( "Settings", "IgnoreReleaserGroup" ) );

		# Create the announcement directory.
		# Because the processed announcement directory is within the announcement directory, we don't need to create the announcement directory separately.
		processedAnnouncementPath = Settings.GetProcessedAnnouncementPath();
		if not os.path.exists( processedAnnouncementPath ):
			os.makedirs( processedAnnouncementPath );