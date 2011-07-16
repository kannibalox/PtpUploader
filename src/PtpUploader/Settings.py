from MyGlobals import MyGlobals
from TagList import TagList

import codecs
import ConfigParser
import fnmatch
import os
import re

class Settings(object):
	@staticmethod
	def MakeListFromExtensionString(extensions):
		# Make sure everything is in lower case in the settings.
		extensions = extensions.lower()

		# If extensions is empty then we need an empty list. Splitting an empty string with a specified separator returns [''].
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
	def __HasValidExtensionToUpload(path, extensions):
		tempPath = path.lower()
		for extension in extensions:
			if fnmatch.fnmatch( tempPath, "*." + extension ):
				return True
			
		return False

	@staticmethod
	def HasValidVideoExtensionToUpload(path):
		return Settings.__HasValidExtensionToUpload( path, Settings.VideoExtensionsToUpload )

	@staticmethod
	def HasValidAdditionalExtensionToUpload(path):
		return Settings.__HasValidExtensionToUpload( path, Settings.AdditionalExtensionsToUpload )

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
	def GetAnnouncementInvalidPath():
		return os.path.join( Settings.WorkingPath, "announcement/invalid" )

	@staticmethod
	def GetJobLogPath():
		return os.path.join( Settings.WorkingPath, "log/job" )

	@staticmethod
	def GetTemporaryPath():
		return os.path.join( Settings.WorkingPath, "temporary" )

	@staticmethod
	def GetDatabaseFilePath():
		return os.path.join( Settings.WorkingPath, "database.sqlite" )

	@staticmethod
	def __LoadSceneGroups(path):
		groups = []
		file = open( path, "r" )
		for line in file:
			groupName = line.strip()
			if len( groupName ) > 0:
				groupName = groupName.lower()
				groups.append( groupName )
		file.close()
		return groups

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
		print "Loading settings from '%s'." % settingsPath # MyGlobals.Logger is not initalized yet. 
		fp = codecs.open( settingsPath, "r", "utf-8" )
		configParser.readfp( fp )
		fp.close()
		
		Settings.VideoExtensionsToUpload = Settings.MakeListFromExtensionString( configParser.get( "Settings", "VideoExtensionsToUpload" ) )
		Settings.AdditionalExtensionsToUpload = Settings.MakeListFromExtensionString( Settings.__GetDefault( configParser, "Settings", "AdditionalExtensionsToUpload", "bup, idx, ifo, srt, sub" ) )
		Settings.IgnoreFile = Settings.MakeListFromExtensionString( Settings.__GetDefault( configParser, "Settings", "IgnoreFile", "" ) )
		Settings.PtpAnnounceUrl = configParser.get( "Settings", "PtpAnnounceUrl" )
		Settings.PtpUserName = configParser.get( "Settings", "PtpUserName" )
		Settings.PtpPassword = configParser.get( "Settings", "PtpPassword" )
		Settings.GftUserName = Settings.__GetDefault( configParser, "Settings", "GftUserName", "" )
		Settings.GftPassword = Settings.__GetDefault( configParser, "Settings", "GftPassword", "" )
		Settings.GftMaximumParallelDownloads = int( Settings.__GetDefault( configParser, "Settings", "GftMaximumParallelDownloads", "1" ) )
		Settings.GftAutomaticJobFilter = Settings.__GetDefault( configParser, "Settings", "GftAutomaticJobFilter", "" )
		Settings.CinemageddonUserName = Settings.__GetDefault( configParser, "Settings", "CinemageddonUserName", "" )
		Settings.CinemageddonPassword = Settings.__GetDefault( configParser, "Settings", "CinemageddonPassword", "" )
		Settings.CinemageddonMaximumParallelDownloads = int( Settings.__GetDefault( configParser, "Settings", "CinemageddonMaximumParallelDownloads", "1" ) )
		Settings.CinematikUserName = Settings.__GetDefault( configParser, "Settings", "CinematikUserName", "" )
		Settings.CinematikPassword = Settings.__GetDefault( configParser, "Settings", "CinematikPassword", "" )
		Settings.CinematikMaximumParallelDownloads = int( Settings.__GetDefault( configParser, "Settings", "CinematikMaximumParallelDownloads", "1" ) )
		Settings.TorrentLeechUserName = Settings.__GetDefault( configParser, "Settings", "TorrentLeechUserName", "" )
		Settings.TorrentLeechPassword = Settings.__GetDefault( configParser, "Settings", "TorrentLeechPassword", "" )
		Settings.TorrentLeechMaximumParallelDownloads = int( Settings.__GetDefault( configParser, "Settings", "TorrentLeechMaximumParallelDownloads", "1" ) )
		Settings.TorrentLeechAutomaticJobFilter = Settings.__GetDefault( configParser, "Settings", "TorrentLeechAutomaticJobFilter", "" )
		Settings.TorrentFileSourceMaximumParallelDownloads = int( Settings.__GetDefault( configParser, "Settings", "TorrentFileSourceMaximumParallelDownloads", "3" ) )
		
		Settings.ImgurApiKey = Settings.__GetDefault( configParser, "Settings", "ImgurApiKey", "" )
		Settings.OnSuccessfulUpload = Settings.__GetDefault( configParser, "Settings", "OnSuccessfulUpload", "", raw = True )

		Settings.ChtorPath = configParser.get( "Settings", "ChtorPath" )
		Settings.FfmpegPath = Settings.__GetDefault( configParser, "Settings", "FfmpegPath", "" )
		Settings.MediaInfoPath = configParser.get( "Settings", "MediaInfoPath" )
		Settings.MplayerPath = Settings.__GetDefault( configParser, "Settings", "MplayerPath", "" )
		Settings.MktorrentPath = configParser.get( "Settings", "MktorrentPath" )
		Settings.UnrarPath = configParser.get( "Settings", "UnrarPath" )
		Settings.ImageMagickConvertPath = Settings.__GetDefault( configParser, "Settings", "ImageMagickConvertPath", "" ) 
		
		Settings.WorkingPath = configParser.get( "Settings", "WorkingPath" )
		
		Settings.AllowReleaseTag = Settings.MakeListOfListsFromString( Settings.__GetDefault( configParser, "Settings", "AllowReleaseTag", "" ) )
		Settings.IgnoreReleaseTag = Settings.MakeListOfListsFromString( Settings.__GetDefault( configParser, "Settings", "IgnoreReleaseTag", "" ) )
		Settings.IgnoreReleaseTagAfterYear = Settings.MakeListOfListsFromString( Settings.__GetDefault( configParser, "Settings", "IgnoreReleaseTagAfterYear", "" ) )
		Settings.IgnoreReleaserGroup = Settings.MakeListFromExtensionString( Settings.__GetDefault( configParser, "Settings", "IgnoreReleaserGroup", "" ) )
		Settings.SceneReleaserGroup = Settings.__LoadSceneGroups( os.path.join( settingsDirectory, "SceneGroups.txt" ) )

		Settings.WebServerAddress = Settings.__GetDefault( configParser, "Settings", "WebServerAddress", "" )
		Settings.WebServerUsername = Settings.__GetDefault( configParser, "Settings", "WebServerUsername", "admin" )
		Settings.WebServerPassword = Settings.__GetDefault( configParser, "Settings", "WebServerPassword", "" )
		
		Settings.TakeScreenshotOfAdditionalFiles = Settings.__GetDefault( configParser, "Settings", "TakeScreenshotOfAdditionalFiles", "" )
		Settings.TakeScreenshotOfAdditionalFiles = Settings.TakeScreenshotOfAdditionalFiles.lower() == "yes"
		Settings.SizeLimitForAutoCreatedJobs = float( Settings.__GetDefault( configParser, "Settings", "SizeLimitForAutoCreatedJobs", "0" ) ) * 1024 * 1024 * 1024
		Settings.StopIfCoverArtIsMissing = Settings.__GetDefault( configParser, "Settings", "StopIfCoverArtIsMissing", "" )

		# Create the announcement directory.
		# Invalid announcement directory is within the announcement directory, so we don't have to make the announcement directory separately.
		announcementPath = Settings.GetAnnouncementInvalidPath()
		if not os.path.exists( announcementPath ):
			os.makedirs( announcementPath )

		# Create the log directory.
		# Job log directory is within the log directory, so we don't have to make the log directory separately.
		jobLogPath = Settings.GetJobLogPath()
		if not os.path.exists( jobLogPath ):
			os.makedirs( jobLogPath )

		# Create the temporary directory.
		temporaryPath = Settings.GetTemporaryPath()
		if not os.path.exists( temporaryPath ):
			os.makedirs( temporaryPath )