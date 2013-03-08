from Job.JobRunningState import JobRunningState
from Source.SourceBase import SourceBase

from Helper import DecodeHtmlEntities, GetSizeFromText
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

class Gft(SourceBase):
	def __init__(self):
		SourceBase.__init__( self )

		self.Name = "gft"
		self.NameInSettings = "GFT"

	def IsEnabled(self):
		return len( self.Username ) > 0 and len( self.Password ) > 0

	def Login(self):
		MyGlobals.Logger.info( "Logging in to GFT." );
		
		# GFT stores a cookie when login.php is loaded that is needed for takeloin.php. 
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		result = opener.open( "http://www.thegft.org/login.php" )
		response = result.read()

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		postData = urllib.urlencode( { "username": self.Username, "password": self.Password } )
		result = opener.open( "http://www.thegft.org/takelogin.php", postData )
		response = result.read()
		self.CheckIfLoggedInFromResponse( response );
	
	def CheckIfLoggedInFromResponse(self, response):
		if response.find( """action='takelogin.php'""" ) != -1 or response.find( """<a href='login.php'>Back to Login</a>""" ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to GFT. Probably due to the bad user name or password in settings." )

	def __GetTorrentPageAsString( self, logger, releaseInfo ):
		url = "http://www.thegft.org/details.php?id=%s" % releaseInfo.AnnouncementId;
		logger.info( "Downloading NFO from page '%s'." % url );

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) );
		request = urllib2.Request( url );
		result = opener.open( request );
		response = result.read();
		self.CheckIfLoggedInFromResponse( response );

		# Make sure we only get information from the description and not from the comments.
		descriptionEndIndex = response.find( """<p><a name="startcomments"></a></p>""" )
		if descriptionEndIndex == -1:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Description can't found. Probably the layout of the site has changed." )
		
		description = response[ :descriptionEndIndex ]
		return description

	def __ReadTorrentPageInternal( self, logger, releaseInfo, description ):
		# Get release name.
		matches = re.search( r"<title>GFT \d+ :: Details for torrent &quot;(.+)&quot;</title>", description )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Release name can't be found on torrent page." )

		releaseName = DecodeHtmlEntities( matches.group( 1 ) )

		# Get IMDb id.
		if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
			releaseInfo.ImdbId = NfoParser.GetImdbId( description )

		# Check if pretime presents.
		# TODO: this is unreliable as the uploaders on GFT set this
		#if description.find( """<td><img src='/pic/scene.jpg' alt='Scene' /></td>""" ) != -1:
		#	releaseInfo.SetSceneRelease()
		
		# Get size.
		# Two possible formats:
		# <tr><td class="heading" valign="top" align="right">Size</td><td valign="top" align="left">4.47 GB (4,799,041,437bytes )</td></tr>
		# <tr><td class='heading' valign='top' align='right'>Size</td><td valign='top' align='left'>4.47 GB (4,799,041,437bytes )</td></tr>
		matches = re.search( r"""<tr><td class=.heading. valign=.top. align=.right.>Size</td><td valign=.top. align=.left.>.+ \((.+bytes) ?\)</td></tr>""", description )
		if matches is None:
			logger.warning( "Size not found on torrent page." )
		else:
			size = matches.group( 1 )
			releaseInfo.Size = GetSizeFromText( size )

		return releaseName

	# Sets IMDb if presents in the torrent description.
	# Sets scene release if pretime presents on the page.
	# Returns with the release name.
	def __ReadTorrentPage( self, logger, releaseInfo ):
		description = self.__GetTorrentPageAsString( logger, releaseInfo )
		releaseName = self.__ReadTorrentPageInternal( logger, releaseInfo, description )

		# For some reason there are announced, but non visible releases on GFT that never start seeding.
		# We give them some time to become visible then we ignore them.
		maximumTries = 3
		while True:
			# Two possible formats:
			# <td class="heading" valign="top" align="right">Visible</td><td valign="top" align="left"><b>no</b> (dead)</td>
			# <td class="heading" align="right" valign="top">Visible</td><td align="left" valign="top"><b>no</b> (dead)</td>
			if description.find( """<td class="heading" v?align=".+?" v?align=".+?">Visible</td><td v?align=".+?" v?align=".+?"><b>no</b> (dead)</td>""" ) == -1:
				break

			if maximumTries > 1:
				maximumTries -= 1
				time.sleep( 10 ) # Ten seconds.
			else:
				raise PtpUploaderException( JobRunningState.Ignored, "Set to not visible on torrent page." )

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
			raise PtpUploaderException( "Announcement release name '%s' and release name '%s' on GFT are different." % ( releaseInfo.ReleaseName, releaseName ) )

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
		url = "http://www.thegft.org/download.php?torrent=%s" % releaseInfo.AnnouncementId;
		logger.info( "Downloading torrent file from '%s' to '%s'." % ( url, path ) );

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) );
		request = urllib2.Request( url );
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
		result = re.match( r".*thegft\.org/details\.php\?id=(\d+).*", url )
		if result is None:
			return ""
		else:
			return result.group( 1 )

	def GetUrlFromId(self, id):
		return "http://www.thegft.org/details.php?id=" + id

	def GetIdFromAutodlIrssiUrl( self, url ):
		# http://www.thegft.org/download.php?torrent=897257&passkey=AAAAA
		result = re.match( r".*thegft\.org/download\.php\?torrent=(\d+).*", url )
		if result is None:
			return ""
		else:
			return result.group( 1 )
