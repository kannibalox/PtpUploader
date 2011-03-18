from Job.CheckAnnouncement import CheckAnnouncement
from Job.Download import Download
from Job.Upload import Upload
from Source.SourceFactory import SourceFactory
from Tool.Rtorrent import Rtorrent

from AnnouncementWatcher import *
from Database import Database
from Logger import Logger # TODO: HACK

import Queue

class JobManager:
	def __init__(self):
		self.SourceFactory = SourceFactory()
		self.Rtorrent = Rtorrent()
		self.PendingAnnouncements = AnnouncementWatcher.GetPendingAnnouncements( self.SourceFactory ) # Contains ReleaseInfo
		self.PendingDownloads = [] # Contains ReleaseInfo
		self.DatabaseQueue = Queue.Queue() # Contains ReleaseInfo ids.
		
	def __IsSourceAvailable(self, source):
		runningDownloads = 0
		for releaseInfo in self.PendingDownloads:
			if releaseInfo.AnnouncementSource.Name == source.Name:
				runningDownloads += 1
		
		return runningDownloads < source.MaximumParallelDownloads

	def __GetAnnouncementFromPendingList(self):
		for announcementIndex in range( len( self.PendingAnnouncements ) ):
			if self.__IsSourceAvailable( self.PendingAnnouncements[ announcementIndex ].AnnouncementSource ):
				announcementToHandle = self.PendingAnnouncements.pop( announcementIndex )
				announcementToHandle.MoveToProcessed()
				return announcementToHandle

		return None
	
	# Get new announcements, check if we can process anything from it, and add the others to the pending list.		 
	def __ProcessNewAnnouncements(self):
		announcementToHandle = None
		newAnnouncements = AnnouncementWatcher.GetNewAnnouncements( self.SourceFactory )
		for announcementIndex in range( len( newAnnouncements ) ):
			announcement = newAnnouncements[ announcementIndex ]
			if ( not announcementToHandle ) and self.__IsSourceAvailable( announcement.AnnouncementSource ):
				announcementToHandle = announcement
				announcementToHandle.MoveToProcessed()
			else:
				announcement.MoveToPending()
				self.PendingAnnouncements.append( announcement )				

		return announcementToHandle 

	def __GetAnnouncementToProcess(self):
		# TODO: HACK
		
		# First check if we can process anything from the pending announcments.
		#announcementToHandle = self.__GetAnnouncementFromPendingList()
		#if announcementToHandle:
		#	return announcementToHandle

		#return self.__ProcessNewAnnouncements()
		
		if self.DatabaseQueue.empty():
			return None
		
		releaseInfoId = self.DatabaseQueue.get()
		releaseInfo = Database.DbSession.query( ReleaseInfo ).filter( ReleaseInfo.Id == releaseInfoId ).first()
		
		# TODO: HACK
		announcementLogFilePath = os.path.join( Settings.GetAnnouncementLogPath(), releaseInfo.ReleaseName )
		releaseInfo.Logger = Logger( announcementLogFilePath )
		
		# TODO: hack
		releaseInfo.AnnouncementSource = self.SourceFactory.GetSource( releaseInfo.AnnouncementSourceName )
		
		return releaseInfo
	
	def AddToPendingDownloads(self, releaseInfo):
		self.PendingDownloads.append( releaseInfo )

	def AddToDatabaseQueue(self, releaseInfoId):
		self.DatabaseQueue.put( releaseInfoId )
		
	def __GetFinishedDownloadToProcess(self):
		if len( self.PendingDownloads ) > 0:
			print "Pending downloads: %s" % len( self.PendingDownloads )
		
		# TODO: can we use a multicast RPC call get all the statuses in one call?
		for downloadIndex in range( len( self.PendingDownloads ) ):
			releaseInfo = self.PendingDownloads[ downloadIndex ]
			logger = releaseInfo.Logger
			if releaseInfo.IsManualDownload or self.Rtorrent.IsTorrentFinished( logger, releaseInfo.SourceTorrentInfoHash ):
				return self.PendingDownloads.pop( downloadIndex )

		return None
	
	# Returns true, if an announcement or a download has been processed.
	def ProcessJobs(self):
		# If there is a finished download, then upload it.
		releaseInfo = self.__GetFinishedDownloadToProcess()
		if releaseInfo is not None: 
			Upload.DoWork( releaseInfo, self.Rtorrent )
			Database.DbSession.commit() # TODO
			return True

		# If there is a new announcement, then check and start downloading it.
		releaseInfo = self.__GetAnnouncementToProcess()
		if releaseInfo is not None:
			if CheckAnnouncement.DoWork( releaseInfo ):
				Download.DoWork( releaseInfo, self, self.Rtorrent )

			return True

		return False