from Job.FinishedJobPhase import FinishedJobPhase
from Job.JobRunningState import JobRunningState

from Database import Database
from PtpUploaderException import *

import os

class Download:
	def __init__(self, releaseInfo, jobManager, rtorrent):
		self.ReleaseInfo = releaseInfo
		self.JobManager = jobManager
		self.Rtorrent = rtorrent

	def __CreateReleaseDirectory(self):
		if self.ReleaseInfo.IsJobPhaseFinished( FinishedJobPhase.Download_CreateReleaseDirectory ):
			return

		releaseRootPath = self.ReleaseInfo.GetReleaseRootPath()
		self.ReleaseInfo.Logger.info( "Creating release root directory at '%s'." % releaseRootPath )

		if os.path.exists( releaseRootPath ):
			raise PtpUploaderException( "Release root directory '%s' already exists." % releaseRootPath )	

		os.makedirs( releaseRootPath )

		self.ReleaseInfo.SetJobPhaseFinished( FinishedJobPhase.Download_CreateReleaseDirectory )
		Database.DbSession.commit()

	def __DownloadTorrentFile(self):
		if self.ReleaseInfo.IsSourceTorrentPathSet():
			return

		torrentName = self.ReleaseInfo.AnnouncementSource.Name + " " + self.ReleaseInfo.ReleaseName + ".torrent"
		sourceTorrentPath = os.path.join( self.ReleaseInfo.GetReleaseRootPath(), torrentName )
		self.ReleaseInfo.AnnouncementSource.DownloadTorrent( self.ReleaseInfo.Logger, self.ReleaseInfo, sourceTorrentPath )
		
		# Local variable is used temporarily to make sure that SourceTorrentPath is only gets stored in the database if DownloadTorrent succeeded. 
		self.ReleaseInfo.SourceTorrentPath = sourceTorrentPath
		Database.DbSession.commit()

	def __DownloadTorrent(self):
		if len( self.ReleaseInfo.SourceTorrentInfoHash ) > 0:
			return
		
		self.Rtorrent.CleanTorrentFile( self.ReleaseInfo.Logger, self.ReleaseInfo.SourceTorrentPath )
		self.ReleaseInfo.SourceTorrentInfoHash = self.Rtorrent.AddTorrent( self.ReleaseInfo.Logger, self.ReleaseInfo.SourceTorrentPath, self.ReleaseInfo.GetReleaseDownloadPath() )
		Database.DbSession.commit()
		
		self.JobManager.AddToPendingDownloads( self.ReleaseInfo )

	def Work(self):
		# Instead of this if, it would be possible to make a totally generic downloader system through SourceBase.
		if self.ReleaseInfo.AnnouncementSourceName == "file":
			self.ReleaseInfo.Logger.info( "Local directory or file is specified for release '%s', skipping download phase." % self.ReleaseInfo.ReleaseName )
			self.JobManager.AddToPendingDownloads( self.ReleaseInfo )			
			return True

		self.__CreateReleaseDirectory()
		self.__DownloadTorrentFile()
		self.__DownloadTorrent()
		
		return True

	@staticmethod
	def DoWork(releaseInfo, jobManager, rtorrent):
		try:
			download = Download( releaseInfo, jobManager, rtorrent )
			return download.Work()
		except Exception, e:
			releaseInfo.JobRunningState = JobRunningState.Failed
			Database.DbSession.commit()
			
			e.Logger = releaseInfo.Logger
			raise