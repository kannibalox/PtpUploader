from Job.JobRunningState import JobRunningState
from Source.SourceBase import SourceBase

from Helper import DecodeHtmlEntities, GetSizeFromText, RemoveDisallowedCharactersFromPath
from MyGlobals import MyGlobals
from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor
from ReleaseInfo import ReleaseInfo
from ReleaseNameParser import ReleaseNameParser

import re
import time
import requests
import json

class HDBits( SourceBase ):
	def __init__( self ):
		SourceBase.__init__( self )
		self.Name = "hdbits"
		self.NameInSettings = "HDBits"

	def LoadSettings( self, settings ):
		SourceBase.LoadSettings( self, settings )
		self.Password = settings.GetDefault( self.NameInSettings, "Passkey", "" )

	def IsEnabled( self ):
		return len( self.Username ) > 0 and len( self.Password ) > 0

	def Login( self ):
		MyGlobals.Logger.info( "Logging in to HDBits." )
		url = 'https://hdbits.org/api/test'
		data = { "username": self.Username, "passkey": self.Password }
		response = requests.post( url, json.dumps( data ) )
		self.__CheckIfLoggedInFromResponse( response );

	def __CheckIfLoggedInFromResponse( self, response ):
		if response.json()[ 'status' ] != 0:
			raise PtpUploaderException( "Looks like you are not logged in to HDBits. Probably due to the bad user name or password in settings." )

	# Sets IMDb if presents in the torrent description.
	# Returns with the release name.
	def __ReadTorrentPage( self, logger, releaseInfo ):
		url = "https://hdbits.org/api/torrents"
		logger.info( "Downloading NFO from page '%s'." % url )
		data = { "username": self.Username, "passkey": self.Password, "id": releaseInfo.AnnouncementId }
		response = requests.post( url, json.dumps( data ) )
		self.__CheckIfLoggedInFromResponse( response )

		# Make sure we only get information from the description and not from the comments.
		if response.json()[ 'status' ] != 0:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Description can't be found. Probably the layout of the site has changed." )

		# Get release name.

		releaseName = response.json()[ 'data' ][ 0 ][ 'name' ]
		if releaseName is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Release name can't be found on torrent page." )


		# Get IMDb id.
		if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
			releaseInfo.ImdbId = str( response.json()[ 'data' ][ 0 ][ 'imdb' ][ 'id' ] )

		# Get size.
		size = response.json()[ 'data' ][ 0 ][ 'size' ]
		if size is None:
			logger.warning( "Size not found on torrent page." )
		else:
			releaseInfo.Size = size

		# Store the download URL.
		fn = response.json()[ 'data' ][ 0 ][ 'filename' ]
		if fn is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Download link can't be found on torrent page." )
		releaseInfo.SceneAccessDownloadUrl = "https://hdbits.org/download.php/" + fn + "?id=" + releaseInfo.AnnouncementId + "&passkey=" + self.Password
		return releaseName

	def __HandleUserCreatedJob( self, logger, releaseInfo ):
		releaseName = self.__ReadTorrentPage( logger, releaseInfo )
		releaseInfo.ReleaseName = releaseName

		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		isAllowedMessage = releaseNameParser.IsAllowed()
		if isAllowedMessage is not None:
			raise PtpUploaderException( JobRunningState.Ignored, isAllowedMessage )

		releaseInfo.ReleaseName = RemoveDisallowedCharactersFromPath( releaseInfo.ReleaseName)

		releaseNameParser.GetSourceAndFormat( releaseInfo )
		if releaseNameParser.Scene:
			releaseInfo.SetSceneRelease()

	def __HandleAutoCreatedJob( self, logger, releaseInfo ):
		# In case of automatic announcement we have to check the release name if it is valid.
		# We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source.

		releaseInfo.ReleaseName = self.__ReadTorrentPage( logger, releaseInfo )
		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		isAllowedMessage = releaseNameParser.IsAllowed()
		if isAllowedMessage is not None:
			raise PtpUploaderException( JobRunningState.Ignored, isAllowedMessage )

		releaseInfo.ReleaseName = RemoveDisallowedCharactersFromPath( releaseInfo.ReleaseName)

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
		logger.info( "Downloading torrent file from HDBits to '%s'." % path )

		result = MyGlobals.session.get( releaseInfo.SceneAccessDownloadUrl )
		result.raise_for_status()
		response = result.content

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
		result = re.match( r".*hdbits\.org/download\.php/.*\?id=(\d+)&passkey=.*", url )
		if result is None:
			return ""
		else:
			return result.group( 1 )

	def GetUrlFromId( self, id ):
		return "https://hdbits.org/details.php?id=" + id