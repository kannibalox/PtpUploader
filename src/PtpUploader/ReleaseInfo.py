from PtpUploaderException import PtpUploaderException;
from Settings import Settings;

import os;

class ReleaseInfo:
	def __init__(self, announcement, imdbId):
		self.Announcement = announcement;
		self.ImdbId = imdbId;

		# No enum = FAIL.		
		self.IsDvdRip = False;
		self.IsBdRip = False;
		self.IsX264_720p = False;
		self.IsX264_1080p = False;
		
		# If you add a supported format here, make sure to add it to:
		# - Ptp.MovieOnPtpResult.IsReleaseExists
		# - PtpUploadInfo.GetQualityAndSourceFromReleaseInfo
		# - ReleaseInfo.__init__
		releaseName = announcement.ReleaseName.lower();
		if releaseName.find( "dvdrip.xvid" ) != -1:
			self.IsDvdRip = True;
		elif releaseName.find( "bdrip.xvid" ) != -1:
			self.IsBdRip = True;
		elif releaseName.find( "720p.bluray.x264" ) != -1:
			self.IsX264_720p = True;
		elif releaseName.find( "1080p.bluray.x264" ) != -1:
			self.IsX264_1080p = True;
		else:
			raise PtpUploaderException( "Can't figure out release type from release name '%s'." % announcement.ReleaseName );
		
	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/"
	@staticmethod
	def GetReleaseRootPathFromRelaseName(releaseName):
		releasesPath = os.path.join( Settings.WorkingPath, "release" );
		return os.path.join( releasesPath, releaseName );
		
	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/"
	def GetReleaseRootPath(self):
		return ReleaseInfo.GetReleaseRootPathFromRelaseName( self.Announcement.ReleaseName );

	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/download/"
	@staticmethod
	def GetReleaseDownloadPathFromRelaseName(releaseName):
		return os.path.join( ReleaseInfo.GetReleaseRootPathFromRelaseName( releaseName ), "download" );

	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/download/"
	def GetReleaseDownloadPath(self):
		return ReleaseInfo.GetReleaseDownloadPathFromRelaseName( self.Announcement.ReleaseName );
	
	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/upload/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/"
	# It must contain the final release name because of mktorrent.
	def GetReleaseUploadPath(self):
		path = os.path.join( self.GetReleaseRootPath(), "upload" )
		return os.path.join( path, self.Announcement.ReleaseName );