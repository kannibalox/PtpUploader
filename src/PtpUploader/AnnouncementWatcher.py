from Job.JobRunningState import JobRunningState

from Database import Database
from MyGlobals import MyGlobals
from Logger import Logger
from PtpUploaderException import PtpUploaderException
from ReleaseInfo import ReleaseInfo
from Settings import Settings

import datetime
import hashlib
import os
import re
		
class AnnouncementWatcher:
	@staticmethod
	def __SetScheduling( releaseInfo ):
		startDelay = 0

		if releaseInfo.AnnouncementSource.AutomaticJobStartDelay > 0:
			startDelay = releaseInfo.AnnouncementSource.AutomaticJobStartDelay

		# Cooperation.
		if ( releaseInfo.AnnouncementSource.AutomaticJobCooperationMemberCount > 1
			and releaseInfo.AnnouncementSource.AutomaticJobCooperationMemberId >= 0
			and releaseInfo.AnnouncementSource.AutomaticJobCooperationMemberId < releaseInfo.AnnouncementSource.AutomaticJobCooperationMemberCount
			and releaseInfo.AnnouncementSource.AutomaticJobCooperationDelay > 0
			and len( releaseInfo.ReleaseName ) > 0 ):

			# On some trackers the periods are stripped, so we strip everything here.
			releaseName = releaseInfo.ReleaseName.replace( ".", "" ).replace( "-", "" ).replace( " ", "" ).lower()

			# Give a release name an ID in the range of the number of cooperating users.
			id = int( hashlib.md5( releaseName ).hexdigest(), 16 )
			id = id % releaseInfo.AnnouncementSource.AutomaticJobCooperationMemberCount

			# Delaying is done justly.
			# For example let's assume three users are cooperating with 10 minutes delay.
			# If id = 0 then user #1:  0m, user #2: 10m, user #3: 20m.
			# If id = 1 then user #1: 20m, user #2:  0m, user #3: 10m.
			# If id = 2 then user #1: 10m, user #2: 20m, user #3:  0m.
			if releaseInfo.AnnouncementSource.AutomaticJobCooperationMemberId >= id:
				startDelay = ( releaseInfo.AnnouncementSource.AutomaticJobCooperationMemberId - id ) * releaseInfo.AnnouncementSource.AutomaticJobCooperationDelay
			else:
				startDelay = ( releaseInfo.AnnouncementSource.AutomaticJobCooperationMemberCount - id + releaseInfo.AnnouncementSource.AutomaticJobCooperationMemberId ) * releaseInfo.AnnouncementSource.AutomaticJobCooperationDelay

		if startDelay > 0:
			releaseInfo.JobRunningState = JobRunningState.Scheduled
			releaseInfo.ScheduleTimeUtc = datetime.datetime.utcnow() + datetime.timedelta( seconds = startDelay )

	# Example: [source=gft][id=44][title=Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS]
	@staticmethod
	def __ProcessAnnouncementFile(announcementFilename):
		matches = re.match( r"\[source=(.+?)\]\[id=(.+?)\]\[title=(.+)\]", announcementFilename )			
		if not matches:
			MyGlobals.Logger.info( "Invalid announcement name format: '%s'." % announcementFilename )
			return None
			
		announcementSourceName = matches.group( 1 )
		announcementId = matches.group( 2 )
		releaseName = matches.group( 3 ).strip()
			
		announcementSource = MyGlobals.SourceFactory.GetSource( announcementSourceName )
		if announcementSource is None:
			MyGlobals.Logger.error( "Unknown announcement source: '%s'." % announcementSourceName )
			return None
		
		releaseInfo = ReleaseInfo()
		releaseInfo.LastModificationTime = Database.MakeTimeStamp()
		releaseInfo.ReleaseName = releaseName
		releaseInfo.AnnouncementSource = announcementSource
		releaseInfo.AnnouncementSourceName = announcementSource.Name
		releaseInfo.AnnouncementId = announcementId
		AnnouncementWatcher.__SetScheduling( releaseInfo )

		Database.DbSession.add( releaseInfo )
		Database.DbSession.commit()

		# This must be after the commit because GetLogFilePath uses the Id.
		releaseInfo.Logger = Logger( releaseInfo.GetLogFilePath() )

		return releaseInfo
	
	# No logging here because it would result in spamming.
	@staticmethod
	def LoadAnnouncementFilesIntoTheDatabase():
		announcements = []

		announcementsPath = Settings.GetAnnouncementWatchPath()
		entries = os.listdir( announcementsPath )
		files = [];
		for entry in entries:
			# We can't do anything with undecodable filenames because we can't even join the paths (to move the file to the invalid directory) without getting an UnicodeDecodeError...
			# "Undecodable filenames will still be returned as string objects."
			# http://stackoverflow.com/questions/3409381/how-to-handle-undecodable-filenames-in-python
			if not isinstance( entry, unicode ):
				continue
			
			filePath = os.path.join( announcementsPath, entry )
			if os.path.isfile( filePath ):
				modificationTime = os.path.getmtime( filePath )
				item = modificationTime, filePath # Add as a tuple.
				files.append( item )

		files.sort()
		for item in files:
			path = item[ 1 ] # First element is the modification time, second is the path.
			filename = os.path.basename( path ) # Get the filename.
			releaseInfo = AnnouncementWatcher.__ProcessAnnouncementFile( filename )
			if releaseInfo is None:
				invalidFilePath = os.path.join( Settings.GetAnnouncementInvalidPath(), filename )
				os.rename( path, invalidFilePath )
			else:
				announcements.append( releaseInfo ) 
				os.remove( path )

		return announcements
