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
	def ExtractRelease(logger, releaseInfo):
		pass

	@staticmethod
	def RenameRelease(logger, releaseInfo):
		pass

	@staticmethod
	def IsSingleFileTorrentNeedsDirectory():
		return True
	
	@staticmethod
	def IncludeReleaseNameInReleaseDescription():
		return True