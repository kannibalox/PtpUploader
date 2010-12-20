from PtpUploaderException import PtpUploaderException;

import codecs;
import os;

class PtpUploadInfo:
	def __init__(self):
		self.Type = "Movies"; # Movies, Musicals, Standup Comedy, Concerts
		self.ImdbId = ""; # Just the number. Eg.: 0111161 for http://www.imdb.com/title/tt0111161/
		self.Directors = [];
		self.Title = "";
		self.Year = "";
		self.Tags = "";
		self.MovieDescription = u"";
		self.CoverArtUrl = "";
		self.Scene = ""; # Empty string or "on" (wihout the quotes).
		self.Quality = ""; # Other, Standard Definition, High Definition
		self.Codec = ""; # Other, DivX, XviD, H.264, x264, DVD5, DVD9, BD25, BD50
		self.Container = ""; # Other, MPG, AVI, MP4, MKV, VOB IFO, ISO, m2ts
		self.ResolutionType = ""; # Other, PAL, NTSC, 480p, 576p, 720p, 1080i, 1080p
		self.Resolution = ""; # Exact resolution when ResolutionType is Other. 
		self.Source = ""; # Other, CAM, TS, VHS, TV, DVD-Screener, TC, HDTV, R5, DVD, HD-DVD, Blu-Ray
		self.ReleaseDescription = u"";

	def IsStandardDefintion(self):
		return self.Quality == "Standard Definition";		

	# Fills container, codec and resolution from media info.
	def GetDataFromMediaInfo(self, mediaInfo):
		if mediaInfo.IsAvi():
			self.Container = "AVI";
		elif mediaInfo.IsMkv():
			self.Container = "MKV";
		else:
			raise PtpUploaderException( "Unsupported container: '%s'." % mediaInfo.Container );

		# TODO: check if set already and make sure it remains the same if it set
		if mediaInfo.IsX264():
			self.Codec = "x264";
		elif mediaInfo.IsXvid():
			self.Codec = "XviD";
		elif mediaInfo.IsDivx():
			self.Codec = "DivX";
		else:
			raise PtpUploaderException( "Unsupported codec: '%s'." % mediaInfo.Codec );
		
		# Indicate the exact resolution for standard definition releases.
		if self.IsStandardDefintion():
			self.Resolution = "%sx%s" % ( mediaInfo.Width, mediaInfo.Height );
		
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