from Globals import Globals
from PtpUploaderException import PtpUploaderException
from Settings import Settings

import os;
import re;

class Announcement:
	# Example: [source=gft][id=44][title=Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS]
	def __init__(self, announcementFilePath, source, id, releaseName):
		self.AnnouncementFilePath = announcementFilePath;
		self.Source = source; # A class from the Source namespace.
		self.AnnouncementId = id;
		self.ReleaseName = releaseName;
		self.IsManualDownload = source.Name == "manual";
		self.IsManualAnnouncement = self.IsManualDownload or self.ReleaseName == "ManualAnnouncement";

	@staticmethod
	def ParseAnnouncementFile(sourceFactory, announcementFilePath):
		announcementFilename = os.path.basename( announcementFilePath ) # Get the filename.
		
		matches = re.match( r"\[source=(.+)\]\[id=(\d+)\]\[title=(.+)\]", announcementFilename )			
		if not matches:
			Globals.Logger.info( "Invalid announcement name format: '%s'." % announcementFilename )
			return None
			
		announcementSourceName = matches.group( 1 )
		announcementId = matches.group( 2 )
		releaseName = matches.group( 3 )
			
		source = sourceFactory.GetSource( announcementSourceName )
		if source is None:
			Globals.Logger.error( "Unknown announcement source: '%s'." % announcementSourceName )
			return None

		return Announcement( announcementFilePath, source, announcementId, releaseName )

	@staticmethod
	def MoveAnnouncement(announcementFilePath, targetDirectory):
		# Move the announcement file to the processed directory.
		# "On Unix, if dst exists and is a file, it will be replaced silently if the user has permission." -- this can happen in case of manual downloads.
		# TODO: what happens if the announcement file is not yet been closed? 
		announcementFilename = os.path.basename( announcementFilePath ); # Get the filename.
		targetAnnouncementFilePath = os.path.join( targetDirectory, announcementFilename );
		os.rename( announcementFilePath, targetAnnouncementFilePath );
		return targetAnnouncementFilePath
	
	def MoveToPending(self):
		self.AnnouncementFilePath = Announcement.MoveAnnouncement( self.AnnouncementFilePath, Settings.GetPendingAnnouncementPath() )

	def MoveToProcessed(self):
		self.AnnouncementFilePath = Announcement.MoveAnnouncement( self.AnnouncementFilePath, Settings.GetProcessedAnnouncementPath() )
		
class AnnouncementWatcher:
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
			announcement = Announcement.ParseAnnouncementFile( sourceFactory, path )
			if announcement:
				announcements.append( announcement );
			else:
				Announcement.MoveAnnouncement( path, Settings.GetProcessedAnnouncementPath() )
		
		return announcements
	
	@staticmethod
	def GetNewAnnouncements(sourceFactory):
		return AnnouncementWatcher.__ReadAnnouncements( sourceFactory, Settings.GetAnnouncementWatchPath() )
	
	@staticmethod
	def GetPendingAnnouncements(sourceFactory):
		return AnnouncementWatcher.__ReadAnnouncements( sourceFactory, Settings.GetPendingAnnouncementPath() )