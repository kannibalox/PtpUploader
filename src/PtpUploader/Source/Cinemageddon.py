from InformationSource.Imdb import Imdb
from Job.JobRunningState import JobRunningState
from Source.SourceBase import SourceBase

from Helper import GetSizeFromText
from MyGlobals import MyGlobals
from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor;
from ReleaseInfo import ReleaseInfo;
from Settings import Settings

import os
import re
import urllib
import urllib2

class Cinemageddon(SourceBase):
	def __init__(self):
		self.Name = "cg"
		self.MaximumParallelDownloads = Settings.CinemageddonMaximumParallelDownloads
	
	@staticmethod
	def IsEnabled():
		return len( Settings.CinemageddonUserName ) > 0 and len( Settings.CinemageddonPassword ) > 0

	@staticmethod
	def Login():
		MyGlobals.Logger.info( "Loggin in to Cinemageddon." )
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
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
	def __DownloadNfo(logger, releaseInfo):
		url = "http://cinemageddon.net/details.php?id=%s&filelist=1" % releaseInfo.AnnouncementId
		logger.info( "Collecting info from torrent page '%s'." % url )
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		response = response.decode( "ISO-8859-1", "ignore" )
		Cinemageddon.__CheckIfLoggedInFromResponse( response )

		# Make sure we only get information from the description and not from the comments.
		descriptionEndIndex = response.find( '<p><a name="startcomments"></a></p>' )
		if descriptionEndIndex == -1:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Description can't found on torrent page. Probably the layout of the site has changed." )
		
		description = response[ :descriptionEndIndex ]			

		# We will use the torrent's name as release name.
		matches = re.search( r'href="download.php\?id=(\d+)&name=.+">(.+)\.torrent</a>', description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Can't get release name from torrent page." )
		
		releaseInfo.ReleaseName = matches.group( 2 )

		# Get source and format type
		matches = re.search( r"torrent details for &quot;(.+) \[(\d+)/(.+)/(.+)\]&quot;", description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Can't get release source and format type from torrent page." )
		
		sourceType = matches.group( 3 )
		formatType = matches.group( 4 )

		# Get IMDb id.
		if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
			matches = re.search( r'imdb\.com/title/tt(\d+)', description )
			if matches is None:
				raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "IMDb id can't be found on torrent page." )

			releaseInfo.ImdbId = matches.group( 1 )

		# Get size.
		# Two possible formats:
		# <tr><td class="rowhead" valign="top" align="right">Size</td><td valign="top" align="left">1.46 GB (1,570,628,119 bytes)</td></tr>
		# <tr><td class="rowhead" valign="top" align="right">Size</td><td valign="top" align=left>1.46 GB (1,570,628,119 bytes)</td></tr>
		matches = re.search( r"""<tr><td class="rowhead" valign="top" align="right">Size</td><td valign="top" align="?left"?>.+ \((.+ bytes)\)</td></tr>""", description )
		if matches is None:
			logger.warning( "Size not found on torrent page." )
		else:
			size = matches.group( 1 )
			releaseInfo.Size = GetSizeFromText( size )

		# Ignore XXX releases.
		if description.find( '>Type</td><td valign="top" align=left>XXX<' ) != -1:
			raise PtpUploaderException( JobRunningState.Ignored_Forbidden, "Marked as XXX." )
		
		# Make sure that this is not a wrongly categorized DVDR.
		if re.search( ".vob</td>", description, re.IGNORECASE ) or re.search( ".iso</td>", description, re.IGNORECASE ):
			raise PtpUploaderException( JobRunningState.Ignored_NotSupported, "Wrongly categorized DVDR." )
		
		return sourceType, formatType

	@staticmethod
	def __MapSourceAndFormatToPtp(releaseInfo, sourceType, formatType):
		sourceType = sourceType.lower()
		formatType = formatType.lower()

		# Adding BDrip support would be problematic because there is no easy way to decide if it is HD or SD.
		# Maybe we could use the resolution and file size. But what about the oversized and upscaled releases? 
		
		if releaseInfo.IsResolutionTypeSet():
			releaseInfo.Logger.info( "Resolution type '%s' is already set, not getting from the torrent page." % releaseInfo.ResolutionType )
		else:
			releaseInfo.ResolutionType = "Other"

		if releaseInfo.IsSourceSet():
			releaseInfo.Logger.info( "Source '%s' is already set, not getting from the torrent page." % releaseInfo.Source )
		elif sourceType == "dvdrip":
			releaseInfo.Source = "DVD"
		elif sourceType == "vhsrip":
			releaseInfo.Source = "VHS"
		elif sourceType == "tvrip":
			releaseInfo.Source = "TV"
		else:
			raise PtpUploaderException( JobRunningState.Ignored_NotSupported, "Unsupported source type '%s'." % sourceType )

		if releaseInfo.IsCodecSet():
			releaseInfo.Logger.info( "Codec '%s' is already set, not getting from the torrent page." % releaseInfo.Codec )
		elif formatType == "x264":
			releaseInfo.Codec = "x264"
		elif formatType == "xvid":
			releaseInfo.Codec = "XviD"
		elif formatType == "divx":
			releaseInfo.Codec = "DivX"
		else:
			raise PtpUploaderException( JobRunningState.Ignored_NotSupported, "Unsupported format type '%s'." % formatType )
	
	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		sourceType = ""
		formatType = ""
		
		if releaseInfo.IsUserCreatedJob():
			sourceType, formatType = Cinemageddon.__DownloadNfo( logger, releaseInfo )
		else:
			# TODO: add filterting support for Cinemageddon
			# In case of automatic announcement we have to check the release name if it is valid.
			# We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source. 
			#if not ReleaseFilter.IsValidReleaseName( releaseInfo.ReleaseName ):
			#	logger.info( "Ignoring release '%s' because of its name." % releaseInfo.ReleaseName )
			#	return None
			sourceType, formatType = Cinemageddon.__DownloadNfo( logger, releaseInfo )

		Cinemageddon.__MapSourceAndFormatToPtp( releaseInfo, sourceType, formatType )		

	@staticmethod
	def DownloadTorrent(logger, releaseInfo, path):
		url = "http://cinemageddon.net/download.php?id=%s" % releaseInfo.AnnouncementId
		logger.info( "Downloading torrent file from '%s' to '%s'." % ( url, path ) )

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		Cinemageddon.__CheckIfLoggedInFromResponse( response )
		
		file = open( path, "wb" )
		file.write( response )
		file.close()
		
	@staticmethod
	def ExtractRelease(logger, releaseInfo):
		# Extract the release.
		nfoPath = ReleaseExtractor.Extract( releaseInfo.GetReleaseDownloadPath(), releaseInfo.GetReleaseUploadPath() )
		if nfoPath is not None:
			releaseInfo.Nfo = NfoParser.ReadNfoFileToUnicode( nfoPath )

	@staticmethod
	def __RemoveNonAllowedCharacters(text):
		newText = text

		# This would butcher titles with non-English characters in it.
		# Eg.: Indul a bakterház -> Indul a bakterhz
		# Stripping accents would help a bit, but it still wouldn't perfect. 
				
		#newText = ""
		#for c in text:
		#	if ( c >= '0' and c <= '9' ) or ( c >= 'a' and c <= 'z' ) or ( c >= 'A' and c <= 'Z' ):
		#		newText += c
		#	elif c == ' ':
		#		newText += '.'
		
		# These characters can't be in filenames on Windows.
		forbiddenCharacters = r"""\/:*?"<>|"""
		for c in forbiddenCharacters:
			newText = newText.replace( c, "" )

		if len( newText ) > 0:
			return newText
		else:
			raise PtpUploaderException( "New name for '%s' resulted in empty string." % text )

	# Because some of the releases on CG do not contain the full name of the movie, we have to rename them because of the uploading rules on PTP.
	# The new name will be formatted like this: Movie Name Year
	@staticmethod
	def GetCustomUploadPath(logger, releaseInfo):
		# TODO: if the user forced a release name, then let it upload by that name.
		if releaseInfo.IsZeroImdbId():
			raise PtpUploaderException( "Uploading to CG with zero IMDb ID is not yet supported." % text ) 		
		
		# If the movie already exists on PTP then the IMDb info is not populated in ReleaseInfo.
		if len( releaseInfo.InternationalTitle ) <= 0 or len( releaseInfo.Year ) <= 0:
			imdbInfo = Imdb.GetInfo( logger, releaseInfo.GetImdbId() )
			if len( releaseInfo.InternationalTitle ) <= 0:
				releaseInfo.InternationalTitle = imdbInfo.Title
			if len( releaseInfo.Year ) <= 0:
				releaseInfo.Year = imdbInfo.Year

		name = "%s (%s)" % ( releaseInfo.InternationalTitle, releaseInfo.Year )
		name = Cinemageddon.__RemoveNonAllowedCharacters( name )

		logger.info( "Upload directory will be named '%s' instead of '%s'." % ( name, releaseInfo.ReleaseName ) )
		
		newUploadPath = releaseInfo.GetReleaseUploadPath()
		newUploadPath = os.path.dirname( newUploadPath )
		newUploadPath = os.path.join( newUploadPath, name )
		return newUploadPath

	@staticmethod
	def IncludeReleaseNameInReleaseDescription():
		return False
	
	@staticmethod
	def GetIdFromUrl(url):
		result = re.match( r".*cinemageddon\.net/details.php\?id=(\d+).*", url )
		if result is None:
			return ""
		else:
			return result.group( 1 )	

	@staticmethod
	def GetUrlFromId(id):
		return "http://cinemageddon.net/details.php?id=" + id