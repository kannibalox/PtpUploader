from Job.JobRunningState import JobRunningState
from Source.SourceBase import SourceBase

from Helper import GetSizeFromText, MakeRetryingHttpRequest
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

class FunFile(SourceBase):
	def __init__( self ):
		SourceBase.__init__( self )

		self.Name = "ff"
		self.NameInSettings = "FunFile"

	def LoadSettings( self, settings ):
		SourceBase.LoadSettings( self, settings )

	def IsEnabled( self ):
		return len( self.Username ) > 0 and len( self.Password ) > 0

	def Login( self ):
		MyGlobals.Logger.info( "Logging in to FunFile." )
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		postData = urllib.urlencode( { "username": self.Username, "password": self.Password } )
		request = urllib2.Request( "https://www.funfile.org/takelogin.php", postData )
		result = opener.open( request )
		response = result.read()
		self.CheckIfLoggedInFromResponse( response );

	def CheckIfLoggedInFromResponse( self, response ):
		if response.find( 'action="takelogin.php"' ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to FunFile. Probably due to the bad user name or password in settings." )

	# Sets IMDb if presents in the torrent description.
	# Returns with the release name.
	def __ReadTorrentPage( self, logger, releaseInfo ):
		url = "https://www.funfile.org/details.php?id=%s&filelist=1" % releaseInfo.AnnouncementId
		logger.info( "Downloading NFO from page '%s'." % url )

		response = MakeRetryingHttpRequest( url )
		self.CheckIfLoggedInFromResponse( response )

		# Make sure we only get information from the description and not from the comments.
		descriptionEndIndex = response.find( """<p><a name="startcomments"></a></p>""" )
		if descriptionEndIndex == -1:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Description can't found. Probably the layout of the site has changed." )

		description = response[ :descriptionEndIndex ]

		# Get release name.
		matches = re.search( r"""Details for torrent &quot;(.+)&quot;</title>""", description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Release name can't be found on torrent page." )

		releaseName = matches.group( 1 )

		# Get IMDb id.
		if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
			releaseInfo.ImdbId = NfoParser.GetImdbId( description )

		# Get size.
		# <tr><td class="td_head">Size</td><td class="td_col">699.98 MB (733,983,002 bytes)</td></tr>
		matches = re.search( r"""<tr><td class="rowhead" >Size<span id="filelist"></span></td><td class="row1" >.+ \((.+bytes)\)""", description )
		if matches is None:
			logger.warning( "Size not found on torrent page." )
		else:
			size = matches.group( 1 )
			releaseInfo.Size = GetSizeFromText( size )

		# Store the download URL.
		# <td class="td_head">Download</td><td class="td_col"><a href="download/442572/AAAA/Winnie.the.Pooh.RERIP.DVDRip.XviD-NeDiVx.torrent">
		matches = re.search( r"""<tr><td class="rowhead">Action</td><td class="row1"><span style="float:left"><a class="index" href="download.php/(.+?)">""", description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Download link can't be found on torrent page." )

		releaseInfo.SceneAccessDownloadUrl = "https://www.funfile.org/download.php/" + matches.group( 1 )

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
			raise PtpUploaderException( "Announcement release name '%s' and release name '%s' on FunFile are different." % ( releaseInfo.ReleaseName, releaseName ) )

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
		logger.info( "Downloading torrent file from FunFile to '%s'." % path )

		response = MakeRetryingHttpRequest( releaseInfo.SceneAccessDownloadUrl )
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
		result = re.match( r".*funfile\.org/details.php\?id=(\d+).*", url )
		if result is None:
			return ""
		else:
			return result.group( 1 )

	def GetUrlFromId( self, id ):
		return "https://www.funfile.org/details.php?id=" + id

	def GetIdFromAutodlIrssiUrl( self, url ):
		# http://www.funfile.org/download.php/897257/
		result = re.match( r".*funfile\.org/download.php/(\d+)/.*", url )
		if result is None:
			return ""
		else:
			return result.group( 1 )
