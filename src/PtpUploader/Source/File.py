from Source.SourceBase import SourceBase

from MyGlobals import MyGlobals
from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor
from ReleaseInfo import ReleaseInfo
from ReleaseNameParser import ReleaseNameParser
from Settings import Settings

class File(SourceBase):
	def __init__(self):
		self.Name = "file"
		self.MaximumParallelDownloads = 1
	
	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		# TODO: support for new movies without IMDB id
		if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
			nfo = NfoParser.GetNfoFile( ReleaseInfo.GetReleaseDownloadPathFromRelaseName( releaseInfo.ReleaseName ) )
			imdbId = NfoParser.GetImdbId( nfo )
			if len( imdbId ) > 0:
				releaseInfo.ImdbId = imdbId 
			else:
				logger.info( "Release '%s' doesn't contain IMDb or PTP id." % releaseInfo.ReleaseName )
				return None

		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		releaseNameParser.GetSourceAndFormat( releaseInfo )
		if releaseNameParser.Scene: 
			releaseInfo.SetSceneRelease() 
		return releaseInfo

	@staticmethod
	def IsDownloadFinished(logger, releaseInfo, rtorrent):
		return True
		
	@staticmethod
	def ExtractRelease(logger, releaseInfo):
		# Extract the release.
		nfoPath = ReleaseExtractor.Extract( releaseInfo.GetReleaseDownloadPath(), releaseInfo.GetReleaseUploadPath() )
		if nfoPath is not None:
			releaseInfo.Nfo = NfoParser.ReadNfoFileToUnicode( nfoPath )