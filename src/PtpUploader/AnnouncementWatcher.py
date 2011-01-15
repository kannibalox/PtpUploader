from Globals import Globals
from Logger import Logger
from PtpUploaderException import PtpUploaderException
from ReleaseInfo import ReleaseInfo
from Settings import Settings

import os
import re
		
class AnnouncementWatcher:
	# Example: [source=gft][id=44][title=Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS]
	@staticmethod
	def __ParseAnnouncementFile(sourceFactory, announcementFilePath):
		announcementFilename = os.path.basename( announcementFilePath ) # Get the filename.
		
		matches = re.match( r"\[source=(.+)\]\[id=(\d+)\]\[title=(.+)\]", announcementFilename )			
		if not matches:
			Globals.Logger.info( "Invalid announcement name format: '%s'." % announcementFilename )
			return None
			
		announcementSourceName = matches.group( 1 )
		announcementId = matches.group( 2 )
		releaseName = matches.group( 3 )
			
		announcementSource = sourceFactory.GetSource( announcementSourceName )
		if announcementSource is None:
			Globals.Logger.error( "Unknown announcement source: '%s'." % announcementSourceName )
			return None

		announcementLogFilePath = os.path.join( Settings.GetAnnouncementLogPath(), announcementFilename )
		logger = Logger( announcementLogFilePath )
		return ReleaseInfo( announcementFilePath, announcementSource, announcementId, releaseName, logger )
	
	# No logging here because it would result in spamming.
	@staticmethod
	def __ReadAnnouncements(sourceFactory, announcementsPath):
		announcements = []

		entries = os.listdir( announcementsPath );
		files = [];
		for entry in entries:
			filePath = os.path.join( announcementsPath, entry );
			if os.path.isfile( filePath ):
				modificationTime = os.path.getmtime( filePath );
				item = modificationTime, filePath; # Add as a tuple.
				files.append( item );

		files.sort();
		for item in files:
			path = item[ 1 ]; # First element is the modification time, second is the path.
			releaseInfo = AnnouncementWatcher.__ParseAnnouncementFile( sourceFactory, path )
			if releaseInfo:
				announcements.append( releaseInfo );
			else:
				ReleaseInfo.MoveAnnouncement( path, Settings.GetProcessedAnnouncementPath() )
		
		return announcements
	
	@staticmethod
	def GetNewAnnouncements(sourceFactory):
		return AnnouncementWatcher.__ReadAnnouncements( sourceFactory, Settings.GetAnnouncementWatchPath() )
	
	@staticmethod
	def GetPendingAnnouncements(sourceFactory):
		return AnnouncementWatcher.__ReadAnnouncements( sourceFactory, Settings.GetPendingAnnouncementPath() )