from Globals import Globals
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor;
from ReleaseInfo import ReleaseInfo;
from Settings import Settings

import re
import urllib
import urllib2

class Cinemageddon:
	def __init__(self):
		self.Name = "cg"
		self.MaximumParallelDownloads = Settings.CinemageddonMaximumParallelDownloads
	
	@staticmethod
	def Login():
		Globals.Logger.info( "Loggin in to Cinemageddon." )
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) )
		postData = urllib.urlencode( { "username": Settings.CinemageddonUserName, "password": Settings.CinemageddonPassword } )
		request = urllib2.Request( "http://cinemageddon.net/takelogin.php", postData )
		result = opener.open( request )
		response = result.read()
		Cinemageddon.__CheckIfLoggedInFromResponse( response )
	
	@staticmethod
	def __CheckIfLoggedInFromResponse(response):
		if response.find( 'action="takelogin.php"' ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to Cinemageddon. Probably due to the bad user name or password in settings." )

	@staticmethod
	def __DownloadNfo(announcement):
		url = "http://cinemageddon.net/details.php?id=%s&filelist=1" % announcement.AnnouncementId
		Globals.Logger.info( "Collecting info from torrent page '%s'." % url )
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		Cinemageddon.__CheckIfLoggedInFromResponse( response )

		# We will use the torrent's name as release name.
		matches = re.search( r'href="download.php\?id=(\d+)&name=.+">(.+)\.torrent</a>', response )
		if matches is None:
			raise PtpUploaderException( "Can't get release name from page '%s'." % url )
		
		announcement.ReleaseName = matches.group( 2 )

		# Get source and format type
		matches = re.search( r"torrent details for &quot;(.+) \[(\d+)/(.+)/(.+)\]&quot;", response )
		if matches is None:
			raise PtpUploaderException( "Can't get release source and format type from page '%s'." % url )
		
		sourceType = matches.group( 3 )
		formatType = matches.group( 4 )

		# Get IMDb id
		matches = re.search( r'imdb\.com/title/tt(\d+)', response )
		if matches is None:
			raise PtpUploaderException( "Ignoring release '%s' at '%s' because IMDb id can't be found." % ( announcement.ReleaseName, url ) )

		imdbId = matches.group( 1 )

		# Ignore XXX releases.
		if response.find( '>Type</td><td valign="top" align=left>XXX<' ) != -1:
			raise PtpUploaderException( "Ignoring release '%s' at '%s' because it is XXX." % ( announcement.ReleaseName, url ) )
		
		# Make sure that this is not a wrongly categorized DVDR.
		if re.search( ".vob</td>", response, re.IGNORECASE ) or re.search( ".iso</td>", response, re.IGNORECASE ):
			raise PtpUploaderException( "Ignoring release '%s' at '%s' because it is a wrongly categorized DVDR." % ( announcement.ReleaseName, url ) )
		
		return imdbId, sourceType, formatType

	@staticmethod
	def __MapSourceAndFormatToPtp(ptpUploadInfo, sourceType, formatType):
		sourceType = sourceType.lower()
		formatType = formatType.lower()

		# Adding BDrip support would be problematic because there is no easy way to decide if it is HD or SD.
		# Maybe we could use the resolution and file size. But what about the oversized and upscaled releases? 
		
		if formatType != "xvid" and formatType != "divx" and formatType != "x264":
			raise PtpUploaderException( "Got unsupported format type '%s' from Cinemageddon." % formatType )
			
		ptpUploadInfo.Quality = "Standard Definition"
		ptpUploadInfo.ResolutionType = "Other"

		if sourceType == "dvdrip":
			ptpUploadInfo.Source = "DVD"
		elif sourceType == "vhsrip":
			ptpUploadInfo.Source = "VHS"
		elif sourceType == "tvrip":
			ptpUploadInfo.Source = "TV"
		else:
			raise PtpUploaderException( "Got unsupported source type '%s' from Cinemageddon." % sourceType );
	
	@staticmethod
	def PrepareDownload(announcement):
		imdbId = ""
		sourceType = ""
		formatType = ""
		
		if announcement.IsManualAnnouncement:
			imdbId, sourceType, formatType = Cinemageddon.__DownloadNfo( announcement, getReleaseName = True )
		else:
			# TODO: add filterting support for Cinemageddon
			# In case of automatic announcement we have to check the release name if it is valid.
			# We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source. 
			#if not ReleaseFilter.IsValidReleaseName( announcement.ReleaseName ):
			#	Globals.Logger.info( "Ignoring release '%s' because of its name." % announcement.ReleaseName )
			#	return None
			imdbId, sourceType, formatType = Cinemageddon.__DownloadNfo( announcement )
			
		releaseInfo = ReleaseInfo( announcement, imdbId )
		Cinemageddon.__MapSourceAndFormatToPtp( releaseInfo.PtpUploadInfo, sourceType, formatType )		
		return releaseInfo
		
	@staticmethod
	def DownloadTorrent(releaseInfo, path):
		url = "http://cinemageddon.net/download.php?id=%s" % releaseInfo.Announcement.AnnouncementId
		Globals.Logger.info( "Downloading torrent file from '%s' to '%s'." % ( url, path ) )

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		Cinemageddon.__CheckIfLoggedInFromResponse( response )
		
		file = open( path, "wb" )
		file.write( response )
		file.close()
		
	@staticmethod
	def ExtractRelease(releaseInfo):
		ReleaseExtractor.Extract( releaseInfo.GetReleaseDownloadPath(), releaseInfo.GetReleaseUploadPath() )
		
	@staticmethod
	def IsSingleFileTorrentNeedsDirectory():
		return False