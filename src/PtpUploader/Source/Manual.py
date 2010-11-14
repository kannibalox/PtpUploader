from Globals import Globals;
from NfoParser import NfoParser;
from PtpUploaderException import PtpUploaderException;
from ReleaseInfo import ReleaseInfo;
from SceneRelease import SceneRelease;
from Settings import Settings;

# TODO: add support for non scene releases.
# How will we get the IMDb id and the info gained from GetSourceAndFormatFromSceneReleaseName? Probably only with a custom irc message if there is no NFO.

class Manual:
	def __init__(self):
		self.Name = "manual"
		self.MaximumParallelDownloads = 1
	
	@staticmethod
	def Login():
		pass;
	
	@staticmethod
	def PrepareDownload(announcement):
		nfo = NfoParser.GetNfoFile( ReleaseInfo.GetReleaseDownloadPathFromRelaseName( announcement.ReleaseName ) )
		imdbId = NfoParser.GetImdbId( nfo )
		
		releaseInfo = ReleaseInfo( announcement, imdbId )
		releaseInfo.Nfo = nfo;
		SceneRelease.GetSourceAndFormatFromSceneReleaseName( releaseInfo.PtpUploadInfo, announcement.ReleaseName )
		return releaseInfo
		
	@staticmethod
	def DownloadTorrent(releaseInfo, path):
		pass;
		
	@staticmethod
	def ExtractRelease(releaseInfo):
		# Extract the release.
		sceneRelease = SceneRelease( releaseInfo.GetReleaseDownloadPath() )
		sceneRelease.Extract( releaseInfo.GetReleaseUploadPath() )
		
	@staticmethod
	def IsSingleFileTorrentNeedsDirectory():
		return True