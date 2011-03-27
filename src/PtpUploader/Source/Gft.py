from Job.JobRunningState import JobRunningState
from Source.SourceBase import SourceBase

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

class Gft(SourceBase):
	def __init__(self):
		self.Name = "gft"
		self.MaximumParallelDownloads = Settings.GftMaximumParallelDownloads
	
	@staticmethod
	def Login():
		MyGlobals.Logger.info( "Loggin in to GFT." );
		
		# GFT stores a cookie when login.php is loaded that is needed for takeloin.php. 
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		result = opener.open( "http://www.thegft.org/login.php" )
		response = result.read()

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		postData = urllib.urlencode( { "username": Settings.GftUserName, "password": Settings.GftPassword } )
		result = opener.open( "http://www.thegft.org/takelogin.php", postData )
		response = result.read()
		Gft.CheckIfLoggedInFromResponse( response );
	
	@staticmethod
	def CheckIfLoggedInFromResponse(response):
		if response.find( """action='takelogin.php'""" ) != -1 or response.find( """<a href='login.php'>Back to Login</a>""" ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to GFT. Probably due to the bad user name or password in settings." )
	
	# TODO: no longer needed
#	@staticmethod
#	def __DownloadNfoFromDedicatedPage(logger, releaseInfo):
#		url = "http://www.thegft.org/viewnfo.php?id=%s" % releaseInfo.AnnouncementId
#		logger.info( "Downloading NFO from dedicated page '%s'." % url )
#		
#		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
#		request = urllib2.Request( url )
#		result = opener.open( request )
#		response = result.read()
#		Gft.CheckIfLoggedInFromResponse( response )
#		
#		return response

	
	# Sets IMDb if presents in the torrent description.
	# Sets scene release if pretime presents on the page.
	# Returns with the release name.
	@staticmethod
	def __ReadTorrentPage(logger, releaseInfo):
		url = "http://www.thegft.org/details.php?id=%s" % releaseInfo.AnnouncementId;
		logger.info( "Downloading NFO from page '%s'." % url );
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) );
		request = urllib2.Request( url );
		result = opener.open( request );
		response = result.read();
		Gft.CheckIfLoggedInFromResponse( response );

		# Make sure we only get information from the description and not from the comments.
		descriptionEndIndex = response.find( """<p><a name="startcomments"></a></p>""" )
		if descriptionEndIndex == -1:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Description can't found. Probably the layout of the site has changed." )
		
		description = response[ :descriptionEndIndex ]

		# Get release name.
		matches = re.search( r"<title>GFT 2011 :: Details for torrent &quot;(.+)&quot;</title>", description );
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Release name can't be found on torrent page." );
	
		releaseName = matches.group( 1 );

		# Get IMDb id.
		if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
			releaseInfo.ImdbId = NfoParser.GetImdbId( description )

		# Check if pretime presents.
		# TODO: this is unreliable as the uploaders on GFT set this
		#if description.find( """<td><img src='/pic/scene.jpg' alt='Scene' /></td>""" ) != -1:
		#	releaseInfo.SetSceneRelease()

		# For some reason there are announced, but non visible releases on GFT that never start seeding. Ignore them.
		if description.find( """<td class="heading" align="right" valign="top">Visible</td><td align="left" valign="top"><b>no</b> (dead)</td>""" ) != -1:
			raise PtpUploaderException( JobRunningState.Ignored, "Set to not visible on torrent page." )

		return releaseName

		# TODO: no longer needed

		# Get the NFO.
#		descriptionStartText = '<tr><td class="heading" valign="top" align="right">Description</td><td valign="top" align=left>' 
#		nfoStartIndex = description.find( descriptionStartText )
#		if nfoStartIndex == -1:
#			raise PtpUploaderException( "NFO can't be found on page '%s'." % url ) 
#
#		nfoStartIndex += len( descriptionStartText ) 		
#		nfoEndIndex = description.find( '<tr><td class=rowhead>NFO</td>', nfoStartIndex )
#		if nfoStartIndex == -1:
#			raise PtpUploaderException( "NFO can't be found on page '%s'." % url ) 
#			
#		nfo = description[ nfoStartIndex : nfoEndIndex ]
		
		# Sometimes the Description field is empty but the NFO presents at the dedicated page.
		#nfo = nfo.replace( "</td></tr>", "" )
		#nfo = nfo.strip()
		#if len( nfo ) <= 0:
		#	return Gft.__DownloadNfoFromDedicatedPage( logger, releaseInfo )
		#
		#return nfo

	@staticmethod
	def __HandleUserCreatedJob(logger, releaseInfo):
		releaseName = Gft.__ReadTorrentPage( logger, releaseInfo )
		if not releaseInfo.IsReleaseNameSet():
			releaseInfo.ReleaseName = releaseName

		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		releaseNameParser.GetSourceAndFormat( releaseInfo )
		if releaseNameParser.Scene:
			releaseInfo.SetSceneRelease()

	@staticmethod
	def __HandleAutoCreatedJob(logger, releaseInfo):
		# In case of automatic announcement we have to check the release name if it is valid.
		# We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source.
		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		if not releaseNameParser.IsAllowed():
			raise PtpUploaderException( JobRunningState.Ignored, "Ignored release because of its name." )

		releaseNameParser.GetSourceAndFormat( releaseInfo )
		
		# TODO: temp
		time.sleep( 30 ) # "Tactical delay" because of the not visible torrents. These should be rescheduled.

		releaseName = Gft.__ReadTorrentPage( logger, releaseInfo )
		if releaseName != releaseInfo.ReleaseName:
			raise PtpUploaderException( "Announcement release name '%s' and release name '%s' on page '%s' are different." % ( releaseInfo.ReleaseName, releaseName, url ) )

		if releaseNameParser.Scene:
			releaseInfo.SetSceneRelease()

		if ( not releaseInfo.IsSceneRelease() ) and Settings.GftAutomaticJobFilter == "SceneOnly":
			raise PtpUploaderException( JobRunningState.Ignored, "Non-scene release." )
	
	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		if releaseInfo.IsUserCreatedJob():
			Gft.__HandleUserCreatedJob( logger, releaseInfo )
		else:
			Gft.__HandleAutoCreatedJob( logger, releaseInfo )
	
	@staticmethod
	def DownloadTorrent(logger, releaseInfo, path):
		url = "http://www.thegft.org/download.php?torrent=%s" % releaseInfo.AnnouncementId;
		logger.info( "Downloading torrent file from '%s' to '%s'." % ( url, path ) );

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) );
		request = urllib2.Request( url );
		result = opener.open( request );
		response = result.read();
		Gft.CheckIfLoggedInFromResponse( response );
		
		file = open( path, "wb" );
		file.write( response );
		file.close();

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
		result = re.match( r".*thegft\.org/details.php\?id=(\d+).*", url )
		if result is None:
			return ""
		else:
			return result.group( 1 )