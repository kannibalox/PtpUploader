from Job.JobRunningState import JobRunningState
from Source.SourceBase import SourceBase

from Helper import GetSizeFromText
from MyGlobals import MyGlobals
from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor
from ReleaseInfo import ReleaseInfo
from ReleaseNameParser import ReleaseNameParser

import re
import time
import urllib
import urllib2

class TheDarkSyndicate(SourceBase):
	def __init__(self):
		SourceBase.__init__( self )

		self.Name = "tds"
		self.NameInSettings = "TheDarkSyndicate"

	def IsEnabled(self):
		return len( self.Username ) > 0 and len( self.Password ) > 0

	def Login(self):
		MyGlobals.Logger.info( "Logging in to The Dark Syndicate." )
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		postData = urllib.urlencode( { "username": self.Username, "password": self.Password } )
		result = opener.open( "http://thedarksyndicate.me/login.php", postData )
		response = result.read()
		self.CheckIfLoggedInFromResponse( response )

	def CheckIfLoggedInFromResponse(self, response):
		if response.find( """<a href="login.php"><p>Login</p></a>""" ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to TDS. Probably due to the bad user name or password in settings." )

	# Sets IMDb if presents in the torrent description.
	# Sets scene release if pretime presents on the page.
	# Returns with the release name.
	def __ReadTorrentPage(self, logger, releaseInfo):
		url = self.GetUrlFromId( releaseInfo.AnnouncementId )
		logger.info( "Downloading NFO from page '%s'." % url )

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		self.CheckIfLoggedInFromResponse( response )

		# Make sure we only get information from the description and not from the comments.
		descriptionEndIndex = response.find( "<h2>Torrent Comments</h2>" )
		if descriptionEndIndex == -1:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Description can't found. Probably the layout of the site has changed." )

		description = response[ :descriptionEndIndex ]

		# Get the torrent ID if we don't have it.
		groupId, torrentId = TheDarkSyndicate.__GetGroupAndTorrentIdFromId( releaseInfo.AnnouncementId )
		if int( torrentId ) <= 0:
			matches = re.search( r"This torrent id is (\d+).", description )
			if matches is None:
				raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Torrent ID can't be found on the torrent page." )
			else:
				torrentId = matches.group( 1 )
				releaseInfo.AnnouncementId = TheDarkSyndicate.__MakeIdFromGroupAndTorrentId( groupId, torrentId )

		# Get release name.
		matches = re.search( r"<h2>Details For (.+?)</h2>", description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Release name can't be found on torrent page." )

		releaseName = matches.group( 1 )

		# Get IMDb id.
		if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
			releaseInfo.ImdbId = NfoParser.GetImdbId( description )

		# Get size.
		# Because of the layout of the site the size is below the comments (in HTML source), so we parse the original response here.
		matches = re.search( r"""<td>\s*<div.*?>Size<\/div>\s*<\/td>\s*<td>\s*<div.*?>(.+?)<\/div>\s*<\/td>""", response, re.DOTALL )
		if matches is None:
			logger.warning( "Size not found on torrent page." )
		else:
			size = matches.group( 1 )
			releaseInfo.Size = GetSizeFromText( size )

		return releaseName

	def __HandleUserCreatedJob(self, logger, releaseInfo):
		releaseName = self.__ReadTorrentPage( logger, releaseInfo )
		if not releaseInfo.IsReleaseNameSet():
			releaseInfo.ReleaseName = releaseName

		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		releaseNameParser.GetSourceAndFormat( releaseInfo )
		if releaseNameParser.Scene:
			releaseInfo.SetSceneRelease()

	def __HandleAutoCreatedJob(self, logger, releaseInfo):
		# In case of automatic announcement we have to check the release name if it is valid.
		# We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source.
		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		isAllowedMessage = releaseNameParser.IsAllowed()
		if isAllowedMessage is not None:
			raise PtpUploaderException( JobRunningState.Ignored, isAllowedMessage )

		releaseNameParser.GetSourceAndFormat( releaseInfo )

		releaseName = self.__ReadTorrentPage( logger, releaseInfo )
		if releaseName != releaseInfo.ReleaseName:
			raise PtpUploaderException( "Announcement release name '%s' and release name '%s' on TDS are different." % ( releaseInfo.ReleaseName, releaseName ) )

		if releaseNameParser.Scene:
			releaseInfo.SetSceneRelease()

		if ( not releaseInfo.IsSceneRelease() ) and self.AutomaticJobFilter == "SceneOnly":
			raise PtpUploaderException( JobRunningState.Ignored, "Non-scene release." )

	def PrepareDownload(self, logger, releaseInfo):
		if releaseInfo.IsUserCreatedJob():
			self.__HandleUserCreatedJob( logger, releaseInfo )
		else:
			self.__HandleAutoCreatedJob( logger, releaseInfo )

	def DownloadTorrent(self, logger, releaseInfo, path):
		groupId, torrentId = TheDarkSyndicate.__GetGroupAndTorrentIdFromId( releaseInfo.AnnouncementId )

		# This can't happen unless if PrepareDownload hasn't been called.
		if int( torrentId ) <= 0:
			raise PtpUploaderException( "Torrent ID is missing for group ID %s." % groupId )

		url = "http://thedarksyndicate.me/browse.php?action=download&id=%s" % torrentId
		logger.info( "Downloading torrent file from '%s' to '%s'." % ( url, path ) )

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		self.CheckIfLoggedInFromResponse( response )

		file = open( path, "wb" )
		file.write( response )
		file.close()

		# Calling Helper.ValidateTorrentFile is not needed because NfoParser.IsTorrentContainsMultipleNfos will throw an exception if it is not a valid torrent file.

		# If a torrent contains multiple NFO files then it is likely that the site also showed the wrong NFO and we have checked the existence of another movie on PTP.
		# So we abort here. These errors happen rarely anyway.
		# (We could also try read the NFO with the same name as the release or with the same name as the first RAR and reschedule for checking with the correct IMDb id.)
		if NfoParser.IsTorrentContainsMultipleNfos( path ):
			raise PtpUploaderException( "Torrent '%s' contains multiple NFO files." % path )  

	# Because the tracker is Gazelle-based we need to know which ID are we working with.
	# The easiest way is store both.
	@staticmethod
	def __MakeIdFromGroupAndTorrentId( groupId, torrentId ):
		id = "%s,%s" % ( groupId, torrentId )
		return id

	# See the comment at MakeIdFromGroupAndTorrentId.
	@staticmethod
	def __GetGroupAndTorrentIdFromId( id ):
		groupId, torrentId = id.split( "," )
		return groupId, torrentId

	def GetIdFromUrl( self, url ):
		result = re.match( r".*thedarksyndicate\.me/browse\.php\?id=(\d+).*", url )
		if result is not None:
			return TheDarkSyndicate.__MakeIdFromGroupAndTorrentId( result.group( 1 ), 0 )

		result = re.match( r".*thedarksyndicate\.me/browse\.php\?action=details&torrentid=(\d+).*", url )
		if result is None:
			return ""
		else:
			return TheDarkSyndicate.__MakeIdFromGroupAndTorrentId( 0, result.group( 1 ) )

	def GetUrlFromId( self, id ):
		groupId, torrentId = TheDarkSyndicate.__GetGroupAndTorrentIdFromId( id )
		if groupId > 0:
			return "http://thedarksyndicate.me/browse.php?id=" + groupId
		else:
			return "http://thedarksyndicate.me/browse.php?action=details&torrentid=" + torrentId
