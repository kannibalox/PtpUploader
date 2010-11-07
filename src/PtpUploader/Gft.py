from Globals import Globals;
from PtpUploaderException import PtpUploaderException;
from Settings import Settings;

import re;
import urllib;
import urllib2;

class Gft:
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
			raise PtpUploaderException( "Looks like you are not logged in to Gft. Probably due to the bad cookie in settings." )
	
	@staticmethod
	def DownloadNfo(announcement, getReleaseName = False, checkPretime = True):
		url = "http://www.thegft.org/details.php?id=%s" % announcement.AnnouncementId;
		Globals.Logger.info( "Downloading NFO from page '%s'." % url );
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) );
		request = urllib2.Request( url );
		result = opener.open( request );
		response = result.read();
		Gft.CheckIfLoggedInFromResponse( response );

		# Get release name.
		matches = re.search( r"<title>Details for torrent &quot;(.+)&quot; :: GFTracker </title>", response );
		if matches is None:
			raise PtpUploaderException( "Release name can't be found on page '%s'." % url );
	
		releaseName = matches.group( 1 );
		if getReleaseName:
			announcement.ReleaseName = releaseName;
		elif releaseName != announcement.ReleaseName:
			raise PtpUploaderException( "Announcement release name '%s' and release name '%s' on page '%s' are different." % ( announcement.ReleaseName, releaseName, url ) );

		# For some reason there are announced, but non visible releases on GFT that never start seeding. Ignore them.
		if response.find( '<td class="heading" align="right" valign="top">Visible</td><td align="left" valign="top"><b>no</b>' ) != -1:
			raise PtpUploaderException( "Ignoring release '%s' at '%s' because it is set to not visible." % ( releaseName, url ) ); 
	
		# Check for pretime to ignore non scene releases.
		if checkPretime and response.find( ">Too quick, bitches!!<" ) != -1:
			raise PtpUploaderException( "Pretime can't be found on page '%s'. Possibly a P2P release." % url ); 

		# Get the NFO.
		nfoStartIndex = response.find( '<tr><td class="heading" valign="top" align="right">Description</td><td valign="top" align=left>' );
		if nfoStartIndex == -1:
			raise PtpUploaderException( "NFO can't be found on page '%s'." % url ); 
		
		nfoEndIndex = response.find( '<tr><td class=rowhead>NFO</td>' );
		if nfoStartIndex == -1:
			raise PtpUploaderException( "NFO can't be found on page '%s'." % url ); 
			
		nfo = response[ nfoStartIndex : nfoEndIndex ];
		return nfo;
	
	@staticmethod
	def DownloadTorrent(releaseInfo, path):
		url = "http://www.thegft.org/download.php?id=%s" % releaseInfo.Announcement.AnnouncementId;
		Globals.Logger.info( "Downloading torrent file from '%s' to '%s'." % ( url, path ) );

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) );		
		request = urllib2.Request( url );
		result = opener.open( request );
		response = result.read();
		Gft.CheckIfLoggedInFromResponse( response );
		
		file = open( path, "wb" );
		file.write( response );
		file.close();