from Job.JobRunningState import JobRunningState
from Source.SourceBase import SourceBase

from MyGlobals import MyGlobals
from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor
from ReleaseInfo import ReleaseInfo
from ReleaseNameParser import ReleaseNameParser
from Settings import Settings

# TODO: support if GetReleaseDownloadPath is a file

class File(SourceBase):
	def __init__(self):
		self.Name = "file"
		self.MaximumParallelDownloads = 1
	
	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		# TODO: support if GetReleaseDownloadPath is a file
		
		if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
			nfo = NfoParser.GetNfoFile( ReleaseInfo.GetReleaseDownloadPath() )
			imdbId = NfoParser.GetImdbId( nfo )
			if len( imdbId ) > 0:
				releaseInfo.ImdbId = imdbId 
			else:
				raise PtpUploaderException( "Doesn't contain IMDb ID." )

		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		releaseNameParser.GetSourceAndFormat( releaseInfo )
		if releaseNameParser.Scene: 
			releaseInfo.SetSceneRelease()

	@staticmethod
	def IsDownloadFinished(logger, releaseInfo, rtorrent):
		return True