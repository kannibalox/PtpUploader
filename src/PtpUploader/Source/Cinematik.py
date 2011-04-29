from InformationSource.Imdb import Imdb
from Job.JobRunningState import JobRunningState
from Source.SourceBase import SourceBase

from Helper import GetSizeFromText, GetFileListFromTorrent
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

class Cinematik(SourceBase):
	def __init__(self):
		self.Name = "tik"
		self.MaximumParallelDownloads = Settings.CinematikMaximumParallelDownloads
	
	@staticmethod
	def IsEnabled():
		return len( Settings.CinematikUserName ) > 0 and len( Settings.CinematikPassword ) > 0

	@staticmethod
	def Login():
		MyGlobals.Logger.info( "Loggin in to Cinematik." )

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		postData = urllib.urlencode( { "username": Settings.CinematikUserName, "password": Settings.CinematikPassword } )
		result = opener.open( "http://cinematik.net/takelogin.php", postData )
		response = result.read()
		Cinematik.__CheckIfLoggedInFromResponse( response )
	
	@staticmethod
	def __CheckIfLoggedInFromResponse(response):
		if response.find( 'action="takelogin.php"' ) != -1 or response.find( "<h2>Login failed!</h2>" ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to Cinematik. Probably due to the bad user name or password in settings." )

	@staticmethod
	def __DownloadNfo(logger, releaseInfo):
		url = "http://cinematik.net/details.php?id=%s&filelist=1" % releaseInfo.AnnouncementId
		logger.info( "Collecting info from torrent page '%s'." % url )
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		result = opener.open( url )
		response = result.read()
		response = response.decode( "ISO-8859-1", "ignore" )
		Cinematik.__CheckIfLoggedInFromResponse( response )

		# Make sure we only get information from the description and not from the comments.
		descriptionEndIndex = response.find( '<p><a name="startcomments"></a></p>' )
		if descriptionEndIndex == -1:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Description can't found on torrent page. Probably the layout of the site has changed." )
		
		description = response[ :descriptionEndIndex ]			

		# We will use the torrent's name as release name.
		matches = re.search( r'href="download.php\?id=(\d+)".+?>(.+)\.torrent</a>', description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Can't get release name from torrent page." )
		
		releaseInfo.ReleaseName = matches.group( 2 )

		# Get source and format type
		# <title>Cinematik :: Behind the Mask: The Rise of Leslie Vernon (2006) NTSC DVD9 VIDEO_TS</title>
		matches = re.search( r"<title>Cinematik :: .+? \(\d+\) (.+?) (.+?) (.+?)</title>", description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Can't get resolution type, codec and container from torrent page." )

		resolutionType = matches.group( 1 )
		codec = matches.group( 2 )
		container = matches.group( 3 )

		# Get IMDb id.
		if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
			matches = re.search( r"imdb\.com/title/tt(\d+)", description )
			if matches is None:
				raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "IMDb id can't be found on torrent page." )

			releaseInfo.ImdbId = matches.group( 1 )

		# Get size.
		# <td class="heading" align="right" valign="top">Size</td><td align="left" valign="top">6.81 GB &nbsp;&nbsp;&nbsp;(7,313,989,632 bytes)</td>
		matches = re.search( r"""<td class="heading" align="right" valign="top">Size</td><td align="left" valign="top">.+\((.+ bytes)\)</td>""", description )
		if matches is None:
			logger.warning( "Size not found on torrent page." )
		else:
			size = matches.group( 1 )
			releaseInfo.Size = GetSizeFromText( size )

		return resolutionType, codec, container

	@staticmethod
	def __MapInfoFromTorrentDescriptionToPtp(releaseInfo, resolutionType, codec, container):
		resolutionType = resolutionType.lower()
		codec = codec.lower()
		container = container.lower()

		if releaseInfo.IsResolutionTypeSet():
			releaseInfo.Logger.info( "Resolution type '%s' is already set, not getting from the torrent page." % releaseInfo.ResolutionType )
		elif resolutionType == "ntsc":
			releaseInfo.ResolutionType = "NTSC"
		elif resolutionType == "pal":
			releaseInfo.ResolutionType = "PAL"
		else:
			raise PtpUploaderException( JobRunningState.Ignored_NotSupported, "Unsupported resolution type '%s'." % resolutionType )

		if releaseInfo.IsCodecSet() and releaseInfo.IsSourceSet():
			releaseInfo.Logger.info( "Codec '%s' and source '%s' are already set, not getting from the torrent page." % ( releaseInfo.Codec, releaseInfo.Source ) )
		elif codec == "dvd5":
			releaseInfo.Codec = "DVD5"
			releaseInfo.Source = "DVD"
		elif codec == "dvd9":
			releaseInfo.Codec = "DVD9"
			releaseInfo.Source = "DVD"
		else:
			raise PtpUploaderException( JobRunningState.Ignored_NotSupported, "Unsupported codec type '%s'." % codec )

		if releaseInfo.IsContainerSet():
			releaseInfo.Logger.info( "Container '%s' is already set, not getting from the torrent page." % releaseInfo.Container )
		elif container == "video_ts" or container == "video_ts [widescreen]":
			releaseInfo.Container = "VOB IFO"
		else:
			raise PtpUploaderException( JobRunningState.Ignored_NotSupported, "Unsupported container type '%s'." % container )
	
	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		resolutionType = ""
		codec = ""
		container = ""
		
		if releaseInfo.IsUserCreatedJob():
			resolutionType, codec, container = Cinematik.__DownloadNfo( logger, releaseInfo )
		else:
			# TODO: add filterting support for Cinematik
			resolutionType, codec, container = Cinematik.__DownloadNfo( logger, releaseInfo )

		Cinematik.__MapInfoFromTorrentDescriptionToPtp( releaseInfo, resolutionType, codec, container )

	@staticmethod
	def __ValidateTorrentFile(torrentPath):
		files = GetFileListFromTorrent( torrentPath )
		for file in files:
			file = file.lower();
			
			# Make sure it doesn't contains ISO files.  
			if file.endswith( ".iso" ):
				raise PtpUploaderException( JobRunningState.Ignored_NotSupported, "Found an ISO file in the torrent." )

			# Make sure that all files are in the VIDEO_TS folder. (This is needed because of the uploading rules on PTP.)  
			if file.startswith( "video_ts" ):
				raise PtpUploaderException( JobRunningState.Ignored_NotSupported, "Files are not in the VIDEO_TS folder in the torrent." )

	@staticmethod
	def DownloadTorrent(logger, releaseInfo, path):
		url = "http://cinematik.net/download.php?id=%s" % releaseInfo.AnnouncementId
		logger.info( "Downloading torrent file from '%s' to '%s'." % ( url, path ) )

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		result = opener.open( url )
		response = result.read()
		Cinematik.__CheckIfLoggedInFromResponse( response )
		
		file = open( path, "wb" )
		file.write( response )
		file.close()

		Cinematik.__ValidateTorrentFile( path )
		
	@staticmethod
	def ExtractRelease(logger, releaseInfo):
		# Extract the release.
		ReleaseExtractor.Extract( releaseInfo.GetReleaseDownloadPath(), releaseInfo.GetReleaseUploadPath() )
		releaseInfo.Nfo = NfoParser.FindAndReadNfoFileToUnicode( releaseInfo.GetReleaseDownloadPath() )

	# TODO: Cinematik: move this to helper.py
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

	# TODO: Cinematik: use a shared function with Cinemageddon
	# Because some of the releases on Cinematik do not contain the full name of the movie, we have to rename them because of the uploading rules on PTP.
	# The new name will be formatted like this: Movie Name Year
	@staticmethod
	def GetCustomUploadPath(logger, releaseInfo):
		# TODO: if the user forced a release name, then let it upload by that name.
		if releaseInfo.IsZeroImdbId():
			raise PtpUploaderException( "Uploading to Cinematik with zero IMDb ID is not yet supported." % text ) 		
		
		# If the movie already exists on PTP then the IMDb info is not populated in ReleaseInfo.
		if len( releaseInfo.InternationalTitle ) <= 0 or len( releaseInfo.Year ) <= 0:
			imdbInfo = Imdb.GetInfo( logger, releaseInfo.GetImdbId() )
			if len( releaseInfo.InternationalTitle ) <= 0:
				releaseInfo.InternationalTitle = imdbInfo.Title
			if len( releaseInfo.Year ) <= 0:
				releaseInfo.Year = imdbInfo.Year

		name = "%s (%s)" % ( releaseInfo.InternationalTitle, releaseInfo.Year )
		name = Cinematik.__RemoveNonAllowedCharacters( name )

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
		result = re.match( r".*cinematik\.net/details.php\?id=(\d+).*", url )
		if result is None:
			return ""
		else:
			return result.group( 1 )	

	@staticmethod
	def GetUrlFromId(id):
		return "http://cinematik.net/details.php?id=" + id