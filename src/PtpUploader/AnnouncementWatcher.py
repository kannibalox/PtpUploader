from PtpUploaderException import PtpUploaderException;
from Settings import Settings;

import os;
import re;

class Announcement:
	# Example: [source=gft][id=44][title=Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS]
	def __init__(self, name):
		matches = re.match( r"\[source=(.+)\]\[id=(\d+)\]\[title=(.+)\]", name );			
		if matches:
			self.AnnouncementSourceName = matches.group( 1 );
			self.AnnouncementId = matches.group( 2 );
			self.ReleaseName = matches.group( 3 );
			self.IsManualDownload = self.AnnouncementSourceName == "manual";
			self.IsManualAnnouncement = self.IsManualDownload or self.ReleaseName == "ManualAnnouncement";
		else:
			raise PtpUploaderException( "Invalid announcement name format: '%s'." % name );
		
class AnnouncementWatcher:
	# No logging here because it would result in spamming.
	@staticmethod
	def GetAnnouncement():
		announcementWatchPath = Settings.GetAnnouncementWatchPath();
		entries = os.listdir( announcementWatchPath );
		files = [];
		for entry in entries:
			filePath = os.path.join( announcementWatchPath, entry );
			if os.path.isfile( filePath ):
				modificationTime = os.path.getmtime( filePath );
				item = modificationTime, filePath; # Add as a tuple.
				files.append( item );

		if len( files ) > 0:
			files.sort();
			item = files[ 0 ];
			path = item[ 1 ]; # First element is the modification time, second is the path.

			# Move the announcement file to the processed directory.
			# "On Unix, if dst exists and is a file, it will be replaced silently if the user has permission." -- this can happen in case of manual downloads.
			# TODO: what happens if the announcement file is not yet been closed? 
			announcementFilename = os.path.basename( path ); # Get the filename.
			processedAnnouncementFilePath = os.path.join( Settings.GetProcessedAnnouncementPath(), announcementFilename );
			os.rename( path, processedAnnouncementFilePath );

			return Announcement( announcementFilename );
		
		return None;