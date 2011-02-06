from Globals import Globals;
from NfoParser import NfoParser;
from PtpUploaderException import PtpUploaderException;
from ReleaseFilter import ReleaseFilter;
from ReleaseInfo import ReleaseInfo;
from SceneRelease import SceneRelease;
from Settings import Settings;

import re;
import time
import urllib;
import urllib2;

class Gft:
	def __init__(self):
		self.Name = "gft"
		self.MaximumParallelDownloads = Settings.GftMaximumParallelDownloads
	
	@staticmethod
	def Login():
		Globals.Logger.info( "Loggin in to GFT." );
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) );
		postData = urllib.urlencode( { "username": Settings.GftUserName, "password": Settings.GftPassword } )
		request = urllib2.Request( "http://www.thegft.org/takelogin.php", postData );
		result = opener.open( request );
		response = result.read();
		Gft.CheckIfLoggedInFromResponse( response );
	
	@staticmethod
	def CheckIfLoggedInFromResponse(response):
		if response.find( 'action="takelogin.php"' ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to GFT. Probably due to the bad user name or password in settings." )
	
	@staticmethod
	def __IsPretimePresents(description):
		return description.find( ">Too quick, bitches!!<" ) == -1 and description.find( ">Pre Offline<" ) == -1

	@staticmethod
	def __DownloadNfoFromDedicatedPage(logger, releaseInfo):
		url = "http://www.thegft.org/viewnfo.php?id=%s" % releaseInfo.AnnouncementId
		logger.info( "Downloading NFO from dedicated page '%s'." % url )
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		Gft.CheckIfLoggedInFromResponse( response )
		
		return response

	@staticmethod
	def __DownloadNfo(logger, releaseInfo, getReleaseName = False, checkPretime = True):
		url = "http://www.thegft.org/details.php?id=%s" % releaseInfo.AnnouncementId;
		logger.info( "Downloading NFO from page '%s'." % url );
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) );
		request = urllib2.Request( url );
		result = opener.open( request );
		response = result.read();
		Gft.CheckIfLoggedInFromResponse( response );

		# Make sure we only get information from the description and not from the comments.
		descriptionEndIndex = response.find( '<p><a name="startcomments"></a></p>' )
		if descriptionEndIndex == -1:
			raise PtpUploaderException( "Description can't found on page '%s'. Probably the layout of the site has changed." % url )
		
		description = response[ :descriptionEndIndex ]			

		# Get release name.
		matches = re.search( r"<title>Details for torrent &quot;(.+)&quot; :: GFTracker </title>", description );
		if matches is None:
			raise PtpUploaderException( "Release name can't be found on page '%s'." % url );
	
		releaseName = matches.group( 1 );
		if getReleaseName:
			releaseInfo.ReleaseName = releaseName;
		elif releaseName != releaseInfo.ReleaseName:
			raise PtpUploaderException( "Announcement release name '%s' and release name '%s' on page '%s' are different." % ( releaseInfo.ReleaseName, releaseName, url ) );

		# For some reason there are announced, but non visible releases on GFT that never start seeding. Ignore them.
		# <td class="heading" valign="top" align="right">Visible</td><td valign="top" align=left><b>no</b> (dead)</td></tr>
		if re.search( r'">Visible</td><td.+><b>no</b> \(dead\)', description ):
			raise PtpUploaderException( "Ignoring release '%s' at '%s' because it is set to not visible." % ( releaseName, url ) ); 
	
		# Check for pretime to ignore non scene releases.
		if checkPretime and not Gft.__IsPretimePresents( description ):
			raise PtpUploaderException( "Pretime can't be found on page '%s'. Possibly a P2P release." % url ); 

		# Get the NFO.
		descriptionStartText = '<tr><td class="heading" valign="top" align="right">Description</td><td valign="top" align=left>' 
		nfoStartIndex = description.find( descriptionStartText )
		if nfoStartIndex == -1:
			raise PtpUploaderException( "NFO can't be found on page '%s'." % url ) 

		nfoStartIndex += len( descriptionStartText ) 		
		nfoEndIndex = description.find( '<tr><td class=rowhead>NFO</td>', nfoStartIndex )
		if nfoStartIndex == -1:
			raise PtpUploaderException( "NFO can't be found on page '%s'." % url ) 
			
		nfo = description[ nfoStartIndex : nfoEndIndex ]
		
		# Sometimes the Description field is empty but the NFO presents at the dedicated page.
		nfo = nfo.replace( "</td></tr>", "" )
		nfo = nfo.strip()
		if len( nfo ) <= 0:
			return Gft.__DownloadNfoFromDedicatedPage( logger, releaseInfo )
		
		return nfo
	
	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		nfoText = "";
		
		if releaseInfo.IsManualAnnouncement:
			# Download the NFO and get the release name.
			nfoText = Gft.__DownloadNfo( logger, releaseInfo, getReleaseName = True, checkPretime = False );
		else:
			# In case of automatic announcement we have to check the release name if it is valid.
			# We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source.
			releaserGroup = ReleaseFilter.IsValidReleaseName( releaseInfo.ReleaseName )
			if releaserGroup is None:
				logger.info( "Ignoring release '%s' because of its name." % releaseInfo.ReleaseName );
				return None;

			# TODO: temp
			time.sleep( 30 ); # "Tactical delay" because of the not visible torrents. These should be rescheduled.

			# If the release is from a known scene releaser group we skip the pretime checking.
			# This is useful because the pretime sometime not presents on GFT.
			isKnownSceneReleaserGroup = releaserGroup in Settings.SceneReleaserGroup

			# Download the NFO.
			nfoText = Gft.__DownloadNfo( logger, releaseInfo, getReleaseName = False, checkPretime = not isKnownSceneReleaserGroup )
		
		releaseInfo.ImdbId = NfoParser.GetImdbId( nfoText )
		SceneRelease.GetSourceAndFormatFromSceneReleaseName( releaseInfo, releaseInfo.ReleaseName )
		return releaseInfo;
	
	@staticmethod
	def DownloadTorrent(logger, releaseInfo, path):
		url = "http://www.thegft.org/download.php?id=%s" % releaseInfo.AnnouncementId;
		logger.info( "Downloading torrent file from '%s' to '%s'." % ( url, path ) );

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) );		
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
		sceneRelease = SceneRelease( releaseInfo.GetReleaseDownloadPath() )
		sceneRelease.Extract( logger, releaseInfo.GetReleaseUploadPath() )
		releaseInfo.Nfo = sceneRelease.Nfo
		
	@staticmethod
	def RenameRelease(logger, releaseInfo):
		pass
				
	@staticmethod
	def IsSingleFileTorrentNeedsDirectory():
		return True
	
	@staticmethod
	def IncludeReleaseNameInReleaseDescription():
		return True