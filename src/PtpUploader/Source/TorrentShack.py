from Job.JobRunningState import JobRunningState
from Source.SourceBase import SourceBase

from Helper import DecodeHtmlEntities, GetSizeFromText, MakeRetryingHttpGetRequestWithRequests, MakeRetryingHttpPostRequestWithRequests
from MyGlobals import MyGlobals
from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor
from ReleaseInfo import ReleaseInfo
from ReleaseNameParser import ReleaseNameParser

import re
import time

class TorrentShack( SourceBase ):
	def __init__( self ):
		SourceBase.__init__( self )

		self.Name = "tsh"
		self.NameInSettings = "TorrentShack"

	def LoadSettings( self, settings ):
		SourceBase.LoadSettings( self, settings )

	def IsEnabled( self ):
		return len( self.Username ) > 0 and len( self.Password ) > 0

	def Login( self ):
		MyGlobals.Logger.info( "Logging in to TorrentShack." )

		# Check the "keep logged in?" checkbox, otherwise we lose our loginsession after some time.
		postData = { "username": self.Username, "password": self.Password, "keeplogged": "1" }

		result = MakeRetryingHttpPostRequestWithRequests( "http://torrentshack.eu/login.php", postData )
		self.CheckIfLoggedInFromResponse( result.text )

	def CheckIfLoggedInFromResponse( self, response ):
		if response.find( 'action="login.php"' ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to TorrentShack. Probably due to the bad user name or password in settings." )

	# Sets IMDb if presents in the torrent description.
	# Returns with the release name.
	def __ReadTorrentPage( self, logger, releaseInfo ):
		url = "http://torrentshack.eu/torrents.php?torrentid=%s" % releaseInfo.AnnouncementId
		logger.info( "Downloading NFO from page '%s'." % url )

		result = MakeRetryingHttpGetRequestWithRequests( url )
		response = result.text
		self.CheckIfLoggedInFromResponse( response )

		# Make sure we only get information from the description and not from the comments.
		descriptionEndIndex = response.find( """<a name="comments">""" )
		if descriptionEndIndex == -1:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Description can't found. Probably the layout of the site has changed." )

		description = response[ :descriptionEndIndex ]

		# Get release name.
		matches = re.search( r"""<title>(.+) :: TorrentShack.eu</title>""", description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Release name can't be found on torrent page." )

		releaseName = DecodeHtmlEntities( matches.group( 1 ) )

		# Get IMDb id.
		if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
			releaseInfo.ImdbId = NfoParser.GetImdbId( description )

		# Get size.
		matches = re.search( r"""<td class="nobr">(.+)</td>""", description )
		if matches is None:
			logger.warning( "Size not found on torrent page." )
		else:
			size = matches.group( 1 )
			releaseInfo.Size = GetSizeFromText( size )

		# Store the download URL.
		#<a href="torrents.php?action=download&amp;id=562922&amp;authkey=XXXXXXXXXXXXX&amp;torrent_pass=XXXXXXXXXXX" title="Download">DL</a>
		matches = re.search( r"""<a href="torrents.php?(.+?)" title="Download">DL</a>""", description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Download link can't be found on torrent page." )
		# We have to change "&amp;" to "&".
		releaseInfo.SceneAccessDownloadUrl = "http://torrentshack.eu/torrents.php" + matches.group( 1 ).replace("&amp;", "&")
		return releaseName

	def __HandleUserCreatedJob( self, logger, releaseInfo ):
		releaseName = self.__ReadTorrentPage( logger, releaseInfo )
		if not releaseInfo.IsReleaseNameSet():
			releaseInfo.ReleaseName = releaseName

		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		releaseNameParser.GetSourceAndFormat( releaseInfo )
		if releaseNameParser.Scene:
			releaseInfo.SetSceneRelease()

	def __HandleAutoCreatedJob( self, logger, releaseInfo ):
		# In case of automatic announcement we have to check the release name if it is valid.
		# We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source.
		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		isAllowedMessage = releaseNameParser.IsAllowed()
		if isAllowedMessage is not None:
			raise PtpUploaderException( JobRunningState.Ignored, isAllowedMessage )

		releaseNameParser.GetSourceAndFormat( releaseInfo )

		releaseName = self.__ReadTorrentPage( logger, releaseInfo )
		if releaseName != releaseInfo.ReleaseName:
			raise PtpUploaderException( "Announcement release name '%s' and release name '%s' on TorrentShack are different." % ( releaseInfo.ReleaseName, releaseName ) )

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
		logger.info( "Downloading torrent file from TorrentShack to '%s'." % path )

		result = MakeRetryingHttpGetRequestWithRequests( releaseInfo.SceneAccessDownloadUrl )
		response = result.content
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

	def GetIdFromUrl( self, url ):
		result = re.match( r".*torrentshack\.eu/torrents.php\?torrentid=(\d+).*", url )
		if result is None:
			return ""
		else:
			return result.group( 1 )

	def GetUrlFromId( self, id ):
		return "http://torrentshack.eu/torrents.php?torrentid=" + id

	def GetIdFromAutodlIrssiUrl( self, url ):
		# http://www.torrentshack.eu/torrents.php?action=diwnload&id=12345
		result = re.match( r".*torrentshack\.eu\/torrents\.php\?action=download\&id=(\d+).*", url )
		if result is None:
			return ""
		else:
			return result.group( 1 )
