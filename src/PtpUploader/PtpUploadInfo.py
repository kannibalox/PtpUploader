from Globals import Globals;
from PtpUploaderException import PtpUploaderException;

import codecs;
import os;

class PtpUploadInfo:
	def __init__(self):
		self.Type = "Movies"; # Movies, Musicals, Standup Comedy, Concerts
		self.ImdbId = ""; # Just the number. Eg.: 0111161 for http://www.imdb.com/title/tt0111161/
		self.RottenTomatoesUrl = "";
		self.Directors = [];
		self.Title = "";
		self.Year = "";
		self.Tags = "";
		self.MovieDescription = "";
		self.CoverArtUrl = "";
		self.Scene = ""; # Empty string or "on" (wihout the quotes).
		self.Quality = ""; # High Definition, Standard Definition, Other
		self.Codec = ""; # XviD, DivX, H.264, x264, DVD5, DVD9, BD25, BD50, Other
		self.Container = ""; # AVI, MPG, MKV, MP4, VOB IFO, ISO, m2ts, Other
		self.ResolutionType = ""; # NTSC, PAL, 480p, 576p, 720p, 1080i, 1080p, Other
		self.Resolution = ""; # Exact resolution when ResolutionType is Other. 
		self.Source = ""; # CAM, TC, TS, R5, DVD-Screener, VHS, DVD, TV, HDTV, HD-DVD, Blu-Ray, Other
		self.ReleaseDescription = "";

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

		if mediaInfo.IsXvid():
			self.Codec = "XviD";
		elif mediaInfo.IsX264():
			self.Codec = "x264";
		else:
			raise PtpUploaderException( "Unsupported codec: '%s'." % mediaInfo.Codec );
		
		# Indicate the exact resolution for standard definition releases.
		if self.IsStandardDefintion():
			self.Resolution = "%sx%s" % ( mediaInfo.Width, mediaInfo.Height );
		
	def FormatReleaseDescription(self, releaseInfo, screenshots, mediaInfos):
		Globals.Logger.info( "Making release description for release '%s' with screenshots at %s." % ( releaseInfo.Announcement.ReleaseName, screenshots ) );
		
		self.ReleaseDescription = u"[size=4][b]%s[/b][/size]\n\n" % releaseInfo.Announcement.ReleaseName;

		for screenshot in screenshots:
			self.ReleaseDescription += u"[img=%s]\n\n" % screenshot;
		
		for mediaInfo in mediaInfos:
			fileName = os.path.basename( mediaInfo.Path );
			self.ReleaseDescription += u"[size=3][u]%s[/u][/size]\n\n" % fileName;
			self.ReleaseDescription += mediaInfo.FormattedMediaInfo; 

		# Add NFO if presents
		if len( releaseInfo.Nfo ) > 0:
			self.ReleaseDescription += u"[size=3][u]NFO[/u][/size]:[pre]\n%s\n[/pre]" % releaseInfo.Nfo;
		
		# We don't use this file for anything, we just save it for convenience.
		releaseDescriptionPath = os.path.join( releaseInfo.GetReleaseRootPath(), "release description.txt" );
		releaseDescriptionFile = codecs.open( releaseDescriptionPath, encoding = "utf-8", mode = "w" );
		releaseDescriptionFile.write( self.ReleaseDescription );
		releaseDescriptionFile.close();