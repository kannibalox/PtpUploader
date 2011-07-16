from Job.JobRunningState import JobRunningState

from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor
from Settings import Settings

class SourceBase:
	@staticmethod
	def IsEnabled():
		return True

	@staticmethod
	def Login():
		pass
	
	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		pass
	
	@staticmethod
	def CheckSizeLimit(logger, releaseInfo):
		if ( not releaseInfo.IsUserCreatedJob() ) and Settings.SizeLimitForAutomaticJobs > 0.0 and releaseInfo.Size > Settings.SizeLimitForAutomaticJobs:
			raise PtpUploaderException( JobRunningState.Ignored, "Ignored because of its size." )
		
	@staticmethod
	def DownloadTorrent(logger, releaseInfo, path):
		pass
	
	@staticmethod
	def IsDownloadFinished(logger, releaseInfo, rtorrent):
		return rtorrent.IsTorrentFinished( logger, releaseInfo.SourceTorrentInfoHash )

	@staticmethod
	def ExtractRelease(logger, releaseInfo):
		ReleaseExtractor.Extract( logger, releaseInfo.GetReleaseDownloadPath(), releaseInfo.GetReleaseUploadPath() )
		releaseInfo.Nfo = NfoParser.FindAndReadNfoFileToUnicode( releaseInfo.GetReleaseDownloadPath() )

	@staticmethod
	def GetCustomUploadPath(logger, releaseInfo):
		return ""

	@staticmethod
	def IsSingleFileTorrentNeedsDirectory():
		return True
	
	@staticmethod
	def IncludeReleaseNameInReleaseDescription():
		return True

	@staticmethod
	def GetIdFromUrl(url):
		return ""

	@staticmethod
	def GetUrlFromId(id):
		return ""	