from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor

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
	def CheckCoverArt(logger, releaseInfo):
		# If it exists on PTP then we don't need a cover.
		if ( not releaseInfo.IsCoverArtUrlSet() ) and ( not releaseInfo.HasPtpId() ):
			raise PtpUploaderException( "Cover art is not set." )

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