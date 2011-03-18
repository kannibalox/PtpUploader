from Globals import Globals
from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor
from ReleaseInfo import ReleaseInfo
from ReleaseNameParser import ReleaseNameParser
from Settings import Settings

class Manual:
	def __init__(self):
		self.Name = "manual"
		self.MaximumParallelDownloads = 1
	
	@staticmethod
	def Login():
		pass;
	
	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		# TODO: support for new movies without IMDB id
		if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
			logger.info( "Release '%s' doesn't contain IMDb or PTP id." % releaseInfo.ReleaseName )
			return None
		
		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		releaseNameParser.GetSourceAndFormat( releaseInfo )
		if releaseNameParser.Scene: 
			releaseInfo.Scene = "on" 
		return releaseInfo
		
	@staticmethod
	def DownloadTorrent(logger, releaseInfo, path):
		pass;
		
	@staticmethod
	def ExtractRelease(logger, releaseInfo):
		# Extract the release.
		nfoPath = ReleaseExtractor.Extract( releaseInfo.GetReleaseDownloadPath(), releaseInfo.GetReleaseUploadPath() )
		if nfoPath is not None:
			releaseInfo.Nfo = NfoParser.ReadNfoFileToUnicode( nfoPath )

	@staticmethod
	def RenameRelease(logger, releaseInfo):
		pass

	@staticmethod
	def IsSingleFileTorrentNeedsDirectory():
		return True
	
	@staticmethod
	def IncludeReleaseNameInReleaseDescription():
		return True