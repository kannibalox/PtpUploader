from Job.FinishedJobPhase import FinishedJobPhase
from Job.JobRunningState import JobRunningState
from Job.WorkerBase import WorkerBase

from Database import Database
from PtpUploaderException import *

import os

class Download(WorkerBase):
	def __init__(self, releaseInfo, jobManager, rtorrent):
		WorkerBase.__init__( self, releaseInfo )
		
		self.JobManager = jobManager
		self.Rtorrent = rtorrent

	def __CreateReleaseDirectory(self):
		if self.ReleaseInfo.IsJobPhaseFinished( FinishedJobPhase.Download_CreateReleaseDirectory ):
			self.ReleaseInfo.Logger.info( "Release root path creation phase has been reached previously, not creating it again." )
			return

		releaseRootPath = self.ReleaseInfo.GetReleaseRootPath()
		self.ReleaseInfo.Logger.info( "Creating release root directory at '%s'." % releaseRootPath )

		if os.path.exists( releaseRootPath ):
			raise PtpUploaderException( "Release root directory '%s' already exists." % releaseRootPath )	

		os.makedirs( releaseRootPath )

		self.ReleaseInfo.SetJobPhaseFinished( FinishedJobPhase.Download_CreateReleaseDirectory )
		Database.DbSession.commit()

	def __DownloadTorrentFile(self):
		if self.ReleaseInfo.IsSourceTorrentFilePathSet():
			self.ReleaseInfo.Logger.info( "Source torrent file path is set, not download the file again." )
			return

		torrentName = self.ReleaseInfo.AnnouncementSource.Name + " " + self.ReleaseInfo.ReleaseName + ".torrent"
		sourceTorrentFilePath = os.path.join( self.ReleaseInfo.GetReleaseRootPath(), torrentName )
		self.ReleaseInfo.AnnouncementSource.DownloadTorrent( self.ReleaseInfo.Logger, self.ReleaseInfo, sourceTorrentFilePath )
		
		# Local variable is used temporarily to make sure that SourceTorrentFilePath is only gets stored in the database if DownloadTorrent succeeded. 
		self.ReleaseInfo.SourceTorrentFilePath = sourceTorrentFilePath
		Database.DbSession.commit()

	def __DownloadTorrent(self):
		if len( self.ReleaseInfo.SourceTorrentInfoHash ) > 0:
			self.ReleaseInfo.Logger.info( "Source torrent info hash is set, not starting torent again." )
		else:
			self.Rtorrent.CleanTorrentFile( self.ReleaseInfo.Logger, self.ReleaseInfo.SourceTorrentFilePath )
			self.ReleaseInfo.SourceTorrentInfoHash = self.Rtorrent.AddTorrent( self.ReleaseInfo.Logger, self.ReleaseInfo.SourceTorrentFilePath, self.ReleaseInfo.GetReleaseDownloadPath() )
			Database.DbSession.commit()

		self.JobManager.AddToPendingDownloads( self.ReleaseInfo )

	def Work(self):
		# Instead of this if, it would be possible to make a totally generic downloader system through SourceBase.
		if self.ReleaseInfo.AnnouncementSourceName == "file":
			self.ReleaseInfo.Logger.info( "Local directory or file is specified for release '%s', skipping download phase." % self.ReleaseInfo.ReleaseName )
			self.JobManager.AddToPendingDownloads( self.ReleaseInfo )			
			return

		self.__CreateReleaseDirectory()
		self.__DownloadTorrentFile()
		self.__DownloadTorrent()

	@staticmethod
	def DoWork(releaseInfo, jobManager, rtorrent):
		download = Download( releaseInfo, jobManager, rtorrent )
		download.WorkGuarded()