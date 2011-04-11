from Job.JobRunningState import JobRunningState
from Source.SourceBase import SourceBase

from Helper import GetSizeFromText
from MyGlobals import MyGlobals
from NfoParser import NfoParser
from PtpUploaderException import *
from ReleaseExtractor import ReleaseExtractor
from ReleaseInfo import ReleaseInfo
from ReleaseNameParser import ReleaseNameParser
from Settings import Settings

import re
import urllib
import urllib2

class TorrentLeech(SourceBase):
	def __init__(self):
		self.Name = "tl"
		self.MaximumParallelDownloads = Settings.TorrentLeechMaximumParallelDownloads

	@staticmethod
	def IsEnabled():
		return len( Settings.TorrentLeechUserName ) > 0 and len( Settings.TorrentLeechPassword ) > 0

	@staticmethod
	def Login():
		MyGlobals.Logger.info( "Logging in to TorrentLeech." )
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
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

	# Release names on TL don't contain periods. This function restores them.
	# Eg.: "Far From Heaven 2002 720p BluRay x264-HALCYON" instead of "Far.From.Heaven.2002.720p.BluRay.x264-HALCYON"
	@staticmethod
	def __RestoreReleaseName(releaseName):
		return releaseName.replace( " ", "." )
	
	# On TorrentLeech the torrent page doesn't contain the NFO, and the NFO page doesn't contain the release name so we have to read them separately. 
	@staticmethod
	def __GetReleaseNameAndSize(logger, releaseInfo):
		url = "http://www.torrentleech.org/torrent/%s" % releaseInfo.AnnouncementId
		logger.info( "Downloading release name and size from page '%s'." % url )
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		TorrentLeech.CheckIfLoggedInFromResponse( response )

		# Get release name.
		matches = re.search( "<title>Torrent Details for (.+) :: TorrentLeech.org</title>", response )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Release name can't be found on torrent page." )
		releaseName = TorrentLeech.__RestoreReleaseName( matches.group( 1 ) )

		# Get size.
		# <td class="label">Size</td><td>5.47 GB</td></tr>
		size = 0
		matches = re.search( r"""<td class="label">Size</td><td>(.+)</td></tr>""", response )
		if matches is None:
			logger.warning( "Size not found on torrent page." )
		else:
			size = GetSizeFromText( matches.group( 1 ) )

		return releaseName, size

	# On TorrentLeech the torrent page doesn't contain the NFO, and the NFO page doesn't contain the release name so we have to read them separately. 
	@staticmethod
	def __ReadImdbIdFromNfoPage(logger, releaseInfo):
		if releaseInfo.HasImdbId() or releaseInfo.HasPtpId():
			return
		
		url = "http://www.torrentleech.org/torrents/torrent/nfotext?torrentID=%s" % releaseInfo.AnnouncementId
		logger.info( "Downloading NFO from page '%s'." % url )
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		TorrentLeech.CheckIfLoggedInFromResponse( response )

		releaseInfo.ImdbId = NfoParser.GetImdbId( response )
	
	@staticmethod
	def __HandleUserCreatedJob(logger, releaseInfo):
		if ( not releaseInfo.IsReleaseNameSet() ) or releaseInfo.Size == 0:
			releaseName, releaseInfo.Size = TorrentLeech.__GetReleaseNameAndSize( logger, releaseInfo )
			if not releaseInfo.IsReleaseNameSet():
				releaseInfo.ReleaseName = releaseName

		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		releaseNameParser.GetSourceAndFormat( releaseInfo )

		# Pretime is not indicated on TorrentLeech so we have to rely on our scene groups list.
		if releaseNameParser.Scene:
			releaseInfo.SetSceneRelease()

		TorrentLeech.__ReadImdbIdFromNfoPage( logger, releaseInfo )

	@staticmethod
	def __HandleAutoCreatedJob(logger, releaseInfo):
		releaseInfo.ReleaseName = TorrentLeech.__RestoreReleaseName( releaseInfo.ReleaseName )
		
		# In case of automatic announcement we have to check the release name if it is valid.
		# We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source.
		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		if not releaseNameParser.IsAllowed():
			raise PtpUploaderException( JobRunningState.Ignored, "Ignored because of its name." )

		releaseNameParser.GetSourceAndFormat( releaseInfo )
		
		releaseName, releaseInfo.Size = TorrentLeech.__GetReleaseNameAndSize( logger, releaseInfo )
		if releaseName != releaseInfo.ReleaseName:
			raise PtpUploaderException( "Announcement release name '%s' and release name '%s' on page '%s' are different." % ( releaseInfo.ReleaseName, releaseName, url ) )

		# Pretime is not indicated on TorrentLeech so we have to rely on our scene groups list.
		if releaseNameParser.Scene:
			releaseInfo.SetSceneRelease()

		if ( not releaseInfo.IsSceneRelease() ) and Settings.TorrentLeechAutomaticJobFilter == "SceneOnly":
			raise PtpUploaderException( JobRunningState.Ignored, "Non-scene release." )

		TorrentLeech.__ReadImdbIdFromNfoPage( logger, releaseInfo )
	
	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		# TODO: temp
		# TorrentLeech has a bad habit of logging out, so we put this here.
		TorrentLeech.Login()
		
		if releaseInfo.IsUserCreatedJob():
			TorrentLeech.__HandleUserCreatedJob( logger, releaseInfo )
		else:
			TorrentLeech.__HandleAutoCreatedJob( logger, releaseInfo )
	
	@staticmethod
	def DownloadTorrent(logger, releaseInfo, path):
		# Filename in the URL could be anything.
		url = "http://www.torrentleech.org/download/%s/TL.torrent" % releaseInfo.AnnouncementId
		logger.info( "Downloading torrent file from '%s' to '%s'." % ( url, path ) )

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )		
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
	def GetIdFromUrl(url):
		result = re.match( r".*torrentleech\.org/torrent/(\d+).*", url )
		if result is None:
			return ""
		else:
			return result.group( 1 )

	@staticmethod
	def GetUrlFromId(id):
		return "http://www.torrentleech.org/torrent/" + id