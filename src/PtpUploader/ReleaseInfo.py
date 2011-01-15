from PtpUploaderException import PtpUploaderException
from Settings import Settings

import codecs
import os

class ReleaseInfo:
	def __init__(self, announcement, imdbId):
		self.Announcement = announcement

		# These are the required fields needed for an upload to PTP.		
		self.Type = "Movies" # Movies, Musicals, Standup Comedy, Concerts
		self.ImdbId = imdbId # Just the number. Eg.: 0111161 for http://www.imdb.com/title/tt0111161/
		self.Directors = []
		self.Title = ""
		self.Year = ""
		self.Tags = ""
		self.MovieDescription = u""
		self.CoverArtUrl = ""
		self.Scene = "" # Empty string or "on" (wihout the quotes).
		self.Quality = "" # Other, Standard Definition, High Definition
		self.Codec = "" # Other, DivX, XviD, H.264, x264, DVD5, DVD9, BD25, BD50
		self.Container = "" # Other, MPG, AVI, MP4, MKV, VOB IFO, ISO, m2ts
		self.ResolutionType = "" # Other, PAL, NTSC, 480p, 576p, 720p, 1080i, 1080p
		self.Resolution = "" # Exact resolution when ResolutionType is Other. 
		self.Source = "" # Other, CAM, TS, VHS, TV, DVD-Screener, TC, HDTV, R5, DVD, HD-DVD, Blu-Ray
		self.ReleaseDescription = u""
		# Till this.
		
		self.Nfo = u""
		self.SourceTorrentInfoHash = ""

	def GetImdbId(self):
		return self.ImdbId

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
	
	def IsStandardDefintion(self):
		return self.Quality == "Standard Definition"		

	# Fills container, codec and resolution from media info.
	def GetDataFromMediaInfo(self, mediaInfo):
		if mediaInfo.IsAvi():
			self.Container = "AVI"
		elif mediaInfo.IsMkv():
			self.Container = "MKV"
		else:
			raise PtpUploaderException( "Unsupported container: '%s'." % mediaInfo.Container )

		# TODO: check if set already and make sure it remains the same if it set
		if mediaInfo.IsX264():
			self.Codec = "x264"
			if mediaInfo.IsAvi():
				raise PtpUploaderException( "X264 in AVI is not allowed." )
		elif mediaInfo.IsXvid():
			self.Codec = "XviD"
			if mediaInfo.IsMkv():
				raise PtpUploaderException( "XviD in MKV is not allowed." )
		elif mediaInfo.IsDivx():
			self.Codec = "DivX"
			if mediaInfo.IsMkv():
				raise PtpUploaderException( "DivX in MKV is not allowed." )
		else:
			raise PtpUploaderException( "Unsupported codec: '%s'." % mediaInfo.Codec )

		# Indicate the exact resolution for standard definition releases.
		if self.IsStandardDefintion():
			self.Resolution = "%sx%s" % ( mediaInfo.Width, mediaInfo.Height )
		
	# releaseDescriptionFilePath: optional. If given the description is written to file.
	def FormatReleaseDescription(self, logger, releaseInfo, screenshots, mediaInfos, releaseDescriptionFilePath = None):
		logger.info( "Making release description for release '%s' with screenshots at %s." % ( releaseInfo.Announcement.ReleaseName, screenshots ) )

		self.ReleaseDescription = u"[size=4][b]%s[/b][/size]\n\n" % releaseInfo.Announcement.ReleaseName

		for screenshot in screenshots:
			self.ReleaseDescription += u"[img=%s]\n\n" % screenshot

		for mediaInfo in mediaInfos:
			# Add file name before each media info if there are more than one videos in the release.
			if len( mediaInfos ) > 1:
				fileName = os.path.basename( mediaInfo.Path )
				self.ReleaseDescription += u"[size=3][u]%s[/u][/size]\n\n" % fileName

			self.ReleaseDescription += mediaInfo.FormattedMediaInfo

		# Add NFO if presents
		if len( releaseInfo.Nfo ) > 0:
			self.ReleaseDescription += u"[size=3][u]NFO[/u][/size]:[pre]\n%s\n[/pre]" % releaseInfo.Nfo

		# We don't use this file for anything, we just save it for convenience.
		if releaseDescriptionFilePath is not None:
			releaseDescriptionFile = codecs.open( releaseDescriptionFilePath, encoding = "utf-8", mode = "w" )
			releaseDescriptionFile.write( self.ReleaseDescription )
			releaseDescriptionFile.close()