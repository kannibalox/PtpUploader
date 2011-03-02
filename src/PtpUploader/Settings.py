from Globals import Globals
from TagList import TagList

import ConfigParser
import fnmatch
import os
import re

class Settings(object):
	@staticmethod
	def MakeListFromExtensionString(extensions):
		# Looks like Python's split is not working as one would except (and as its documentation says). 
		# "Splitting an empty string or a string consisting of just whitespace returns an empty list."
		extensions = extensions.strip() 
		if len( extensions ) > 0:
			list = extensions.split( "," )
			for i in range( len( list ) ):
				list[ i ] = list[ i ].strip()
				
			return list
		else:
			return []

	# This makes a list of TagList.
	# Eg.: "A B, C, D E" will become [ [ "A", "B" ], [ "C" ], [ "D", "E" ] ]
	@staticmethod
	def MakeListOfListsFromString(extensions):
		list = Settings.MakeListFromExtensionString( extensions )
		for i in range( len( list ) ):
			list[ i ] = TagList( list[ i ].split( " " ) ) 

		return list 
	
	@staticmethod
	def HasValidExtensionToUpload(path, extensions):
		tempPath = path.lower()
		for extension in extensions:
			if fnmatch.fnmatch( tempPath, "*." + extension ):
				return True
			
		return False

	@staticmethod
	def HasValidVideoExtensionToUpload(path):
		return Settings.HasValidExtensionToUpload( path, Settings.VideoExtensionsToUpload )

	@staticmethod
	def HasValidSubtitleExtensionToUpload(path):
		return Settings.HasValidExtensionToUpload( path, Settings.SubtitleExtensionsToUpload )

	@staticmethod
	def IsFileOnIgnoreList(path):
		path = os.path.basename( path ) # We only filter the filenames.
		path = path.lower()
		for ignoreFile in Settings.IgnoreFile:
			if re.match( ignoreFile, path ) is not None:
				return True;
		return False

	@staticmethod
	def GetAnnouncementWatchPath():
		return os.path.join( Settings.WorkingPath, "announcement" )

	@staticmethod
	def GetPendingAnnouncementPath():
		return os.path.join( Settings.WorkingPath, "announcement/pending" )

	@staticmethod
	def GetProcessedAnnouncementPath():
		return os.path.join( Settings.WorkingPath, "announcement/processed" )

	@staticmethod
	def GetAnnouncementLogPath():
		return os.path.join( Settings.WorkingPath, "log/announcement" )

	@staticmethod
	def __GetDefault(configParser, section, option, default, raw = False):
		try:
			return configParser.get( section, option, raw = raw )
  		except ConfigParser.NoOptionError:
  			return default

	@staticmethod
	def LoadSettings():
		configParser = ConfigParser.ConfigParser()
		configParser.optionxform = str # Make option names case sensitive.
		
		# Load Settings.ini from the same directory where PtpUploader is.
		settingsDirectory, moduleFilename = os.path.split( __file__ ) # __file__ contains the full path of the current running module
		settingsPath = os.path.join( settingsDirectory, "Settings.ini" )
		fp = open( settingsPath, "r" )
		configParser.readfp( fp )
		fp.close()
	
		Settings.VideoExtensionsToUpload = Settings.MakeListFromExtensionString( configParser.get( "Settings", "VideoExtensionsToUpload" ) )
		Settings.SubtitleExtensionsToUpload = Settings.MakeListFromExtensionString( configParser.get( "Settings", "SubtitleExtensionsToUpload" ) )
		Settings.IgnoreFile = Settings.MakeListFromExtensionString( Settings.__GetDefault( configParser, "Settings", "IgnoreFile", "" ) )
		Settings.PtpAnnounceUrl = configParser.get( "Settings", "PtpAnnounceUrl" )
		Settings.PtpUserName = configParser.get( "Settings", "PtpUserName" )
		Settings.PtpPassword = configParser.get( "Settings", "PtpPassword" )
		Settings.GftUserName = Settings.__GetDefault( configParser, "Settings", "GftUserName", "" )
		Settings.GftPassword = Settings.__GetDefault( configParser, "Settings", "GftPassword", "" )
		Settings.GftMaximumParallelDownloads = int( Settings.__GetDefault( configParser, "Settings", "GftMaximumParallelDownloads", "1" ) )
		Settings.CinemageddonUserName = Settings.__GetDefault( configParser, "Settings", "CinemageddonUserName", "" )
		Settings.CinemageddonPassword = Settings.__GetDefault( configParser, "Settings", "CinemageddonPassword", "" )
		Settings.CinemageddonMaximumParallelDownloads = int( Settings.__GetDefault( configParser, "Settings", "CinemageddonMaximumParallelDownloads", "1" ) )
		Settings.TorrentLeechUserName = Settings.__GetDefault( configParser, "Settings", "TorrentLeechUserName", "" )
		Settings.TorrentLeechPassword = Settings.__GetDefault( configParser, "Settings", "TorrentLeechPassword", "" )
		Settings.TorrentLeechMaximumParallelDownloads = int( Settings.__GetDefault( configParser, "Settings", "TorrentLeechMaximumParallelDownloads", "1" ) )
		
		Settings.ImgurApiKey = Settings.__GetDefault( configParser, "Settings", "ImgurApiKey", "" )
		Settings.OnSuccessfulUpload = Settings.__GetDefault( configParser, "Settings", "OnSuccessfulUpload", "", raw = True )

		Settings.ChtorPath = configParser.get( "Settings", "ChtorPath" )
		Settings.FfmpegPath = configParser.get( "Settings", "FfmpegPath" )
		Settings.MediaInfoPath = configParser.get( "Settings", "MediaInfoPath" )
		Settings.MktorrentPath = configParser.get( "Settings", "MktorrentPath" )
		Settings.UnrarPath = configParser.get( "Settings", "UnrarPath" )
		
		Settings.WorkingPath = configParser.get( "Settings", "WorkingPath" )
		
		Settings.AllowReleaseTag = Settings.MakeListOfListsFromString( Settings.__GetDefault( configParser, "Settings", "AllowReleaseTag", "" ) )
		Settings.IgnoreReleaseTag = Settings.MakeListOfListsFromString( Settings.__GetDefault( configParser, "Settings", "IgnoreReleaseTag", "" ) )
		Settings.IgnoreReleaseTagAfterYear = Settings.MakeListOfListsFromString( Settings.__GetDefault( configParser, "Settings", "IgnoreReleaseTagAfterYear", "" ) )
		Settings.IgnoreReleaserGroup = Settings.MakeListFromExtensionString( Settings.__GetDefault( configParser, "Settings", "IgnoreReleaserGroup", "" ) )
		Settings.SceneReleaserGroup = Settings.MakeListFromExtensionString( Settings.__GetDefault( configParser, "Settings", "SceneReleaserGroup", "" ) )

		# Create the announcement directory.
		# Because the processed announcement directory is within the announcement directory, we don't need to create the announcement directory separately.
		processedAnnouncementPath = Settings.GetProcessedAnnouncementPath()
		if not os.path.exists( processedAnnouncementPath ):
			os.makedirs( processedAnnouncementPath )

		# Create the pending announcement directory.
		pendingAnnouncementPath = Settings.GetPendingAnnouncementPath()
		if not os.path.exists( pendingAnnouncementPath ):
			os.makedirs( pendingAnnouncementPath )