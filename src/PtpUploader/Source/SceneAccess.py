from Job.JobRunningState import JobRunningState
from Source.SourceBase import SourceBase

from Helper import GetSizeFromText
from MyGlobals import MyGlobals
from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor
from ReleaseInfo import ReleaseInfo
from ReleaseNameParser import ReleaseNameParser
from Settings import Settings

import re
import time
import urllib
import urllib2

class SceneAccess(SourceBase):
	def __init__(self):
		self.Name = "scc"
		self.Username = Settings.GetDefault( "SceneAccess", "Username", "" )
		self.Password = Settings.GetDefault( "SceneAccess", "Password", "" )
		self.MaximumParallelDownloads = int( Settings.GetDefault( "SceneAccess", "MaximumParallelDownloads", "1" ) )
		self.IrcEnabled = Settings.GetDefault( "SceneAccess", "IrcEnabled", "" ).lower() == "yes"

	def IsEnabled(self):
		return len( self.Username ) > 0 and len( self.Password ) > 0

	def Login(self):
		MyGlobals.Logger.info( "Logging in to SceneAccess." );
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		postData = urllib.urlencode( { "username": self.Username, "password": self.Password } )
		result = opener.open( "http://www.sceneaccess.org/login", postData )
		response = result.read()
		self.CheckIfLoggedInFromResponse( response );
	
	def CheckIfLoggedInFromResponse(self, response):
		if response.find( """<div id="login_box_rcvr">""" ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to SceneAccess. Probably due to the bad user name or password in settings." )
	
	# Sets IMDb if presents in the torrent description.
	# Returns with the release name.
	def __ReadTorrentPage(self, logger, releaseInfo):
		url = "http://www.sceneaccess.org/details?id=%s" % releaseInfo.AnnouncementId
		logger.info( "Downloading NFO from page '%s'." % url )
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		self.CheckIfLoggedInFromResponse( response )

		# Make sure we only get information from the description and not from the comments.
		descriptionEndIndex = response.find( """<p><a name="comments"></a></p>""" )
		if descriptionEndIndex == -1:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Description can't found. Probably the layout of the site has changed." )
		
		description = response[ :descriptionEndIndex ]

		# Get release name.
		matches = re.search( r"""<div id="details_box_header"><h1>(.+?)</h1></div>""", description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Release name can't be found on torrent page." )

		releaseName = matches.group( 1 )

		# Get IMDb id.
		if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
			releaseInfo.ImdbId = NfoParser.GetImdbId( description )

		# Get size.
		# <tr><td class="td_head">Size</td><td class="td_col">699.98 MB (733,983,002 bytes)</td></tr>
		matches = re.search( r"""<tr><td class="td_head">Size</td><td class="td_col">.+ \((.+bytes)\)</td></tr>""", description )
		if matches is None:
			logger.warning( "Size not found on torrent page." )
		else:
			size = matches.group( 1 )
			releaseInfo.Size = GetSizeFromText( size )
			
		# Store the download URL.
		# <td class="td_head">Download</td><td class="td_col"><a class="index" href="download/442572/8bf9b4f6a24ec4ceb6b2b90603348f07/Winnie.the.Pooh.RERIP.DVDRip.XviD-NeDiVx.torrent">
		matches = re.search( r"""<td class="td_head">Download</td><td class="td_col"><a class="index" href="(.+?)">""", description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Release name can't be found on torrent page." )

		releaseInfo.SceneAccessDownloadUrl = "http://www.sceneaccess.org/" + matches.group( 1 )

		return releaseName

	def __HandleUserCreatedJob(self, logger, releaseInfo):
		releaseName = self.__ReadTorrentPage( logger, releaseInfo )
		if not releaseInfo.IsReleaseNameSet():
			releaseInfo.ReleaseName = releaseName

		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		releaseNameParser.GetSourceAndFormat( releaseInfo )

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
			raise PtpUploaderException( "Announcement release name '%s' and release name '%s' on SceneAccess are different." % ( releaseInfo.ReleaseName, releaseName ) )

	def PrepareDownload(self, logger, releaseInfo):
		if releaseInfo.IsUserCreatedJob():
			self.__HandleUserCreatedJob( logger, releaseInfo )
		else:
			self.__HandleAutoCreatedJob( logger, releaseInfo )

		# There are only scene releases on SceneAccess.
		releaseInfo.SetSceneRelease()

	def DownloadTorrent(self, logger, releaseInfo, path):
		# This can't happen.
		if len( releaseInfo.SceneAccessDownloadUrl ) <= 0:
			raise PtpUploaderException( "SceneAccessDownloadUrl is not set." )			
		
		# We don't log the download URL because it is sensitive information.
		logger.info( "Downloading torrent file from SceneAccess to '%s'." % path )

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) );
		request = urllib2.Request( releaseInfo.SceneAccessDownloadUrl );
		result = opener.open( request );
		response = result.read();
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

	def GetIdFromUrl(self, url):
		result = re.match( r".*sceneaccess\.org/details\?id=(\d+).*", url )
		if result is None:
			return ""
		else:
			return result.group( 1 )

	def GetUrlFromId(self, id):
		return "http://www.sceneaccess.org/details?id=" + id
	
	def InviteToIrc(self):
		if not self.IrcEnabled:
			return

		MyGlobals.Logger.info( "Requesting IRC invite on SceneAccess." );
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		postData = urllib.urlencode( { "announce": "yes" } )
		result = opener.open( "http://www.sceneaccess.org/irc", postData )
		response = result.read()
		self.CheckIfLoggedInFromResponse( response );
