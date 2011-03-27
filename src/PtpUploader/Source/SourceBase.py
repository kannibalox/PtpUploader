class SourceBase:
	@staticmethod
	def Login():
		pass
	
	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		pass
		
	@staticmethod
	def DownloadTorrent(logger, releaseInfo, path):
		pass
	
	@staticmethod
	def IsDownloadFinished(logger, releaseInfo, rtorrent):
		return rtorrent.IsTorrentFinished( logger, releaseInfo.SourceTorrentInfoHash )

	@staticmethod
	def ExtractRelease(logger, releaseInfo):
		pass

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