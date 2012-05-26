from Job.CheckAnnouncement import CheckAnnouncement
from Job.JobRunningState import JobRunningState
from Job.Upload import Upload
from Tool.Rtorrent import Rtorrent

from AnnouncementWatcher import *
from Database import Database
from Logger import Logger

import datetime
import Queue
import threading

class JobManagerItem:
	def __init__(self, releaseInfoId, releaseInfo):
		self.ReleaseInfoId = releaseInfoId # This will be accessed from another thread in case of stop request.
		self.ReleaseInfo = releaseInfo
		
		# So why this is not in ReleaseInfo? Because SQLAlchemy could possibly return with the same instance when restarting a canceled job.
		# This will be accessed from another thread in case of stop request.
		self.StopRequested = False

# All public methods are thread-safe.
# JobManager must be used from WorkerThread only (except the methods that state otherwise) because it deals with ReleaseInfo instances that can't pass thread boundaries because of SQLAlchemy.
# Both PendingAnnouncements and PendingDownloads gets modified from different thread than WorkerThread when cancelling a job so we use JobManagerItem.
# It makes the code really ugly...
class JobManager:
	def __init__(self):
		self.Lock = threading.RLock()
		self.Rtorrent = Rtorrent()
		self.PendingAnnouncements = [] # Contains JobManagerItem.
		self.PendingDownloads = [] # Contains JobManagerItem.
		
	def __IsSourceAvailable(self, source):
		# This is handled in CheckAnnouncement.
		if source is None:
			return True

		runningDownloads = 0
		for item in self.PendingDownloads:
			releaseInfo = self.__GetJobManagerItemAsReleaseInfo( item )
			if releaseInfo.AnnouncementSource.Name == source.Name:
				runningDownloads += 1
		
		return runningDownloads < source.MaximumParallelDownloads

	def __CanStartPendingJob( self, releaseInfo ):
		if releaseInfo.JobRunningState == JobRunningState.Scheduled and datetime.datetime.utcnow() < releaseInfo.ScheduleTimeUtc:
			return False

		return self.__IsSourceAvailable( releaseInfo.AnnouncementSource )

	def __LoadReleaseInfoFromDatabase(self, releaseInfoId):
		releaseInfo = Database.DbSession.query( ReleaseInfo ).filter( ReleaseInfo.Id == releaseInfoId ).first()
		releaseInfo.Logger = Logger( releaseInfo.GetLogFilePath() )
		releaseInfo.AnnouncementSource = MyGlobals.SourceFactory.GetSource( releaseInfo.AnnouncementSourceName )
		return releaseInfo
	
	def __GetJobManagerItemAsReleaseInfo(self, item):
		if item.ReleaseInfo is None:
			item.ReleaseInfo = self.__LoadReleaseInfoFromDatabase( item.ReleaseInfoId )
			return item.ReleaseInfo
		else:
			return item.ReleaseInfo

	def __GetAnnouncementToProcess(self):
		processIndex = -1
		
		# First check if we can process anything from the pending announcments.
		# Jobs with immediate start option have priority over other jobs.
		for announcementIndex in range( len( self.PendingAnnouncements ) ):
			jobManagerItem = self.PendingAnnouncements[ announcementIndex ]
			releaseInfo = self.__GetJobManagerItemAsReleaseInfo( jobManagerItem )
			if releaseInfo.IsStartImmediately():
				processIndex = announcementIndex
				break
			elif processIndex == -1 and self.__CanStartPendingJob( releaseInfo ):
				processIndex = announcementIndex

		if processIndex != -1:		
			return self.PendingAnnouncements.pop( processIndex )

		# Check if there is new automatic announcements in the watch directory.
		announcementToHandle = None
		releaseInfos = AnnouncementWatcher.LoadAnnouncementFilesIntoTheDatabase()
		for releaseInfo in releaseInfos: 
			jobManagerItem = JobManagerItem( releaseInfo.Id, releaseInfo )
			if ( not announcementToHandle ) and self.__CanStartPendingJob( releaseInfo ):
				announcementToHandle = jobManagerItem
			else:
				self.PendingAnnouncements.append( jobManagerItem )

		return announcementToHandle

	# Must be called from the WorkerThread because of ReleaseInfo.
	def AddToPendingDownloads(self, releaseInfo):
		self.Lock.acquire()		

		try:
			self.PendingDownloads.append( JobManagerItem( releaseInfo.Id, releaseInfo ) )
		finally:
			self.Lock.release()

	def __GetFinishedDownloadToProcess(self):
		if len( self.PendingDownloads ) > 0:
			print "Pending downloads: %s" % len( self.PendingDownloads )
		
		# TODO: can we use a multicast RPC call get all the statuses in one call?
		for downloadIndex in range( len( self.PendingDownloads ) ):
			jobManagerItem = self.PendingDownloads[ downloadIndex ]
			releaseInfo = self.__GetJobManagerItemAsReleaseInfo( jobManagerItem )
			logger = releaseInfo.Logger
			if releaseInfo.AnnouncementSource.IsDownloadFinished( logger, releaseInfo, self.Rtorrent ):
				return self.PendingDownloads.pop( downloadIndex )

		return None

	# Can be called from any thread.
	def StartJob(self, releaseInfoId):
		self.Lock.acquire()
		
		try:
			self.PendingAnnouncements.append( JobManagerItem( releaseInfoId, None ) )
		finally:
			self.Lock.release()

	def __StopJobInternal(self, releaseInfoId):
		# Iterate the list backwards because we may delete from it.
		for downloadIndex in reversed( xrange( len( self.PendingDownloads ) ) ):
			item = self.PendingDownloads[ downloadIndex ]
			if item.ReleaseInfoId == releaseInfoId or releaseInfoId == -1:
				self.__SetJobStopped( item.ReleaseInfoId )
				self.PendingDownloads.pop( downloadIndex )
		
		# Iterate the list backwards because we may delete from it.
		for announcementIndex in reversed( xrange( len( self.PendingAnnouncements ) ) ):
			item = self.PendingAnnouncements[ announcementIndex ]
			if item.ReleaseInfoId == releaseInfoId or releaseInfoId == -1:
				self.__SetJobStopped( item.ReleaseInfoId )
				self.PendingAnnouncements.pop( announcementIndex )
	
	def __SetJobStopped(self, releaseInfoId):
		# We have to get a new instance of ReleaseInfo because this function could come from another thread.
		releaseInfo = self.__LoadReleaseInfoFromDatabase( releaseInfoId )
		releaseInfo.JobRunningState = JobRunningState.Paused
		Database.DbSession.commit()

	# Can be called from any thread.
	def StopJob(self, releaseInfoId):
		self.Lock.acquire()

		try:
			self.__StopJobInternal( releaseInfoId )
		finally:
			self.Lock.release()

	# Must be called from the WorkerThread because of ReleaseInfo.
	def GetJobPhaseToProcess(self):
		self.Lock.acquire()

		try:
			# If there is a finished download, then upload it.
			jobManagerItem = self.__GetFinishedDownloadToProcess()
			if jobManagerItem is not None:
				return Upload( self, jobManagerItem, self.Rtorrent ) 
	
			# If there is a new announcement, then check and start downloading it.
			jobManagerItem = self.__GetAnnouncementToProcess()
			if jobManagerItem is not None:
				return CheckAnnouncement( self, jobManagerItem, self.Rtorrent )
			
			return None
		finally:
			self.Lock.release()