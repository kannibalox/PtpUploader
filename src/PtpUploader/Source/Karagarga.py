from InformationSource.Imdb import Imdb
from Job.JobRunningState import JobRunningState
from Source.SourceBase import SourceBase

from Helper import GetSizeFromText, RemoveDisallowedCharactersFromPath, ValidateTorrentFile
from MyGlobals import MyGlobals
from NfoParser import NfoParser
from PtpUploaderException import *
from ReleaseExtractor import ReleaseExtractor;
from ReleaseInfo import ReleaseInfo;
from Settings import Settings

import os
import re
import urllib
import urllib2

class Karagarga(SourceBase):
	def __init__(self):
		self.Name = "kg"
		self.Username = Settings.GetDefault( "Karagarga", "Username", "" )
		self.Password = Settings.GetDefault( "Karagarga", "Password", "" )
		self.MaximumParallelDownloads = int( Settings.GetDefault( "Karagarga", "MaximumParallelDownloads", "4" ) )

	def IsEnabled(self):
		return len( self.Username ) > 0 and len( self.Password ) > 0

	def Login(self):
		if len( self.Username ) <= 0:
			raise PtpUploaderInvalidLoginException( "Couldn't log in to Karagarga. Your username is not specified.." )

		if len( self.Password ) <= 0:
			raise PtpUploaderInvalidLoginException( "Couldn't log in to Karagarga. Your password is not specified.." )
	
		MyGlobals.Logger.info( "Logging in to Karagarga." )
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		postData = urllib.urlencode( { "username": self.Username, "password": self.Password } )
		request = urllib2.Request( "http://karagarga.net/takelogin.php", postData )
		result = opener.open( request )
		response = result.read()
		self.__CheckIfLoggedInFromResponse( response )
	
	def __CheckIfLoggedInFromResponse(self, response):
		if response.find( 'action="takelogin.php"' ) != -1 or response.find( """<h2>Login failed!</h2>""" ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to Karagarga. Probably due to the bad user name or password in settings." )

	def __DownloadNfoParseSourceType(self, releaseInfo, description):
		if releaseInfo.IsSourceSet():
			releaseInfo.Logger.info( "Source '%s' is already set, not getting from the torrent page." % releaseInfo.Source )
			return

		# <tr><td class="heading" align="right" valign="top">Source</td><td colspan="2" align="left" valign="top">dvdrip</td></tr>
		matches = re.search( """<tr><td class="heading".*?>Source</td><td.*?>(.+?)</td></tr>""", description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Source type can't be found. Probably the layout of the site has changed." )

		sourceType = matches.group( 1 ).lower()

		# DVDR and HD are present in the genre list. These are not supported.
		# <td style="border:none;"><img src="genreimages/dvdr.png" width="40" height="40" border="0" title="DVDR"></td>
		# <td style="border: medium none;"><img src="genreimages/hdrip.png" title="HD" border="0" height="40" width="40"></td>
		matches = re.search( """<td.*?><img src="genreimages/.+?" .*?title="(.+?)".*?></td>""", description )
		if matches is not None:
			notSupportedSourceType = matches.group( 1 ).lower()
			if notSupportedSourceType == "dvdr" or notSupportedSourceType == "hd":
				sourceType = notSupportedSourceType

		if sourceType == "blu-ray":
			releaseInfo.Source = "Blu-ray"
		elif sourceType == "dvdrip":
			releaseInfo.Source = "DVD"
		elif sourceType == "vhsrip":
			releaseInfo.Source = "VHS"
		elif sourceType == "tvrip":
			releaseInfo.Source = "TV"
		else:
			raise PtpUploaderException( JobRunningState.Ignored_NotSupported, "Unsupported source type '%s'." % sourceType )

	# TODO: SD mkv supprot
	def __DownloadNfoParseFormatType(self, releaseInfo, description):
		if releaseInfo.IsCodecSet():
			releaseInfo.Logger.info( "Codec '%s' is already set, not getting from the torrent page." % releaseInfo.Codec )
			return
		
		# <tr><td class="heading" align="right" valign="top">Rip Specs</td><td colspan="2" align="left" valign="top">[General] Format: AVI
		# ...
		# </td></tr>		
		ripSpecs = re.search( r"<tr><td.*?>Rip Specs</td><td.*?>(.+?)</td></tr>", description, re.DOTALL )
		if ripSpecs is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Rip specifications can't be found on the page." )			
		
		ripSpecs = ripSpecs.group( 1 )

		# Some program makes a stupid format like this 'Video Codec Type(e.g. "DIV3"): xvid', so we have to handle this specially.
		match = re.search( r"""Video Codec Type.*?\(e\.g\..+?\):(.+)""", ripSpecs, re.IGNORECASE )
		if match:
			ripSpecs = "Codec: " + match.group( 1 )
		
		if re.search( r"Codec.+?XviD", ripSpecs, re.IGNORECASE ) or\
			re.search( r"Video Format.+?XviD", ripSpecs, re.IGNORECASE ):
			releaseInfo.Codec = "XviD"
		elif re.search( r"Codec.+?DivX", ripSpecs, re.IGNORECASE ) or\
			re.search( r"Video Format.+?DivX", ripSpecs, re.IGNORECASE ):
			releaseInfo.Codec = "DivX"
		elif re.search( r"Codec.+?V_MPEG4/ISO/AVC", ripSpecs, re.IGNORECASE ) or\
			re.search( r"Codec.+?x264", ripSpecs, re.IGNORECASE ):
			releaseInfo.Codec = "x264"
		else:
			raise PtpUploaderException( JobRunningState.Ignored_NotSupported, "Can't figure out codec from the rip specifications." )

	def __DownloadNfo(self, logger, releaseInfo):
		url = "http://karagarga.net/details.php?id=%s&filelist=1" % releaseInfo.AnnouncementId
		logger.info( "Collecting info from torrent page '%s'." % url )
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		response = response.decode( "ISO-8859-1", "ignore" )
		self.__CheckIfLoggedInFromResponse( response )

		# Make sure we only get information from the description and not from the comments.
		descriptionEndIndex = response.find( '<p><a name="startcomments"></a></p>' )
		if descriptionEndIndex == -1:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Description can't found on torrent page. Probably the layout of the site has changed." )
		
		description = response[ :descriptionEndIndex ]			

		# We will use the torrent's name as release name.
		matches = re.search( r'href="down.php/(\d+)/.+?">(.+?)\.torrent</a>', description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Can't get release name from torrent page." )

		releaseName = matches.group( 2 )
		
		# Remove the extension of the container from the release name. (It is there on single file releases.)
		# Optional flags parameter for sub function was only introduced in Python v2.7 so we use compile.sub instead. 
		releaseName = re.compile( r"\.avi$", re.IGNORECASE ).sub( "", releaseName )
		releaseName = re.compile( r"\.mkv$", re.IGNORECASE ).sub( "", releaseName )
		releaseInfo.ReleaseName = releaseName
		
		# Make sure it is under the movie category.
		# <tr><td class="heading" align="right" valign="top">Type</td><td colspan="2" align="left" valign="top"><a href="browse.php?cat=1">Movie</a></td></tr>
		matches = re.search( r"""<tr><td.*?>Type</td><td.*?><a href="browse.php\?cat=1">Movie</a></td></tr>""", description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_NotSupported, "Type is not movie." )			

		# Get IMDb id.
		if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
			matches = re.search( r'imdb\.com/title/tt(\d+)', description )
			if matches is None:
				raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "IMDb id can't be found on torrent page." )

			releaseInfo.ImdbId = matches.group( 1 )

		# Get size.
		# <tr><td class="heading" align="right" valign="top">Size</td><td colspan="2" align="left" valign="top">1.37GB (1,476,374,914 bytes)</td></tr>
		matches = re.search( r"""<tr><td.*?>Size</td><td.*?>.+ \((.+ bytes)\)</td></tr>""", description )
		if matches is None:
			logger.warning( "Size not found on torrent page." )
		else:
			size = matches.group( 1 )
			releaseInfo.Size = GetSizeFromText( size )

		self.__DownloadNfoParseSourceType( releaseInfo, description )
		self.__DownloadNfoParseFormatType( releaseInfo, description )
		
		# Make sure that this is not a wrongly categorized DVDR.
		if ( not releaseInfo.IsDvdImage() ) and ( re.search( r"<td>.+?\.vob</td>", description, re.IGNORECASE ) or re.search( r"<td>.+?\.iso</td>", description, re.IGNORECASE ) ):
			raise PtpUploaderException( JobRunningState.Ignored_NotSupported, "Wrongly categorized DVDR." )
	
	def PrepareDownload(self, logger, releaseInfo):
		if releaseInfo.IsUserCreatedJob():
			self.__DownloadNfo( logger, releaseInfo )
		else:
			# TODO: add filtering support for Karagarga
			# In case of automatic announcement we have to check the release name if it is valid.
			# We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source. 
			#if not ReleaseFilter.IsValidReleaseName( releaseInfo.ReleaseName ):
			#	logger.info( "Ignoring release '%s' because of its name." % releaseInfo.ReleaseName )
			#	return None
			self.__DownloadNfo( logger, releaseInfo )

		if releaseInfo.IsResolutionTypeSet():
			releaseInfo.Logger.info( "Resolution type '%s' is already set, not getting from the torrent page." % releaseInfo.ResolutionType )
		else:
			releaseInfo.ResolutionType = "Other"

	def DownloadTorrent(self, logger, releaseInfo, path):
		# Any non empty filename can be specified.
		url = "http://karagarga.net/down.php/%s/filename.torrent" % releaseInfo.AnnouncementId
		logger.info( "Downloading torrent file from '%s' to '%s'." % ( url, path ) )

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		self.__CheckIfLoggedInFromResponse( response )
		
		file = open( path, "wb" )
		file.write( response )
		file.close()

		ValidateTorrentFile( path )

	def IncludeReleaseNameInReleaseDescription(self):
		return False
	
	def GetIdFromUrl(self, url):
		result = re.match( r".*karagarga\.net/details.php\?id=(\d+).*", url )
		if result is None:
			return ""
		else:
			return result.group( 1 )	

	def GetUrlFromId(self, id):
		return "http://karagarga.net/details.php?id=" + id