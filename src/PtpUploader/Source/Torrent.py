from Source.SourceBase import SourceBase

from Globals import Globals
from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor
from ReleaseInfo import ReleaseInfo
from ReleaseNameParser import ReleaseNameParser
from Settings import Settings

class Torrent(SourceBase):
	def __init__(self):
		self.Name = "torrent"
		self.MaximumParallelDownloads = 1

	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		# TODO: support for uploads from torrent without specifying IMDb id and reading it from NFO. (We only get IMDb id when the download is finisehd.)

		# TODO: support for new movies without IMDB id
		if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
			logger.info( "Release '%s' doesn't contain IMDb or PTP id." % releaseInfo.ReleaseName )
			return None
		
		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		releaseNameParser.GetSourceAndFormat( releaseInfo )
		if releaseNameParser.Scene: 
			releaseInfo.SetSceneRelease() 
		return releaseInfo
		
	@staticmethod
	def ExtractRelease(logger, releaseInfo):
		# Extract the release.
		nfoPath = ReleaseExtractor.Extract( releaseInfo.GetReleaseDownloadPath(), releaseInfo.GetReleaseUploadPath() )
		if nfoPath is not None:
			releaseInfo.Nfo = NfoParser.ReadNfoFileToUnicode( nfoPath )