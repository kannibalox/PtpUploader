from Job.JobRunningState import JobRunningState
from Source.SourceBase import SourceBase

from Helper import DecodeHtmlEntities, GetSizeFromText, MakeRetryingHttpRequest, RemoveDisallowedCharactersFromPath
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

class HDTorrents( SourceBase ):
	RequiredHttpHeader = { 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
		'Referer': 'https://hd-torrents.org',
		'Origin': 'https://hd-torrents.org' }

	def __init__( self ):
		SourceBase.__init__( self )

		self.Name = "hdts"
		self.NameInSettings = "HDTorrents"

	def LoadSettings( self, settings ):
		SourceBase.LoadSettings( self, settings )

	def IsEnabled( self ):
		return len( self.Username ) > 0 and len( self.Password ) > 0

	def Login( self ):
		MyGlobals.Logger.info( "Logging in to HD-Torrents." )
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		postData = urllib.urlencode( { "uid": self.Username, "pwd": self.Password } )
		request = urllib2.Request( "https://hd-torrents.org/login.php", postData, headers=HDTorrents.RequiredHttpHeader )
		result = opener.open( request )
		response = result.read()
		self.CheckIfLoggedInFromResponse( response );

	def CheckIfLoggedInFromResponse( self, response ):
		if response.find( 'form action="login.php""' ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to HDTorrents. Probably due to the bad user name or password in settings." )

	# Sets IMDb if presents in the torrent description.
	# Returns with the release name.
	def __ReadTorrentPage( self, logger, releaseInfo ):
		url = "http://hd-torrents.org/details.php?id=%s" % releaseInfo.AnnouncementId
		logger.info( "Downloading NFO from page '%s'." % url )
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( url, headers=HDTorrents.RequiredHttpHeader )
		result = opener.open( request )
		response = result.read()
		response = response.decode( "utf-8", "ignore" )
		self.CheckIfLoggedInFromResponse( response )

		# Make sure we only get information from the description and not from the comments.
		descriptionEndIndex = response.find( """<a name="comments" />""" )
		if descriptionEndIndex == -1:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Description can't be found. Probably the layout of the site has changed." )

		description = response[ :descriptionEndIndex ]

		# Get release name.
		matches = re.search( r"""File Name</td><td class="detailsright" align="center">(.*)</a><br><small>""", description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Release name can't be found on torrent page." )

		releaseName = DecodeHtmlEntities( matches.group( 1 ) )

		# Get IMDb id.
		if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
			releaseInfo.ImdbId = NfoParser.GetImdbId( description )

		# Get size.
		matches = re.search( r"""Size:</td><td class="detailsright" align="left">(.*)</td>""", description )
		if matches is None:
			logger.warning( "Size not found on torrent page." )
		else:
			size = matches.group( 1 )
			releaseInfo.Size = GetSizeFromText( size )

		# Store the download URL.
		#<a href="download.php?id=c787dc1e59f6245c159a02f4402a089141933f4d&f=Hand+Of+God+S01E01+Pilot+720p+WEBRip+x264-W4F+.torrent">
		matches = re.search( r"""<a href="download.php\?(.+?)">""", description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Download link can't be found on torrent page." )
		releaseInfo.SceneAccessDownloadUrl = "http://hd-torrents.org/download.php?" + matches.group( 1 )
		return releaseName

	def __HandleUserCreatedJob( self, logger, releaseInfo ):
		releaseName = self.__ReadTorrentPage( logger, releaseInfo )
		if not releaseInfo.IsReleaseNameSet():
			releaseInfo.ReleaseName = RemoveDisallowedCharactersFromPath( releaseName )

		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		isAllowedMessage = releaseNameParser.IsAllowed()
		if isAllowedMessage is not None:
			raise PtpUploaderException( JobRunningState.Ignored, isAllowedMessage )

		releaseNameParser.GetSourceAndFormat( releaseInfo )
		if releaseNameParser.Scene:
			releaseInfo.SetSceneRelease()

	def __HandleAutoCreatedJob( self, logger, releaseInfo ):
		# In case of automatic announcement we have to check the release name if it is valid.
		# We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source.

		releaseInfo.ReleaseName = self.__ReadTorrentPage( logger, releaseInfo )
		releaseInfo.ReleaseName = RemoveDisallowedCharactersFromPath( releaseInfo.ReleaseName )

		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		isAllowedMessage = releaseNameParser.IsAllowed()
		if isAllowedMessage is not None:
			raise PtpUploaderException( JobRunningState.Ignored, isAllowedMessage )

		releaseNameParser.GetSourceAndFormat( releaseInfo )

		if releaseNameParser.Scene:
			releaseInfo.SetSceneRelease()

		if ( not releaseInfo.IsSceneRelease() ) and self.AutomaticJobFilter == "SceneOnly":
			raise PtpUploaderException( JobRunningState.Ignored, "Non-scene release." )

	def PrepareDownload( self, logger, releaseInfo ):
		if releaseInfo.IsUserCreatedJob():
			self.__HandleUserCreatedJob( logger, releaseInfo )
		else:
			self.__HandleAutoCreatedJob( logger, releaseInfo )

	def DownloadTorrent( self, logger, releaseInfo, path ):
		# This can't happen.
		if len( releaseInfo.SceneAccessDownloadUrl ) <= 0:
			raise PtpUploaderException( "Download URL is not set." )

		# We don't log the download URL because it is sensitive information.
		logger.info( "Downloading torrent file from HD-Torrents to '%s'." % path )

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( releaseInfo.SceneAccessDownloadUrl, headers=HDTorrents.RequiredHttpHeader )
		result = opener.open( request )
		response = result.read()
		self.CheckIfLoggedInFromResponse( response );

		file = open( path, "wb" );
		file.write( response );
		file.close();

		# Calling Helper.ValidateTorrentFile is not needed because NfoParser.IsTorrentContainsMultipleNfos will throw an exception if it is not a valid torrent file.

		# If a torrent contains multiple NFO files then it is likely that the site also showed the wrong NFO and we have checked the existence of another movie on PTP.
		# So we abort here. These errors happen rarely anyway.
		# (We could also try read the NFO with the same name as the release or with the same name as the first RAR and reschedule for checking with the correct IMDb id.)
		if NfoParser.IsTorrentContainsMultipleNfos( path ):
			raise PtpUploaderException( "Torrent '%s' contains multiple NFO files." % path )

	def GetIdFromUrl( self, url ):
		result = re.match( r".*hd-torrents\.org/download\.php\?id=(\s+).*", url )
		if result is None:
			return ""
		else:
			return result.group( 1 )

	def GetUrlFromId( self, id ):
		return "http://hd-torrents.org/details.php?id=" + id

	def GetIdFromAutodlIrssiUrl( self, url ):
		# https://hd-torrents.org//download.php?id=808b75cd4c5517d5a3001becb3b7c6ce5274ca62&f=Brief%20Encounter%201945%20720p%20BluRay%20FLAC%20x264-HDB.torrent
		result = re.match( r".*hd-torrents\.org\/\/download\.php\?id=(\w+)&f", url )
		if result is None:
			return ""
		else:
			return DecodeHtmlEntities( result.group( 1 ))
