from PtpUploadInfo import PtpUploadInfo
from PtpUploaderException import PtpUploaderException
from Settings import Settings

import os

class ReleaseInfo:
	def __init__(self, announcement, imdbId):
		self.Announcement = announcement
		self.PtpUploadInfo = PtpUploadInfo()
		self.PtpUploadInfo.ImdbId = imdbId
		self.Nfo = u""
		self.SourceTorrentInfoHash = ""

	def GetImdbId(self):
		return self.PtpUploadInfo.ImdbId

	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/"
	@staticmethod
	def GetReleaseRootPathFromRelaseName(releaseName):
		releasesPath = os.path.join( Settings.WorkingPath, "release" )
		return os.path.join( releasesPath, releaseName )
		
	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/"
	def GetReleaseRootPath(self):
		return ReleaseInfo.GetReleaseRootPathFromRelaseName( self.Announcement.ReleaseName )

	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/download/"
	@staticmethod
	def GetReleaseDownloadPathFromRelaseName(releaseName):
		return os.path.join( ReleaseInfo.GetReleaseRootPathFromRelaseName( releaseName ), "download" )

	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/download/"
	def GetReleaseDownloadPath(self):
		return ReleaseInfo.GetReleaseDownloadPathFromRelaseName( self.Announcement.ReleaseName )
	
	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/upload/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/"
	# It must contain the final release name because of mktorrent.
	def GetReleaseUploadPath(self):
		path = os.path.join( self.GetReleaseRootPath(), "upload" )
		return os.path.join( path, self.Announcement.ReleaseName )