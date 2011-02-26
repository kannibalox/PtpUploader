from Globals import Globals
from NfoParser import NfoParser
from PtpUploaderException import *
from ReleaseExtractor import ReleaseExtractor
from ReleaseInfo import ReleaseInfo
from ReleaseNameParser import ReleaseNameParser
from Settings import Settings

import re
import urllib
import urllib2

class TorrentLeech:
	def __init__(self):
		self.Name = "tl"
		self.MaximumParallelDownloads = Settings.TorrentLeechMaximumParallelDownloads
	
	@staticmethod
	def Login():
		Globals.Logger.info( "Logging in to TorrentLeech." )
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) )
		postData = urllib.urlencode( { "username": Settings.TorrentLeechUserName, "password": Settings.TorrentLeechPassword } )
		request = urllib2.Request( "http://www.torrentleech.org/user/account/login/", postData )
		result = opener.open( request )
		response = result.read()
		TorrentLeech.CheckIfLoggedInFromResponse( response )
	
	@staticmethod
	def CheckIfLoggedInFromResponse(response):
		if response.find( '<div class="recaptcha">' ) != -1:
			raise PtpUploaderInvalidLoginException( "Can't login to TorrentLeech because there is a captcha on the login page." )
		
		if response.find( '<form method="post" action="/user/account/login/">' ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to TorrentLeech. Probably due to the bad user name or password in settings." )

	# Release names on TL don't contain periods. This functions restore them.
	# Eg.: "Far From Heaven 2002 720p BluRay x264-HALCYON" instead of "Far.From.Heaven.2002.720p.BluRay.x264-HALCYON"
	@staticmethod
	def __RestoreReleaseName(releaseName):
		return releaseName.replace( " ", "." )
	
	@staticmethod
	def __GetReleaseName(logger, releaseInfo):
		url = "http://www.torrentleech.org/torrent/%s" % releaseInfo.AnnouncementId
		logger.info( "Downloading release name from page '%s'." % url )
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		TorrentLeech.CheckIfLoggedInFromResponse( response )

		# Get release name.
		matches = re.search( "<title>Torrent Details for (.+) :: TorrentLeech.org</title>", response )
		if matches is None:
			raise PtpUploaderException( "Release name can't be found on page '%s'." % url )

		return matches.group( 1 )

	@staticmethod
	def __GetNfo(logger, releaseInfo, getReleaseName = False):
		url = "http://www.torrentleech.org/torrents/torrent/nfotext?torrentID=%s" % releaseInfo.AnnouncementId
		logger.info( "Downloading NFO from page '%s'." % url )
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		TorrentLeech.CheckIfLoggedInFromResponse( response )

		return response

	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		# TODO: temp
		# TorrentLeech has a bad habit of logging out, so we put this here.
		TorrentLeech.Login()
		
		# In case of manual announcement we don't have the name, so get it.
		if releaseInfo.IsManualAnnouncement:
			releaseInfo.ReleaseName = TorrentLeech.__GetReleaseName( logger, releaseInfo )

		releaseInfo.ReleaseName = TorrentLeech.__RestoreReleaseName( releaseInfo.ReleaseName )
			
		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		releaseNameParser.GetSourceAndFormat( releaseInfo )

		# We don't have to check the release name of manual announcements. 
		if ( not releaseInfo.IsManualAnnouncement ) and ( not releaseNameParser.IsAllowed() ):
			logger.info( "Ignoring release '%s' because of its name." % releaseInfo.ReleaseName )
			return None

		# Download the NFO.
		nfoText = TorrentLeech.__GetNfo( logger, releaseInfo )
		releaseInfo.ImdbId = NfoParser.GetImdbId( nfoText )

		# Pretime is not indicated on TorrentLeech so we have to rely on our scene groups list.
		if releaseNameParser.Scene:
			releaseInfo.Scene = "on" 
		
		return releaseInfo
	
	@staticmethod
	def DownloadTorrent(logger, releaseInfo, path):
		# Filename in the URL could be anything.
		url = "http://www.torrentleech.org/download/%s/TL.torrent" % releaseInfo.AnnouncementId
		logger.info( "Downloading torrent file from '%s' to '%s'." % ( url, path ) )

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) )		
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		TorrentLeech.CheckIfLoggedInFromResponse( response )
		
		file = open( path, "wb" )
		file.write( response )
		file.close()

		# If a torrent contains multiple NFO files then it is likely that the site also showed the wrong NFO and we have checked the existence of another movie on PTP.
		# So we abort here. These errors happen rarely anyway.
		# (We could also try read the NFO with the same name as the release or with the same name as the first RAR and reschedule for checking with the correct IMDb id.)
		if NfoParser.IsTorrentContainsMultipleNfos( path ):
			raise PtpUploaderException( "Torrent '%s' contains multiple NFO files." % path )  

	@staticmethod
	def ExtractRelease(logger, releaseInfo):
		# Extract the release.
		nfoPath = ReleaseExtractor.Extract( releaseInfo.GetReleaseDownloadPath(), releaseInfo.GetReleaseUploadPath() )
		if nfoPath is not None:
			releaseInfo.Nfo = NfoParser.ReadNfoFileToUnicode( nfoPath )

	@staticmethod
	def RenameRelease(logger, releaseInfo):
		pass
				
	@staticmethod
	def IsSingleFileTorrentNeedsDirectory():
		return True
	
	@staticmethod
	def IncludeReleaseNameInReleaseDescription():
		return True